import { useCallback, useEffect, useState, type FormEvent } from "react";
import { FileText, Folder, Pencil, Trash2, Archive, RotateCcw, ArrowRightLeft, ExternalLink } from "lucide-react";
import { ApiError, archiveProject, createProject, deleteProject, getProject, getProjectDeletionImpact, listProjects, moveProjectFiles, reactivateProject, renameProject, updateProjectConfig } from "../../api";
import type { Project, ProjectCandidate, ProjectDeleteCounts, ProjectDetailResponse, ProjectsResponse, Role } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { useToast } from "../primitives/Toast";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { DataTable } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { projectStatusLabel, projectStatusTone } from "../shared/toneMaps";
import { Tabs } from "../primitives/Tabs";
import { Dialog } from "../primitives/Dialog";
import { Menu } from "../primitives/Menu";
import { ProjectResources } from "./ProjectResources";
import { ProjectSkills } from "./ProjectSkills";
import { ProjectAgents } from "./ProjectAgents";
import { ProjectThreads } from "./ProjectThreads";
import "./ProjectsPage.css";

export function ProjectDeletionConfirmation({ project, busy, error, onConfirm }: { project: Project; busy: boolean; error: string | null; onConfirm: () => void }) {
  const [impact, setImpact] = useState<ProjectDeleteCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [typedName, setTypedName] = useState("");
  useEffect(() => {
    let current = true;
    setLoading(true);
    setLoadError(false);
    setImpact(null);
    void getProjectDeletionImpact(project.slug).then(({ impact: counts }) => {
      if (current) setImpact(counts);
    }).catch(() => {
      if (current) setLoadError(true);
    }).finally(() => {
      if (current) setLoading(false);
    });
    return () => { current = false; };
  }, [project.slug, retry]);
  const labels: [keyof ProjectDeleteCounts, string][] = [["threads", "Hilos"], ["messages", "Mensajes"], ["files", "Archivos"], ["folders", "Carpetas"], ["memories", "Memorias"], ["kb_documents", "Documentos de KB"], ["kb_chunks", "Chunks de KB"], ["artifacts", "Artefactos"], ["attachments", "Adjuntos"]];
  return <div className="projects-page__action-dialog">
    <p>Se eliminarán definitivamente {project.name}. Esta acción no se puede deshacer.</p>
    <p className="projects-page__delete-warning" role="alert">No se puede deshacer. Se perderán los datos enumerados a continuación.</p>
    {loading ? <p role="status">Cargando información de eliminación…</p> : null}
    {loadError ? <div role="alert">No pudimos cargar la información de eliminación. <Button variant="secondary" onClick={() => setRetry((value) => value + 1)}>Reintentar</Button></div> : null}
    {impact ? <ul className="projects-page__delete-impact" aria-label="Información de eliminación">{labels.map(([key, label]) => <li key={key}>{label}: {impact[key]}</li>)}</ul> : null}
    <Input label={`Escribe ${project.name}`} value={typedName} onChange={(event) => setTypedName(event.target.value)} />
    {error ? <p role="alert">{error}</p> : null}
    <Button variant="danger" disabled={busy || loading || loadError || !impact || typedName !== project.name} onClick={onConfirm}>{busy ? "Procesando…" : "Eliminar proyecto"}</Button>
  </div>;
}

