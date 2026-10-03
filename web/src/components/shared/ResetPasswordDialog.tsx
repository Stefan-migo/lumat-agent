import { useState } from "react";
import { KeyRound, LockKeyhole, RefreshCw } from "lucide-react";
import { ApiError, resetUserPassword } from "../../api";
import type { AdminUser } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { StateMessage } from "./StateMessage";

const passwordAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

function generatePassword() {
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => passwordAlphabet[byte % passwordAlphabet.length]).join("");
}

export function ResetPasswordDialog({ target, onClose, onDone }: { target: AdminUser | null; onClose: () => void; onDone?: () => void }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "danger"; title: string; detail?: string } | null>(null);

  const close = () => {
    if (busy) return;
    setPassword(""); setDone(false); setFeedback(null); onClose();
  };
  const reset = async () => {
    if (!target || password.length < 8 || busy) return;
    setBusy(true); setFeedback(null);
    try {
      await resetUserPassword(target.id, password);
      setFeedback({ tone: "success", title: "Contraseña restablecida", detail: "La nueva contraseña fue aplicada de forma segura." });
      setDone(true);
      onDone?.();
    } catch (error) {
      const title = error instanceof ApiError && error.status === 422 ? "La contraseña debe tener al menos 8 caracteres"
        : error instanceof ApiError && error.status === 403 ? "No puedes restablecer tu propia contraseña"
        : error instanceof ApiError && error.status === 404 ? "El usuario ya no existe"
        : error instanceof ApiError ? error.detail : "No pudimos restablecer la contraseña";
      setFeedback({ tone: "danger", title });
    } finally { setBusy(false); }
  };

  return <Dialog open={target !== null} onClose={close} title="Restablecer contraseña" icon={KeyRound} description="Define una nueva contraseña para esta cuenta.">
    {target ? <div className="user-reset-form">
      <section className="user-access-card" aria-label="Usuario de acceso"><Avatar name={target.name ?? target.username} /><div><span>Usuario de acceso</span><strong>{target.name ?? target.username}</strong><small>{target.username}</small></div></section>
      <Input label="Nueva contraseña" type="password" icon={LockKeyhole} revealable helper="La contraseña debe tener al menos 8 caracteres." value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy || done} />
      {feedback ? <StateMessage {...feedback} role={feedback.tone === "danger" ? "alert" : "status"} /> : null}
      {!done ? <Button variant="secondary" className="user-reset-form__generate" disabled={busy} onClick={() => setPassword(generatePassword())}><Icon icon={RefreshCw} />Generar contraseña</Button> : null}
      <footer className="dialog-footer"><Button variant="secondary" disabled={busy} onClick={close}>Cancelar</Button>{done ? <Button onClick={close}>Listo</Button> : <Button disabled={password.length < 8 || busy} onClick={() => void reset()}>{busy ? "Restableciendo…" : "Restablecer contraseña"}</Button>}</footer>
    </div> : null}
  </Dialog>;
}
