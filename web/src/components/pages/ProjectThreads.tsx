import { useCallback, useMemo, useState } from "react";
import { ArrowUpRight, Clock, History, Info, MessageSquare, Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError, createChatThread, deleteChatThread, listChatThreads, renameChatThread } from "../../api";
import type { InternalChatThreadSummary } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { useToast } from "../primitives/Toast";
import { StateMessage } from "../shared/StateMessage";
import { formatThreadActivity } from "./threadDateGroups";

type SortKey = "recent" | "oldest" | "title";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "recent", label: "Más recientes" },
  { value: "oldest", label: "Más antiguos" },
  { value: "title", label: "Título (A–Z)" },
];

const PAGE_SIZE = 20;

function activityTime(thread: InternalChatThreadSummary): number {
  const value = thread.updated_at || thread.created_at;
  const time = value ? new Date(value).getTime() : Number.NEGATIVE_INFINITY;
  return Number.isNaN(time) ? Number.NEGATIVE_INFINITY : time;
}

export function ProjectThreads({
  projectSlug,
  projectName,
  onOpenThread,
  onOpenHistory,
}: {
  projectSlug: string;
  projectName: string;
  onOpenThread?: (threadId: number, projectSlug: string) => void;
  onOpenHistory?: (projectSlug: string) => void;
}) {
  const load = useCallback(() => listChatThreads(50, projectSlug), [projectSlug]);
  const result = useAsyncData(load, true);
  const threads = useMemo(() => result.data?.threads ?? [], [result.data]);
  const toast = useToast();

  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("recent");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [renameTarget, setRenameTarget] = useState<InternalChatThreadSummary | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<InternalChatThreadSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const normalized = query.trim().toLocaleLowerCase("es-CL");
  const visible = threads
    .filter((thread) => !normalized || `${thread.title ?? ""} ${thread.preview ?? ""}`.toLocaleLowerCase("es-CL").includes(normalized))
    .sort((a, b) => sort === "title"
      ? (a.title ?? "Sin título").localeCompare(b.title ?? "Sin título", "es-CL")
      : sort === "oldest" ? activityTime(a) - activityTime(b) : activityTime(b) - activityTime(a));
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageThreads = visible.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const openThread = (thread: InternalChatThreadSummary) => onOpenThread?.(thread.id, projectSlug);
  const openHistory = () => onOpenHistory?.(projectSlug);

  const createThread = async () => {
    setCreating(true);
    try {
      const created = await createChatThread(projectSlug);
      onOpenThread?.(created.thread.id, projectSlug);
    } catch (reason: unknown) {
      toast.show(reason instanceof ApiError ? reason.detail : "No pudimos crear el hilo.", "danger");
    } finally {
      setCreating(false);
    }
  };

  const openRename = (thread: InternalChatThreadSummary) => { setActionError(null); setRenameTarget(thread); setRenameTitle(thread.title ?? ""); };
  const openDelete = (thread: InternalChatThreadSummary) => { setActionError(null); setDeleteTarget(thread); };
  const closeActions = () => { setRenameTarget(null); setDeleteTarget(null); setActionError(null); };

  const submitRename = async () => {
    const target = renameTarget;
    if (!target) return;
    setBusy(true);
    setActionError(null);
    try {
      await renameChatThread(target.id, renameTitle.trim());
      closeActions();
      toast.show("Hilo renombrado.");
      result.retry();
    } catch (reason: unknown) {
      setActionError(reason instanceof ApiError ? reason.detail : "No pudimos renombrar el hilo.");
    } finally {
      setBusy(false);
    }
  };

  const submitDelete = async () => {
    const target = deleteTarget;
    if (!target) return;
    setBusy(true);
    setActionError(null);
    try {
      await deleteChatThread(target.id);
      closeActions();
      toast.show("Hilo eliminado.");
      result.retry();
    } catch (reason: unknown) {
      setActionError(reason instanceof ApiError ? reason.detail : "No pudimos eliminar el hilo.");
    } finally {
      setBusy(false);
    }
  };

  const emptyVisual = (
    <div className="project-threads__empty">
      <span className="project-threads__empty-icon" aria-hidden="true">
        <Icon icon={MessageSquare} />
        <Icon icon={Clock} size="sm" className="project-threads__empty-clock" />
      </span>
      <p className="project-threads__empty-title">Aún no hay hilos en este proyecto</p>
      <p className="project-threads__empty-copy">Por ahora, consulta tus conversaciones desde el historial del asistente.</p>
      <Button onClick={openHistory}><Icon icon={History} size="sm" /> Abrir historial</Button>
      <p className="project-threads__empty-note">El historial del asistente reúne las conversaciones de todos tus proyectos.</p>
    </div>
  );

  const unavailableVisual = (
    <div className="project-threads__empty">
      <span className="project-threads__empty-icon" aria-hidden="true">
        <Icon icon={MessageSquare} />
        <Icon icon={Clock} size="sm" className="project-threads__empty-clock" />
      </span>
      <p className="project-threads__empty-title">Los hilos de este proyecto aún no están disponibles</p>
      <p className="project-threads__empty-copy">Por ahora, consulta tus conversaciones desde el historial del asistente.</p>
      <Button onClick={openHistory}><Icon icon={History} size="sm" /> Abrir historial</Button>
      <p className="project-threads__empty-note">El historial del asistente reúne las conversaciones de todos tus proyectos.</p>
    </div>
  );

  if (result.state === "loading") {
    return <div className="project-threads">
      <Card icon={MessageSquare} title="Hilos del proyecto" description={`Conversaciones asociadas a ${projectName}.`}>
        <StateMessage tone="info" role="status" spinner title="Cargando hilos" />
      </Card>
    </div>;
  }

  if (result.state === "denied" || result.state === "error") {
    return <div className="project-threads">
      <Card
        icon={MessageSquare}
        title="Hilos del proyecto"
        headerAction={<Badge>No disponible</Badge>}
        footer={<p className="projects-page__note"><Icon icon={Info} size="sm" />Esta vista estará disponible cuando sea posible asociar los hilos al proyecto.</p>}
      >
        {unavailableVisual}
        {result.state === "error" ? <div className="project-threads__retry"><Button variant="secondary" onClick={result.retry}>Reintentar</Button></div> : null}
      </Card>
    </div>;
  }

  if (threads.length === 0) {
    return <div className="project-threads">
      <Card icon={MessageSquare} title="Hilos del proyecto">{emptyVisual}</Card>
    </div>;
  }

  return <div className="project-threads">
    <Card
      icon={MessageSquare}
      title={`Hilos del proyecto (${threads.length})`}
      description={`Conversaciones asociadas a ${projectName}.`}
      headerAction={<Button disabled={creating} onClick={() => void createThread()}><Icon icon={Plus} size="sm" /> {creating ? "Creando…" : "Nuevo hilo"}</Button>}
    >
      <div className="project-threads__toolbar">
        <SearchInput aria-label="Buscar hilo" placeholder="Buscar hilo…" onSearch={(value) => { setQuery(value); setPage(1); }} />
        <label className="project-threads__sort">
          <Icon icon={Clock} size="sm" />
          <select aria-label="Ordenar hilos" value={sort} onChange={(event) => { setSort(event.target.value as SortKey); setPage(1); }}>
            {SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </div>

      {visible.length === 0 ? <p className="project-threads__no-match">No encontramos hilos. Prueba con otro nombre.</p> : <>
        <div className="project-threads__table">
          <div className="project-threads__head" aria-hidden="true"><span>Hilo</span><span>Última actividad</span><span>Acciones</span></div>
          <ul className="project-threads__list">
            {pageThreads.map((thread) => <li className="project-threads__row" key={thread.id}>
              <span className="project-threads__thread">
                <span className="project-threads__tile" aria-hidden="true"><Icon icon={MessageSquare} /></span>
                <span className="project-threads__copy">
                  <strong>{thread.title || "Sin título"}</strong>
                  {thread.preview ? <span>{thread.preview}</span> : null}
                </span>
              </span>
              <time className="project-threads__activity" dateTime={thread.updated_at ?? thread.created_at ?? undefined}>{formatThreadActivity(thread)}</time>
              <span className="project-threads__actions">
                <Button variant="secondary" onClick={() => openThread(thread)}><Icon icon={ArrowUpRight} size="sm" /> Abrir hilo</Button>
                <Menu
                  trigger="icon"
                  label={`Acciones de ${thread.title || "hilo"}`}
                  align="end"
                  items={[
                    { value: "rename", label: "Renombrar", icon: Pencil },
                    { value: "delete", label: "Eliminar hilo", icon: Trash2, tone: "danger" },
                  ]}
                  onSelect={(value) => (value === "rename" ? openRename(thread) : openDelete(thread))}
                />
              </span>
            </li>)}
          </ul>
        </div>
        <footer className="project-threads__footer">
          <span className="project-threads__count">{threads.length} {threads.length === 1 ? "hilo" : "hilos"}</span>
          {pageCount > 1 ? <nav className="project-threads__pagination" aria-label={`Paginación de hilos de ${projectName}`}>
            <span aria-live="polite">{currentPage} de {pageCount}</span>
            <Button variant="secondary" aria-label="Página anterior" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>«</Button>
            <Button variant="secondary" aria-label="Página siguiente" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>»</Button>
          </nav> : <span className="project-threads__pagination">1 de 1</span>}
        </footer>
      </>}
    </Card>

    <Dialog open={renameTarget !== null} onClose={closeActions} title="Renombrar hilo" icon={Pencil}>
      <Input label="Nombre del hilo" value={renameTitle} autoFocus error={actionError ?? undefined} onChange={(event) => setRenameTitle(event.target.value)} />
      <div className="project-threads__dialog-actions">
        <Button variant="secondary" onClick={closeActions}>Cancelar</Button>
        <Button disabled={busy || renameTitle.trim() === ""} onClick={() => void submitRename()}>{busy ? "Guardando…" : "Guardar"}</Button>
      </div>
    </Dialog>

    <Dialog open={deleteTarget !== null} onClose={closeActions} title="Eliminar hilo" icon={Trash2}>
      <p className="project-threads__dialog-question">¿Quieres eliminar este hilo? Esta acción no se puede deshacer.</p>
      {actionError ? <StateMessage tone="danger" role="alert" title={actionError} /> : null}
      <div className="project-threads__dialog-actions">
        <Button variant="secondary" onClick={closeActions}>Cancelar</Button>
        <Button variant="danger" disabled={busy} onClick={() => void submitDelete()}><Icon icon={Trash2} size="sm" /> {busy ? "Eliminando…" : "Eliminar hilo"}</Button>
      </div>
    </Dialog>
  </div>;
}