export function ProjectsPage({ projectSlug, onOpenProject, onOpenChat, onOpenThread, onOpenHistory, data, state, role, embedded = false }: { projectSlug?: string; onOpenProject?: (slug: string) => void; onOpenChat?: (slug: string) => void; onOpenThread?: (threadId: number, slug: string) => void; onOpenHistory?: (slug: string) => void; data?: ProjectsResponse; state?: AsyncDataState; role?: Role; embedded?: boolean }) {
  const toast = useToast();
  const [form, setForm] = useState({ slug: "", name: "", purpose: "" });
  const [createdProjects, setCreatedProjects] = useState<ProjectsResponse | null>(null);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"active" | "archived" | "all">("active");
  const [query, setQuery] = useState("");
  const [actionTarget, setActionTarget] = useState<{ action: "rename" | "archive" | "reactivate" | "move" | "delete"; project: Project } | null>(null);
  const [actionValue, setActionValue] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [savingInstructions, setSavingInstructions] = useState(false);
  const load = useCallback(() => listProjects(), []);
  const fetched = useAsyncData(load, data === undefined);
  const detailLoad = useCallback(() => getProject(projectSlug!), [projectSlug]);
  const detail = useAsyncData(detailLoad, projectSlug !== undefined);
  const body = detail.data as ProjectDetailResponse | null;
  useEffect(() => {
    setInstructions(body?.project.config?.instructions ?? "");
  }, [body?.project.slug, body?.project.config?.instructions]);
  const saveInstructions = async () => {
    setSavingInstructions(true);
    try {
      await updateProjectConfig(projectSlug!, { instructions });
      toast.show("Instrucciones guardadas.");
    } catch (reason: unknown) {
      toast.show(reason instanceof ApiError ? reason.detail : "No pudimos guardar las instrucciones.", "danger");
    } finally {
      setSavingInstructions(false);
    }
  };
  if (projectSlug) {
    const notFound = detail.state === "error" && detail.error instanceof ApiError && detail.error.status === 404;
    return <PageFrame className={embedded ? "projects-page--embedded" : undefined} title={body?.project.name ?? "Proyecto"} titleIcon={body ? Folder : undefined} titleAdornment={body ? <Badge tone={projectStatusTone(body.project.status)}>{projectStatusLabel(body.project.status)}</Badge> : null} subtitle={body ? body.project.purpose : "Detalle del proyecto"} actions={embedded ? null : <><Button variant="secondary" onClick={() => onOpenChat?.(body?.project.slug ?? projectSlug)}>Abrir asistente</Button><Button variant="secondary" onClick={() => window.history.back()}>Volver a proyectos</Button></>} state={detail.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyecto" /> : notFound ? <StateMessage tone="warning" role="alert" title="No encontramos este proyecto" detail="Revisa el enlace o vuelve a la lista de proyectos." /> : detail.state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el proyecto" detail="Intenta cargar el proyecto nuevamente más tarde." /><Button variant="secondary" onClick={detail.retry}>Reintentar</Button></> : undefined}>
      {body ? <Tabs ariaLabel="Secciones del proyecto" tabs={[{ id: "context", label: "Contexto" }, { id: "threads", label: "Hilos" }, { id: "agents", label: "Agentes" }, { id: "skills", label: "Skills" }]}>{(active) => {
        if (active === "threads") return <ProjectThreads projectSlug={body.project.slug} projectName={body.project.name} onOpenThread={onOpenThread} onOpenHistory={onOpenHistory} />;
        if (active === "agents") return <ProjectAgents projectSlug={body.project.slug} />;
        if (active === "skills") return <ProjectSkills projectSlug={body.project.slug} role={role} skills={body.project.config?.skills ?? []} />;
        return <div className="projects-page__context">
          <Card icon={FileText} title="Instrucciones del proyecto" description="Define el contexto compartido por el asistente." footer={<Button disabled={savingInstructions} onClick={() => void saveInstructions()}>{savingInstructions ? "Guardando…" : "Guardar cambios"}</Button>}>
            <Input label="Nombre del proyecto" value={body.project.name} disabled onChange={() => undefined} />
            <Textarea label="Propósito" value={body.project.purpose} disabled onChange={() => undefined} />
            <Textarea label="Instrucciones del proyecto" placeholder="Describe cómo debe trabajar el asistente en este proyecto…" value={instructions} onChange={(event) => setInstructions(event.target.value)} />
            <p className="projects-page__hint">Estas instrucciones forman parte del contexto del proyecto.</p>
          </Card>
          <ProjectResources projectSlug={body.project.slug} projectId={body.project.id} projectName={body.project.name} role={role} />
        </div>;
      }}</Tabs> : null}
    </PageFrame>;
  }
  const projects = data ?? fetched.data;
  const currentState = state ?? (data ? "ready" : fetched.state);
  const create = async (event: FormEvent) => {
    event.preventDefault();
    setCreating(true);
    try {
      let created: Project;
      try {
        created = (await createProject(form)).project;
      } catch (reason: unknown) {
        const detail = reason instanceof ApiError ? reason.detail : "No pudimos crear el proyecto";
        const candidates = reason instanceof ApiError && Array.isArray(reason.structuredDetail?.candidates)
          ? reason.structuredDetail.candidates as ProjectCandidate[]
          : [];
        const candidateDetails = candidates.map((candidate) => `${candidate.name} (${candidate.slug}) · ${candidate.similarity}`).join("; ");
        toast.show(candidateDetails ? `${detail}: ${candidateDetails}` : detail, "danger");
        return;
      }
      setForm({ slug: "", name: "", purpose: "" });
      setCreateOpen(false);
      toast.show("Proyecto creado.");
      try {
        setCreatedProjects(await listProjects());
      } catch {
        // The refresh is best-effort: the project was created, so a list failure
        // must neither read as a creation error nor hide the new project.
        setCreatedProjects({ projects: [...(createdProjects ?? projects)?.projects ?? [], created] });
      }
    } finally {
      setCreating(false);
    }
  };
  const allProjects = createdProjects ?? projects;
  const filteredProjects = (allProjects?.projects ?? []).filter((project) =>
    (statusFilter === "all" || project.status === statusFilter) && project.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())
  );
  const runAction = async () => {
    if (!actionTarget) return;
    setActionBusy(true); setActionError(null);
    try {
      const { action, project } = actionTarget;
      if (action === "rename") await renameProject(project.slug, actionValue);
      else if (action === "archive") await archiveProject(project.slug);
      else if (action === "reactivate") await reactivateProject(project.slug);
      else if (action === "move") await moveProjectFiles(project.slug, actionValue);
      else await deleteProject(project.slug);
      setActionTarget(null); setActionValue(""); setCreatedProjects(await listProjects());
    } catch (error: unknown) {
      setActionError(error instanceof ApiError ? error.detail : "No pudimos completar la acción.");
    } finally { setActionBusy(false); }
  };
  const actionTitle = actionTarget?.action === "rename" ? "Renombrar proyecto" : actionTarget?.action === "move" ? "Mover contexto y archivos" : actionTarget?.action === "delete" ? "Eliminar proyecto" : actionTarget?.action === "archive" ? "Archivar proyecto" : "Reactivar proyecto";
  return <PageFrame title="Proyectos" subtitle="Administra los espacios de trabajo del asistente." actions={<Button onClick={() => { setForm({ slug: "", name: "", purpose: "" }); setCreateOpen(true); }}>Nuevo proyecto</Button>} state={currentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyectos" /> : currentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los proyectos" /> : undefined}>
    <section className="projects-page__registry" aria-label="Administrar proyectos">
      <div className="projects-page__toolbar">
        <label>Estado <select aria-label="Filtrar por estado" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "active" | "archived" | "all")}><option value="active">Activos</option><option value="archived">Archivados</option><option value="all">Todos</option></select></label>
        <Input label="Buscar por nombre" value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      {!allProjects ? null : allProjects.projects.length === 0 ? <EmptyState title="No hay proyectos" description="Crea un proyecto para comenzar." /> : filteredProjects.length === 0 ? <EmptyState title="No encontramos proyectos" description="Cambia el filtro o prueba con otro nombre." /> : <DataTable rows={filteredProjects} rowKey={(project) => project.slug} actionsHeader="Acciones" actions={(project) => <Menu label={`Acciones de ${project.name}`} trigger="icon" align="end" items={[{ value: "open", label: "Abrir", icon: ExternalLink }, { value: "rename", label: "Renombrar", icon: Pencil }, { value: project.status === "active" ? "archive" : "reactivate", label: project.status === "active" ? "Archivar" : "Reactivar", icon: project.status === "active" ? Archive : RotateCcw }, { value: "move", label: "Mover contexto y archivos", icon: ArrowRightLeft }, ...(project.slug === "default" ? [] : [{ value: "delete", label: "Eliminar", icon: Trash2, tone: "danger" as const }])]} onSelect={(value) => { if (value === "open") onOpenProject?.(project.slug); else { setActionValue(value === "rename" ? project.name : ""); setActionError(null); setActionTarget({ action: value as NonNullable<typeof actionTarget>["action"], project }); } }} />} columns={[{ key: "name", header: "Proyecto", render: (project) => <Button variant="tertiary" onClick={() => onOpenProject?.(project.slug)}>{project.name}</Button> }, { key: "purpose", header: "Propósito", render: (project) => project.purpose }, { key: "status", header: "Estado", render: (project) => <Badge tone={projectStatusTone(project.status)}>{projectStatusLabel(project.status)}</Badge> }]} />}
    </section>
    <Dialog open={createOpen} onClose={() => setCreateOpen(false)} title="Nuevo proyecto"><form onSubmit={(event) => void create(event)} className="projects-page__form"><Input label="Slug" maxLength={100} required value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} /><Input label="Nombre" maxLength={200} required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /><Textarea label="Propósito" maxLength={500} required value={form.purpose} onChange={(event) => setForm({ ...form, purpose: event.target.value })} /><Button type="submit" disabled={creating}>{creating ? "Creando…" : "Crear proyecto"}</Button></form></Dialog>
    <Dialog open={actionTarget !== null} onClose={() => { setActionTarget(null); setActionError(null); }} title={actionTitle ?? "Acción del proyecto"}>
      {actionTarget ? actionTarget.action === "delete" ? <ProjectDeletionConfirmation project={actionTarget.project} busy={actionBusy} error={actionError} onConfirm={() => void runAction()} /> : <div className="projects-page__action-dialog">{actionTarget.action === "rename" ? <Input label="Nombre del proyecto" value={actionValue} onChange={(event) => setActionValue(event.target.value)} /> : actionTarget.action === "move" ? <><p>Mover los archivos y carpetas de {actionTarget.project.name}; los hilos no se moverán.</p><label>Proyecto destino<select aria-label="Proyecto destino" value={actionValue} onChange={(event) => setActionValue(event.target.value)}><option value="">Selecciona un proyecto</option>{(allProjects?.projects ?? []).filter((project) => project.status === "active" && project.slug !== actionTarget.project.slug).map((project) => <option key={project.slug} value={project.slug}>{project.name}</option>)}</select></label></> : <p>{actionTarget.action === "archive" ? <>El proyecto {actionTarget.project.name} dejará de aparecer en el worktree.</> : <>El proyecto {actionTarget.project.name} volverá a aparecer en el worktree.</>}</p>}{actionError ? <p role="alert">{actionError}</p> : null}<Button variant="primary" disabled={actionBusy || (actionTarget.action === "rename" && !actionValue.trim()) || (actionTarget.action === "move" && !actionValue)} onClick={() => void runAction()}>{actionBusy ? "Procesando…" : actionTarget.action === "rename" ? "Guardar nombre" : actionTarget.action === "move" ? "Mover archivos" : actionTarget.action === "archive" ? "Archivar proyecto" : "Reactivar proyecto"}</Button></div> : null}
    </Dialog>
  </PageFrame>;
}
