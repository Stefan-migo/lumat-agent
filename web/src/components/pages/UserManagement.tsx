import { useCallback, useState } from "react";
import { ApiError, createUser, fetchUsers, resetUserPassword, toggleUserActive } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { AdminUser, Role, User } from "../../types";
import { roleLabels } from "../../roleLabels";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { DataTable, type Column } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { Dialog } from "../primitives/Dialog";

const passwordAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

function generatePassword() {
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => passwordAlphabet[byte % passwordAlphabet.length]).join("");
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.detail : fallback;
}

export interface UserManagementProps { currentUser: User; }

export function UserManagement({ currentUser }: UserManagementProps) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("operador");
  const [mutationState, setMutationState] = useState<{ tone: "success" | "danger" | "info"; title: string; detail?: string } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);
  const [resetDraft, setResetDraft] = useState("");
  const [resetBusy, setResetBusy] = useState(false);
  const [resetDone, setResetDone] = useState(false);
  const data = useAsyncData(useCallback(fetchUsers, []), currentUser.role === "admin", refreshKey);

  if (currentUser.role !== "admin") {
    return <PageFrame title="Usuarios" meta="Administra el acceso al panel" state={<StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />}>{null}</PageFrame>;
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim()) { setMutationState({ tone: "danger", title: "El usuario es obligatorio" }); return; }
    if (password.length < 8) { setMutationState({ tone: "danger", title: "La contraseña debe tener al menos 8 caracteres" }); return; }
    setMutationState({ tone: "info", title: "Creando usuario" });
    try {
      await createUser({ username: username.trim(), password, role });
      setUsername(""); setPassword("");
      setMutationState({ tone: "success", title: "Usuario creado" });
      setRefreshKey((value) => value + 1);
    } catch (error) {
      setPassword("");
      setMutationState({ tone: "danger", title: errorMessage(error, "No pudimos crear el usuario") });
    }
  };

  const toggle = async (user: AdminUser) => {
    setBusyId(user.id); setMutationState({ tone: "info", title: "Actualizando estado" });
    try { await toggleUserActive(user.id); setMutationState({ tone: "success", title: "Estado actualizado" }); setRefreshKey((value) => value + 1); }
    catch (error) { setMutationState({ tone: "danger", title: errorMessage(error, "No pudimos actualizar el estado") }); }
    finally { setBusyId(null); }
  };

  const closeReset = () => {
    if (resetBusy) return;
    setResetTarget(null);
    setResetDraft("");
    setResetDone(false);
    setMutationState(null);
  };

  const reset = async () => {
    if (!resetTarget || resetDraft.length < 8 || resetBusy) return;
    setResetBusy(true);
    setMutationState(null);
    try {
      await resetUserPassword(resetTarget.id, resetDraft);
      setMutationState({ tone: "success", title: "Contraseña restablecida", detail: "La nueva contraseña fue aplicada de forma segura." });
      setResetDone(true);
      setRefreshKey((value) => value + 1);
    } catch (error) {
      const title = error instanceof ApiError && error.status === 422 ? "La contraseña debe tener al menos 8 caracteres"
        : error instanceof ApiError && error.status === 403 ? "No puedes restablecer tu propia contraseña"
        : error instanceof ApiError && error.status === 404 ? "El usuario ya no existe"
        : errorMessage(error, "No pudimos restablecer la contraseña");
      setMutationState({ tone: "danger", title });
    } finally { setResetBusy(false); }
  };

  const columns: Column<AdminUser>[] = [
    { key: "username", header: "Usuario", render: (user) => user.username },
    { key: "role", header: "Rol", render: (user) => roleLabels[user.role] },
    { key: "active", header: "Estado", render: (user) => user.active ? "Activo" : "Inactivo" },
  ];
  const state = data.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando usuarios" />
    : data.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />
    : data.state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los usuarios" detail="Intenta nuevamente en unos minutos." />
    : mutationState && !resetTarget ? <StateMessage {...mutationState} role={mutationState.tone === "danger" ? "alert" : "status"} /> : null;
  const users = data.data?.users ?? [];

  return <PageFrame title="Usuarios" meta="Administra el acceso al panel" state={state}>
    <Card title="Crear usuario">
      <form onSubmit={submit}>
        <Input label="Usuario" value={username} onChange={(event) => setUsername(event.target.value)} />
        <Input label="Contraseña" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <label>Rol<select aria-label="Rol" value={role} onChange={(event) => setRole(event.target.value as Role)}><option value="operador">Operador</option><option value="tecnico">Técnico</option><option value="admin">Administrador</option></select></label>
        <Button type="submit">Crear usuario</Button>
      </form>
    </Card>
    {data.state === "empty" || (data.state === "ready" && users.length === 0) ? <p>No hay usuarios</p> : <DataTable columns={columns} rows={users} rowKey={(user) => String(user.id)} actions={(user) => <><Button variant="secondary" disabled={(user.id === currentUser.id || user.username === currentUser.username) || busyId === user.id} onClick={() => void toggle(user)}>{user.active ? "Desactivar" : "Activar"}</Button><Button variant="secondary" disabled={(user.id === currentUser.id || user.username === currentUser.username) || busyId === user.id} onClick={() => { setResetTarget(user); setResetDraft(""); setResetDone(false); setMutationState(null); }}>Restablecer contraseña</Button></>} />}
    <Dialog open={resetTarget !== null} onClose={closeReset} title="Restablecer contraseña">
      {resetTarget ? <>
        <p>Define una nueva contraseña para {resetTarget.username}.</p>
        <Input label="Nueva contraseña" type="text" value={resetDraft} onChange={(event) => setResetDraft(event.target.value)} disabled={resetBusy || resetDone} />
        <p>La contraseña debe tener al menos 8 caracteres.</p>
        {mutationState ? <StateMessage {...mutationState} role={mutationState.tone === "danger" ? "alert" : "status"} /> : null}
        {resetDone ? <Button onClick={closeReset}>Listo</Button> : <>
          <Button variant="secondary" disabled={resetBusy} onClick={() => setResetDraft(generatePassword())}>Generar</Button>
          <Button disabled={resetDraft.length < 8 || resetBusy} onClick={() => void reset()}>{resetBusy ? "Restableciendo…" : "Restablecer contraseña"}</Button>
        </>}
      </> : null}
    </Dialog>
  </PageFrame>;
}
