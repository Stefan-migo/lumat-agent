import { useCallback, useMemo, useState } from "react";
import { BriefcaseBusiness, KeyRound, LockKeyhole, ShieldCheck, SlidersHorizontal, UserRoundMinus, Wrench } from "lucide-react";
import { ApiError, createUser, fetchUsers, resetUserPassword, toggleUserActive } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { AdminUser, Role, User } from "../../types";
import { roleLabels } from "../../roleLabels";
import { Button } from "../primitives/Button";
import { Input } from "../primitives/Input";
import { DataTable, type Column } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { Dialog } from "../primitives/Dialog";
import { pathForRoute } from "../domain/panelRoutes";
import { SearchInput } from "../primitives/SearchInput";
import { Select } from "../primitives/Select";
import { Tabs } from "../primitives/Tabs";
import { Avatar } from "../primitives/Avatar";
import { StatusBadge } from "../primitives/StatusBadge";
import { Icon } from "../primitives/Icon";
import { Badge } from "../primitives/Badge";
import { Menu } from "../primitives/Menu";

const roleIcons = { admin: ShieldCheck, operador: BriefcaseBusiness, tecnico: Wrench } as const;
const pageSize = 10;

const passwordAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

function generatePassword() {
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => passwordAlphabet[byte % passwordAlphabet.length]).join("");
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.detail : fallback;
}

export interface UserManagementProps { currentUser: User; onOpenUser?: (id: number) => void; }

export function UserManagement({ currentUser, onOpenUser }: UserManagementProps) {
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
  const [createOpen, setCreateOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "all">("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
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
      setCreateOpen(false);
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

  const state = data.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando usuarios" />
    : data.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />
    : data.state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los usuarios" detail="Intenta nuevamente en unos minutos." />
    : mutationState && !resetTarget && !createOpen ? <StateMessage {...mutationState} role={mutationState.tone === "danger" ? "alert" : "status"} /> : null;
  const users = data.data?.users ?? [];
  const roleUsers = useMemo(() => users.filter((user) => roleFilter === "all" || user.role === roleFilter), [users, roleFilter]);
  const matchingUsers = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return roleUsers.filter((user) => !needle || `${user.name ?? ""} ${user.username}`.toLocaleLowerCase().includes(needle));
  }, [roleUsers, query]);
  const visibleUsers = matchingUsers.filter((user) => statusFilter === "all" || (statusFilter === "active" ? user.active : !user.active));
  const pageCount = Math.max(1, Math.ceil(visibleUsers.length / pageSize));
  const pageUsers = visibleUsers.slice((page - 1) * pageSize, page * pageSize);
  const columns: Column<AdminUser>[] = [
     { key: "username", header: "Usuario", render: (user) => <div className="table__resource"><Avatar name={user.name ?? user.username} /><a className="table__resource-name" href={pathForRoute({ view: "users", userId: user.id })} onClick={onOpenUser ? (event) => { event.preventDefault(); onOpenUser(user.id); } : undefined}>{user.name ?? user.username}</a>{user.username === currentUser.username ? <Badge tone="neutral">Tú</Badge> : null}</div> },
     { key: "role", header: "Rol", render: (user) => <span className="table__role"><Icon icon={roleIcons[user.role]} />{roleLabels[user.role]}</span> },
    { key: "active", header: "Estado", render: (user) => <StatusBadge status={user.active ? "closed" : "pending"} label={user.active ? "Activo" : "Inactivo"} /> },
  ];

  return <PageFrame title="Usuarios" meta="Administra el acceso al panel" actions={<Button onClick={() => { setMutationState(null); setCreateOpen(true); }}>Nuevo usuario</Button>} state={state}>
    {data.state === "empty" || (data.state === "ready" && users.length === 0) ? <p>No hay usuarios</p> : <>
      <Tabs ariaLabel="Filtrar por estado" activeTab={statusFilter} onTabChange={(value) => { setStatusFilter(value); setPage(1); }} tabs={[{ id: "all", label: `Todos ${matchingUsers.length}` }, { id: "active", label: `Activos ${matchingUsers.filter((user) => user.active).length}` }, { id: "inactive", label: `Inactivos ${matchingUsers.filter((user) => !user.active).length}` }]}>
        {() => <div className="table-card">
          <section className="table-toolbar" aria-label="Filtros de usuarios">
            <SearchInput aria-label="Buscar usuarios" placeholder="Buscar por nombre de usuario…" onSearch={(value) => { setQuery(value); setPage(1); }} />
            <div className="table-toolbar__select"><Icon icon={SlidersHorizontal} /><Select label="Filtrar por rol" size="sm" value={roleFilter} options={[{ value: "all", label: "Todos los roles" }, { value: "admin", label: roleLabels.admin }, { value: "operador", label: roleLabels.operador }, { value: "tecnico", label: roleLabels.tecnico }]} onChange={(event) => { setRoleFilter(event.target.value as Role | "all"); setPage(1); }} /></div>
          </section>
          <DataTable columns={columns} rows={pageUsers} rowKey={(user) => String(user.id)} actions={(user) => user.username === currentUser.username ? <span className="table__actions-unavailable"><Icon icon={LockKeyhole} size="sm" /> Acciones no disponibles</span> : <Menu label={`Acciones para ${user.name ?? user.username}`} trigger="icon" items={[{ value: "toggle", label: user.active ? "Desactivar usuario" : "Activar usuario", icon: UserRoundMinus, disabled: busyId === user.id }, { value: "reset", label: "Restablecer contraseña", icon: KeyRound, disabled: busyId === user.id }]} onSelect={(value) => { if (value === "toggle") void toggle(user); else { setResetTarget(user); setResetDraft(""); setResetDone(false); setMutationState(null); } }} />} />
          <footer className="table-footer"><span>Mostrando {pageUsers.length} de {visibleUsers.length} usuarios</span><div className="table-footer__pagination"><Button variant="secondary" aria-label="Anterior" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>‹</Button><span className="table-footer__page" aria-current="page">{page}</span><Button variant="secondary" aria-label="Siguiente" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>›</Button></div></footer>
        </div>}
      </Tabs>
    </>}
    <Dialog open={createOpen} onClose={() => { setCreateOpen(false); setMutationState(null); }} title="Nuevo usuario">
      <form onSubmit={submit}>
        <Input label="Usuario" value={username} onChange={(event) => setUsername(event.target.value)} />
        <Input label="Contraseña" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <label>Rol<select aria-label="Rol" value={role} onChange={(event) => setRole(event.target.value as Role)}><option value="operador">Operador</option><option value="tecnico">Técnico</option><option value="admin">Administrador</option></select></label>
        {mutationState && !resetTarget ? <StateMessage {...mutationState} role={mutationState.tone === "danger" ? "alert" : "status"} /> : null}
        <Button type="submit">Crear usuario</Button>
      </form>
    </Dialog>
    <Dialog open={resetTarget !== null} onClose={closeReset} title="Restablecer contraseña">
      {resetTarget ? <>
        <p>Define una nueva contraseña para {resetTarget.name ?? resetTarget.username}.</p>
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
