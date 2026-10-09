import { useState } from "react";
import { Bell } from "lucide-react";
import { PageFrame } from "../shared/PageFrame";
import { Button } from "../primitives/Button";

export function PushSettings({ supported = typeof window !== "undefined" && "PushManager" in window, embedded = false }: { supported?: boolean; embedded?: boolean }) {
  const [permission, setPermission] = useState<NotificationPermission | "unsupported">("default");
  const enable = async () => {
    if (!supported || !("Notification" in window)) { setPermission("unsupported"); return; }
    setPermission(await Notification.requestPermission());
  };
  const fallback = "Recibirás notificaciones por correo o WhatsApp.";
  const content = <><p>{!supported || permission === "unsupported" ? `Este navegador no admite push. ${fallback}` : permission === "denied" ? `Denegaste los avisos del navegador. ${fallback}` : permission === "granted" ? "Push activado." : "Activa los avisos del navegador para recibir novedades."}</p>{supported && permission !== "unsupported" && permission !== "denied" ? <><Button onClick={() => void enable()}>{permission === "granted" ? "Push activado" : "Activar notificaciones"}</Button>{permission !== "granted" ? <p className="push-settings__legend"><Bell aria-hidden="true" />El navegador te pedirá permiso.</p> : null}</> : null}</>;
  return embedded ? <section className="push-settings">{content}</section> : <PageFrame title="Notificaciones push" meta="Avisos del navegador para este dispositivo"><div className="push-settings">{content}</div></PageFrame>;
}
