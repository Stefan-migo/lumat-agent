import { useState } from "react";
import { Bell } from "lucide-react";
import { fetchPushConfig, savePushSubscription } from "../../api";
import { PageFrame } from "../shared/PageFrame";
import { Button } from "../primitives/Button";

/** The three capabilities a browser needs before a subscription can exist. */
export function browserSupportsPush(): boolean {
  return typeof window !== "undefined"
    && "PushManager" in window
    && "Notification" in window
    && "serviceWorker" in navigator;
}

export function applicationServerKeyFromBase64Url(key: string): Uint8Array {
  const padding = "=".repeat((4 - key.length % 4) % 4);
  const binary = atob(key.replace(/-/g, "+").replace(/_/g, "/") + padding);
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

const FALLBACK = "Recibirás notificaciones por correo o WhatsApp.";

export function PushSettings({ supported = browserSupportsPush(), embedded = false }: { supported?: boolean; embedded?: boolean }) {
  const [permission, setPermission] = useState<NotificationPermission | "unsupported">("default");
  // A missing server key is NOT an unsupported browser. Production ran for weeks
  // with no VAPID keys configured and told every operator "this browser does not
  // support push", which is false and hides the real fix (docs/ops.md §2.8.3).
  const [unconfigured, setUnconfigured] = useState(false);
  const [error, setError] = useState(false);
  const enable = async () => {
    if (!supported || !("Notification" in window) || !("serviceWorker" in navigator)) { setPermission("unsupported"); return; }
    try {
      const config = await fetchPushConfig();
      if (config.public_key === null) { setUnconfigured(true); return; }
      if (!("PushManager" in window)) { setPermission("unsupported"); return; }
      const result = await Notification.requestPermission();
      if (result !== "granted") { setPermission(result); return; }
      const registration = await navigator.serviceWorker.ready;
      if (!registration.pushManager) { setPermission("unsupported"); return; }
      const existing = await registration.pushManager.getSubscription();
      const subscription = existing ?? (await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKeyFromBase64Url(config.public_key) as BufferSource,
      }));
      const serialized = subscription.toJSON();
      if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys.auth) throw new Error("Incomplete push subscription");
      await savePushSubscription({ endpoint: serialized.endpoint, p256dh: serialized.keys.p256dh, auth: serialized.keys.auth, user_agent: navigator.userAgent });
      setPermission("granted");
      setError(false);
    } catch {
      setError(true);
    }
  };
  const unavailable = !supported || permission === "unsupported";
  const content = <><p>{unavailable ? `Este navegador no admite notificaciones push. ${FALLBACK}`
    : unconfigured ? `Las notificaciones push no están configuradas en el servidor. ${FALLBACK}`
    : permission === "denied" ? `Denegaste los avisos del navegador. ${FALLBACK}`
    : permission === "granted" && !error ? "Push activado."
    : error ? `No pudimos activar las notificaciones push. ${FALLBACK}`
    : "Activa los avisos del navegador para recibir novedades."}</p>{supported && !unconfigured && permission !== "unsupported" && permission !== "denied" && permission !== "granted" ? <><Button onClick={() => void enable()}>Activar notificaciones</Button><p className="push-settings__legend"><Bell aria-hidden="true" />El navegador te pedirá permiso.</p></> : null}</>;
  return embedded ? <section className="push-settings">{content}</section> : <PageFrame title="Notificaciones push" meta="Avisos del navegador para este dispositivo"><div className="push-settings">{content}</div></PageFrame>;
}
