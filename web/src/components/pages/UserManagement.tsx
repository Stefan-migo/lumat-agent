import { useCallback, useMemo, useState } from "react";
import { BriefcaseBusiness, ChevronRight, EllipsisVertical, KeyRound, LockKeyhole, Shield, ShieldCheck, SlidersHorizontal, Trash2, UserPlus, UserRound, UserRoundMinus, Wrench, X } from "lucide-react";
import { ApiError, createUser, deleteUser, fetchUsers, toggleUserActive } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { AdminUser, Role, User } from "../../types";
import { roleLabels } from "../../roleLabels";
import { Button } from "../primitives/Button";
import { Pagination } from "../primitives/Pagination";
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
import { ResetPasswordDialog } from "../shared/ResetPasswordDialog";

const roleIcons = { admin: ShieldCheck, operador: BriefcaseBusiness, tecnico: Wrench } as const;
const pageSize = 10;

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.detail : fallback;
}

export interface UserManagementProps { currentUser: User; onOpenUser?: (id: number) => void; }

export function UserManagement({ currentUser, onOpenUser }: UserManagementProps) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState<Role>("operador");
  const [mutationState, setMutationState] = useState<{ tone: "success" | "danger" | "info"; title: string; detail?: string } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);
  const [actionTarget, setActionTarget] = useState<AdminUser | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
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
    if (password !== confirmPassword) { setMutationState({ tone: "danger", title: "Las contraseñas no coinciden" }); return; }
    setMutationState({ tone: "info", title: "Creando usuario" });
    try {
      await createUser({ username: username.trim(), password, role });
      setUsername(""); setPassword(""); setConfirmPassword("");
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

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setBusyId(deleteTarget.id);
    setDeleteError(null);
    try {
      await deleteUser(deleteTarget.id);
      setDeleteTarget(null);
      setMutationState({ tone: "success", title: "Usuario eliminado" });
      setRefreshKey((value) => value + 1);
    } catch (error) {
      setDeleteError(errorMessage(error, "No pudimos eliminar el usuario"));
    } finally {
      setBusyId(null);
    }
  };

  const closeReset = () => {
    setResetTarget(null);
    setMutationState(null);
  };

  const state = data.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando usuarios" />
    : data.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />
    : data.state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los usuarios" detail="Intenta nuevamente en unos minutos." />
    : mutationState && !createOpen ? <StateMessage {...mutationState} role={mutationState.tone === "danger" ? "alert" : "status"} /> : null;
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

  return <PageFrame title="Usuarios" meta="Administra el acceso al panel" actions={<Button onClick={() => { setMutationState(null); setCreateOpen(true); }}><Icon icon={UserPlus} /> Nuevo usuario</Button>} state={state}>
    {data.state === "empty" || (data.state === "ready" && users.length === 0) ? <p>No hay usuarios</p> : <>
      <Tabs ariaLabel="Filtrar por estado" activeTab={statusFilter} onTabChange={(value) => { setStatusFilter(value); setPage(1); }} tabs={[{ id: "all", label: `Todos ${matchingUsers.length}` }, { id: "active", label: `Activos ${matchingUsers.filter((user) => user.active).length}` }, { id: "inactive", label: `Inactivos ${matchingUsers.filter((user) => !user.active).length}` }]}>
        {() => <div className="table-card">
          <section className="table-toolbar" aria-label="Filtros de usuarios">
            <SearchInput aria-label="Buscar usuarios" placeholder="Buscar por nombre de usuario…" onSearch={(value) => { setQuery(value); setPage(1); }} />
            <div className="table-toolbar__select"><Icon icon={SlidersHorizontal} /><Select label="Filtrar por rol" value={roleFilter} options={[{ value: "all", label: "Todos los roles" }, { value: "admin", label: roleLabels.admin }, { value: "operador", label: roleLabels.operador }, { value: "tecnico", label: roleLabels.tecnico }]} onChange={(event) => { setRoleFilter(event.target.value as Role | "all"); setPage(1); }} /></div>
          </section>
           <div className="table-card__desktop"><DataTable columns={columns} rows={pageUsers} rowKey={(user) => String(user.id)} actions={(user) => user.username === currentUser.username ? <span className="table__actions-unavailable"><Icon icon={LockKeyhole} size="sm" /> Acciones no disponibles</span> : <Menu label={`Acciones para ${user.name ?? user.username}`} trigger="icon" items={[{ value: "toggle", label: user.active ? "Desactivar usuario" : "Activar usuario", icon: UserRoundMinus, disabled: busyId === user.id }, { value: "reset", label: "Restablecer contraseña", icon: KeyRound, disabled: busyId === user.id }, { value: "delete", label: "Eliminar usuario", icon: Trash2, tone: "danger", disabled: busyId === user.id }]} onSelect={(value) => { if (value === "toggle") void toggle(user); else if (value === "reset") { setResetTarget(user); setMutationState(null); } else { setDeleteTarget(user); setDeleteError(null); } }} />} /></div>
          <ul className="table-cards table-cards--mobile" aria-label="Lista de usuarios">
            {pageUsers.map((user) => <li className="table-card__item" key={user.id}>
              <Avatar name={user.name ?? user.username} />
              <div className="table-card__identity">
                <div className="table-card__name"><a className="table__resource-name" href={pathForRoute({ view: "users", userId: user.id })} onClick={onOpenUser ? (event) => { event.preventDefault(); onOpenUser(user.id); } : undefined}>{user.name ?? user.username}</a>{user.username === currentUser.username ? <Badge tone="neutral">Tú</Badge> : null}</div>
                <span className="table__role"><Icon icon={roleIcons[user.role]} />{roleLabels[user.role]}</span>
              </div>
              <div className="table-card__trailing">
                <StatusBadge status={user.active ? "closed" : "pending"} label={user.active ? "Activo" : "Inactivo"} />
                {user.username === currentUser.username ? <span className="table__actions-unavailable" aria-label="Acciones no disponibles"><Icon icon={LockKeyhole} size="sm" /></span> : <button type="button" className="table-card__action" aria-label={`Acciones para ${user.name ?? user.username}`} onClick={() => setActionTarget(user)}><Icon icon={EllipsisVertical} /></button>}
              </div>
            </li>)}
          </ul>
          <footer className="table-footer"><span className="table-footer__count">Mostrando {pageUsers.length} de {visibleUsers.length} usuarios</span><span className="table-footer__mobile-count">{visibleUsers.length} de {visibleUsers.length} usuarios</span><Pagination page={page} pageCount={pageCount} onPageChange={setPage} /></footer>
        </div>}
      </Tabs>
    </>}
    <Dialog open={actionTarget !== null} onClose={() => setActionTarget(null)} title="Acciones de usuario">
      {actionTarget ? <div className="user-mobile-actions">
        <span className="user-mobile-actions__handle" aria-hidden="true" />
        <div className="user-mobile-actions__header"><Avatar name={actionTarget.name ?? actionTarget.username} /><div className="user-mobile-actions__identity"><strong>{actionTarget.name ?? actionTarget.username}</strong><span>{roleLabels[actionTarget.role]} · <span className={actionTarget.active ? "user-mobile-actions__dot" : "user-mobile-actions__dot user-mobile-actions__dot--off"} aria-hidden="true" /> {actionTarget.active ? "Activo" : "Inactivo"}</span></div><button type="button" className="user-mobile-actions__close" aria-label="Cerrar" onClick={() => setActionTarget(null)}><Icon icon={X} /></button></div>
        <button type="button" className="user-mobile-actions__item" onClick={() => { setResetTarget(actionTarget); setMutationState(null); setActionTarget(null); }}><Icon icon={KeyRound} /><span>Restablecer contraseña<small>Actualizar el acceso a la cuenta</small></span><Icon icon={ChevronRight} size="sm" /></button>
         <button type="button" className="user-mobile-actions__item user-mobile-actions__item--danger" disabled={busyId === actionTarget.id} onClick={() => { void toggle(actionTarget); setActionTarget(null); }}><Icon icon={UserRoundMinus} /><span>{actionTarget.active ? "Desactivar usuario" : "Activar usuario"}<small>Impedir el acceso sin eliminar la cuenta</small></span><Icon icon={ChevronRight} size="sm" /></button>
         <button type="button" className="user-mobile-actions__item user-mobile-actions__item--danger" disabled={busyId === actionTarget.id} onClick={() => { setDeleteTarget(actionTarget); setDeleteError(null); setActionTarget(null); }}><Icon icon={Trash2} /><span>Eliminar usuario<small>Eliminar permanentemente la cuenta</small></span><Icon icon={ChevronRight} size="sm" /></button>
        <Button variant="secondary" onClick={() => setActionTarget(null)}>Cancelar</Button>
      </div> : null}
    </Dialog>
    <Dialog open={deleteTarget !== null} onClose={() => { if (busyId === null) { setDeleteTarget(null); setDeleteError(null); } }} title="Eliminar usuario" icon={Trash2} description={deleteTarget ? `Elimina a ${deleteTarget.name ?? deleteTarget.username} de forma permanente. No se puede deshacer.` : undefined}>
      {deleteError ? <StateMessage tone="danger" role="alert" title={deleteError} /> : null}
      <footer className="dialog-footer"><Button variant="secondary" disabled={busyId !== null} onClick={() => { setDeleteTarget(null); setDeleteError(null); }}>Cancelar</Button><Button variant="danger" disabled={busyId !== null} onClick={() => void confirmDelete()}><Icon icon={Trash2} />Eliminar usuario</Button></footer>
    </Dialog>
    <Dialog open={createOpen} onClose={() => { setCreateOpen(false); setMutationState(null); }} title="Nuevo usuario" icon={UserPlus} description="Crea una cuenta y asigna su rol de acceso.">
      <form className="user-dialog-form" onSubmit={submit}>
        <section className="dialog-section" aria-labelledby="access-heading">
          <h3 id="access-heading" className="dialog-section__title">Datos de acceso</h3>
          <Input label="Nombre de usuario" placeholder="Ej. mperez" icon={UserRound} helper="Se utilizará para iniciar sesión en Lumat." value={username} onChange={(event) => setUsername(event.target.value)} />
          <div className="dialog-field-pair">
            <Input label="Contraseña" type="password" revealable icon={LockKeyhole} value={password} onChange={(event) => setPassword(event.target.value)} />
            <Input label="Confirmar contraseña" type="password" revealable icon={LockKeyhole} placeholder="Repite la contraseña" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
          </div>
          <span className="field__helper">Usa una contraseña única y difícil de adivinar.</span>
        </section>
        <section className="dialog-section" aria-labelledby="permissions-heading">
          <h3 id="permissions-heading" className="dialog-section__title">Permisos</h3>
          <div className="user-role-field">
            <Icon icon={Shield} />
            <Select label="Rol de acceso" className="user-role-field__select" value={role} options={[{ value: "operador", label: "Operador" }, { value: "tecnico", label: "Técnico" }, { value: "admin", label: "Administrador" }]} onChange={(event) => setRole(event.target.value as Role)} />
            <span className="field__helper">El rol determina las funciones que podrá utilizar.</span>
          </div>
        </section>
        {mutationState && !resetTarget ? <StateMessage {...mutationState} role={mutationState.tone === "danger" ? "alert" : "status"} /> : null}
        <footer className="dialog-footer"><Button variant="secondary" onClick={() => { setCreateOpen(false); setMutationState(null); }}>Cancelar</Button><Button type="submit"><Icon icon={UserPlus} />Crear usuario</Button></footer>
      </form>
    </Dialog>
    <ResetPasswordDialog target={resetTarget} onClose={closeReset} onDone={() => setRefreshKey((value) => value + 1)} />
  </PageFrame>;
}
