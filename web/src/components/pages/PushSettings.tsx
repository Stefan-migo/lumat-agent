import { useState } from "react";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { Button } from "../primitives/Button";

export function PushSettings({ supported = typeof window !== "undefined" && "PushManager" in window }: { supported?: boolean }) {
  const [permission, setPermission] = useState<NotificationPermission | "unsupported">("default");
  const enable = async () => {
    if (!supported || !("Notification" in window)) { setPermission("unsupported"); return; }
    setPermission(await Notification.requestPermission());
  };
  const fallback = "Recibirás notificaciones por correo o WhatsApp.";
  return <PageFrame title="Notificaciones push"><p>{!supported || permission === "unsupported" ? `Este navegador no admite push. ${fallback}` : permission === "denied" ? `Denegaste los avisos del navegador. ${fallback}` : permission === "granted" ? "Push activado." : "Activa avisos del navegador para recibir novedades."}</p>{supported && permission !== "unsupported" && permission !== "denied" ? <Button onClick={() => void enable()}>{permission === "granted" ? "Push activado" : "Activar push"}</Button> : null}</PageFrame>;
}
