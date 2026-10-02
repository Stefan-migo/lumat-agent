import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, getAdminUser, unlockUser, updateAdminUser } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { AdminUser, AdminUserProfileUpdate } from "../../types";
import { roleLabels } from "../../roleLabels";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

const fields = ["name", "phone", "email", "position"] as const;
type FormFields = Record<(typeof fields)[number], string>;

export function UserFicha({ userId }: { userId: number }) {
  const loadUser = useCallback(() => getAdminUser(userId), [userId]);
  const data = useAsyncData(loadUser, true);
  const [accountOverride, setAccountOverride] = useState<AdminUser | null>(null);
  const [form, setForm] = useState<FormFields>({ name: "", phone: "", email: "", position: "" });
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
  if (!account) return <PageFrame title="Ficha de usuario" state={<StateMessage tone="danger" role="alert" title={data.state === "denied" ? "No tienes permiso para ver esta ficha" : data.state === "error" ? "No pudimos cargar la ficha" : "Cargando ficha"} />}>{null}</PageFrame>;
  return <PageFrame title={account.name ?? account.username} meta={roleLabels[account.role]} actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a usuarios</Button>}>
    <Card title="Datos del usuario">
      <p><strong>{account.name ?? account.username}</strong> <Badge>{roleLabels[account.role]}</Badge></p>
      <form onSubmit={(event) => void save(event)}>
        <Input label="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <Input label="Teléfono" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
        <Input label="Correo" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        <Input label="Cargo" value={form.position} onChange={(event) => setForm({ ...form, position: event.target.value })} />
        {feedback ? <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.title} /> : null}
        <Button type="submit" disabled={busy}>{busy ? "Guardando…" : "Guardar cambios"}</Button>
      </form>
    </Card>
    <Card title="Seguridad de la cuenta">
      {account.locked_until ? <><p>Cuenta bloqueada hasta {new Date(account.locked_until).toLocaleString("es-CL")} · {account.failed_logins} intentos fallidos</p><Button disabled={busy} onClick={() => void unlock()}>Desbloquear cuenta</Button></>
        : <p>La cuenta está desbloqueada</p>}
    </Card>
  </PageFrame>;
}
