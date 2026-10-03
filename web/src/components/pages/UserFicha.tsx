import { useCallback, useEffect, useState, type FormEvent } from "react";
import { BriefcaseBusiness, ChevronLeft, LockKeyhole, Mail, Phone, Save, ShieldCheck, UnlockKeyhole, UserRound } from "lucide-react";
import { ApiError, getAdminUser, unlockUser, updateAdminUser } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { AdminUser, AdminUserProfileUpdate } from "../../types";
import { roleLabels } from "../../roleLabels";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { StatusBadge } from "../primitives/StatusBadge";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

const fields = ["name", "phone", "email", "position"] as const;
type FormFields = Record<(typeof fields)[number], string>;
const emptyForm: FormFields = { name: "", phone: "", email: "", position: "" };

export function UserFicha({ userId }: { userId: number }) {
  const loadUser = useCallback(() => getAdminUser(userId), [userId]);
  const data = useAsyncData(loadUser, true);
  const [accountOverride, setAccountOverride] = useState<AdminUser | null>(null);
  const [form, setForm] = useState<FormFields>(emptyForm);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "danger"; title: string } | null>(null);
  const account = accountOverride ?? data.data?.user ?? null;
  useEffect(() => {
    if (account) setForm(Object.fromEntries(fields.map((field) => [field, account[field] ?? ""])) as FormFields);
  }, [account]);
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!account || busy) return;
    setBusy(true); setFeedback(null);
    const body = Object.fromEntries(fields.map((field) => [field, form[field].trim() || null])) as AdminUserProfileUpdate;
    try {
      const result = await updateAdminUser(userId, body);
      setAccountOverride(result.user);
      setFeedback({ tone: "success", title: "Perfil actualizado" });
    } catch (error) {
      const title = error instanceof ApiError && error.status === 409
        ? "Este correo ya está registrado en otro usuario"
        : error instanceof ApiError ? error.detail : "No pudimos guardar los cambios";
      setFeedback({ tone: "danger", title });
    } finally { setBusy(false); }
  };
  const unlock = async () => {
    setBusy(true); setFeedback(null);
    try {
      const result = await unlockUser(userId);
      setAccountOverride(result.user);
      setFeedback({ tone: "success", title: "La cuenta está desbloqueada" });
    } catch (error) { setFeedback({ tone: "danger", title: error instanceof ApiError ? error.detail : "No pudimos desbloquear la cuenta" }); }
    finally { setBusy(false); }
  };
  if (!account) return <PageFrame title="Detalle del usuario" meta="Consulta y actualiza los datos de esta cuenta." state={<StateMessage tone="danger" role="alert" title={data.state === "denied" ? "No tienes permiso para ver esta ficha" : data.state === "error" ? "No pudimos cargar la ficha" : "Cargando ficha"} />}>{null}</PageFrame>;

  const displayName = account.name ?? account.username;
  const locked = Boolean(account.locked_until);
  return <PageFrame className="user-ficha-page" title="Detalle del usuario" meta="Consulta y actualiza los datos de esta cuenta."
    actions={<Button variant="secondary" className="user-ficha__back" onClick={() => window.history.back()}><Icon icon={ChevronLeft} />Volver a usuarios</Button>}>
    <div className="user-ficha__layout">
      <Card title="Cuenta del usuario" className="user-ficha__account">
        <div className="user-ficha__identity"><Avatar name={displayName} className="user-ficha__avatar" />
          <div className="user-ficha__identity-copy"><h3>{displayName}</h3><Badge tone="success">{roleLabels[account.role]}</Badge></div>
        </div>
        <div className="user-ficha__login"><span>Usuario de acceso</span><strong>{account.username}</strong><p>El rol determina sus permisos en Lumat.</p></div>
      </Card>
      <div className="user-ficha__details">
        <Card title="Datos del usuario" icon={UserRound} description="Mantén actualizada su información de contacto." className="user-ficha__form-card">
          <form onSubmit={(event) => void save(event)}>
            <div className="user-ficha__fields">
              <Input label="Nombre" icon={UserRound} placeholder="Stefan" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              <Input label="Teléfono" icon={Phone} placeholder="56898987" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
              <Input label="Correo electrónico" icon={Mail} placeholder="correo@ejemplo.com" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
              <Input label="Cargo" icon={BriefcaseBusiness} placeholder="Ej. Coordinador de operaciones" value={form.position} onChange={(event) => setForm({ ...form, position: event.target.value })} />
            </div>
            {feedback ? <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.title} /> : null}
            <footer className="user-ficha__footer">
              <Button variant="secondary" disabled={busy} onClick={() => { setForm(Object.fromEntries(fields.map((field) => [field, account[field] ?? ""])) as FormFields); setFeedback(null); }}>Descartar cambios</Button>
              <Button type="submit" disabled={busy}><Icon icon={Save} />{busy ? "Guardando…" : "Guardar cambios"}</Button>
            </footer>
          </form>
        </Card>
        <Card title="Seguridad de la cuenta" icon={ShieldCheck} description="Estado de acceso del usuario." className="user-ficha__security">
          <div className="user-ficha__security-row"><span className="user-ficha__security-icon"><Icon icon={locked ? LockKeyhole : UnlockKeyhole} /></span>
            <div className="user-ficha__security-copy"><strong>{locked ? "Cuenta bloqueada" : "Cuenta desbloqueada"}</strong>
              <p>{locked ? `Bloqueada hasta ${new Date(account.locked_until!).toLocaleString("es-CL")} · ${account.failed_logins} intentos fallidos` : "No hay un bloqueo de seguridad activo."}</p>
            </div>
            {locked ? <Button variant="secondary" disabled={busy} onClick={() => void unlock()}>Desbloquear cuenta</Button>
              : <StatusBadge status="closed" label="Desbloqueada" />}
          </div>
        </Card>
      </div>
    </div>
  </PageFrame>;
}
