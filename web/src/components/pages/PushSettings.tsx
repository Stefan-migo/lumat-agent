import { useState } from "react";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { Button } from "../primitives/Button";

export function PushSettings({ supported = typeof window !== "undefined" && "PushManager" in window }: { supported?: boolean }) {
  const [enabled, setEnabled] = useState(false);
  const enable = async () => { if (!supported || !("Notification" in window)) return; setEnabled((await Notification.requestPermission()) === "granted"); };
  return <PageFrame title="Notificaciones push"><p>{supported ? "Activa avisos del navegador para recibir novedades." : "Este navegador no admite push. Recibirás notificaciones por correo o WhatsApp."}</p>{supported ? <Button onClick={() => void enable()}>{enabled ? "Push activado" : "Activar push"}</Button> : null}</PageFrame>;
}
