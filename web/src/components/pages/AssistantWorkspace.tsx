import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, Download, FileText, Folder, FolderKanban, History, PanelRight, PanelLeft, Plus, X } from "lucide-react";
import { ApiError, createProject, deleteChatThread, downloadAssistantArtifact, listChatThreads, listProjects, renameChatThread } from "../../api";
import type { AssistantArtifact, AssistantAttachment, AssistantCapabilities, AssistantEvidence, AssistantPlan, InternalChatThreadSummary, Project } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { EmptyState } from "../shared/EmptyState";
import { Dialog } from "../primitives/Dialog";
import { StateMessage } from "../shared/StateMessage";
import { Input } from "../primitives/Input";
import { Textarea } from "../primitives/Textarea";
import { projectStatusLabel, projectStatusTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";
import "./AssistantWorkspace.css";

export function AssistantWorkspace({ children, onCreateThread, loadThreadTabs = true, attachments = [], artifacts = [], capabilities, capabilitiesLoading = false, capabilitiesError = false, evidence = [], plan, lifecycle, processing = false }: { children: ReactNode; onCreateThread: () => void; loadThreadTabs?: boolean; attachments?: AssistantAttachment[]; artifacts?: AssistantArtifact[]; capabilities?: AssistantCapabilities | null; capabilitiesLoading?: boolean; capabilitiesError?: boolean; evidence?: AssistantEvidence[]; plan?: AssistantPlan | null; lifecycle?: string | null; processing?: boolean }) {
  const [projectsVisible, setProjectsVisible] = useState(() => window.innerWidth > 1024);
  const [contextVisible, setContextVisible] = useState(() => window.innerWidth > 1024);
  const [search, setSearch] = useState("");
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [threads, setThreads] = useState<InternalChatThreadSummary[]>([]);
  const [threadListError, setThreadListError] = useState<string | null>(null);
  const [, setLocationKey] = useState(() => `${window.location.pathname}${window.location.search}`);
  const [renameTarget, setRenameTarget] = useState<InternalChatThreadSummary | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<InternalChatThreadSummary | null>(null);
  const [threadActionError, setThreadActionError] = useState<string | null>(null);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [projectPurpose, setProjectPurpose] = useState("");
  const [projectSlugEdited, setProjectSlugEdited] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState<string | null>(null);
  const [projectSubmitting, setProjectSubmitting] = useState(false);
  const [busyArtifactId, setBusyArtifactId] = useState<number | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const route = new URLSearchParams(window.location.search);
  const activeThreadId = Number(route.get("thread_id")) || undefined;
  const activeProjectSlug = route.get("proyecto") || selectedProject || undefined;
  const activeThread = threads.find((thread) => thread.id === activeThreadId);
  const downloadArtifact = async (artifact: AssistantArtifact) => {
    setBusyArtifactId(artifact.id);
    setArtifactError(null);
    try {
      await downloadAssistantArtifact(artifact.thread_id, artifact.id, artifact.filename);
    } catch (reason: unknown) {
      setArtifactError(reason instanceof ApiError ? reason.detail : "No pudimos descargar el artefacto.");
    } finally {
      setBusyArtifactId(null);
    }
  };
  const loadProjects = useCallback(() => listProjects(), []);
  const projectsData = useAsyncData(loadProjects, projectsVisible || Boolean(activeProjectSlug));
  const projects = projectsData.data?.projects ?? [];
  const activeProject = projects.find((project) => project.slug === activeProjectSlug);
  const visibleProjects = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return query ? projects.filter((project) => project.name.toLocaleLowerCase().includes(query)) : projects;
  }, [projects, search]);

  const refreshThreads = useCallback(async () => {
    try {
      const result = await listChatThreads(20);
      setThreads(result.threads ?? []);
      setThreadListError(null);
    } catch {
      setThreadListError("No pudimos cargar los hilos.");
    }
  }, []);

  useEffect(() => {
    if (!loadThreadTabs) return;
    void refreshThreads();
  }, [activeThreadId, loadThreadTabs, refreshThreads]);

  useEffect(() => {
    if (!loadThreadTabs) return;
    const onPopState = () => {
      setLocationKey(`${window.location.pathname}${window.location.search}`);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [loadThreadTabs]);

  const navigateToThread = (threadId: number) => {
    window.history.pushState({}, "", pathForRoute({
      view: "chat",
      ...(activeProjectSlug ? { projectSlug: activeProjectSlug } : {}),
      threadId,
    }));
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const renameThread = async () => {
    if (!renameTarget || !renameTitle.trim()) return;
    try {
      await renameChatThread(renameTarget.id, renameTitle.trim());
      setRenameTarget(null);
      setRenameTitle("");
      await refreshThreads();
    } catch {
      setThreadActionError("No pudimos renombrar el hilo.");
    }
  };

  const deleteThread = async () => {
    if (!deleteTarget) return;
    try {
      await deleteChatThread(deleteTarget.id);
      const remaining = threads.filter((thread) => thread.id !== deleteTarget.id);
      setThreads(remaining);
      setDeleteTarget(null);
      if (deleteTarget.id === activeThreadId) {
        if (remaining[0]) navigateToThread(remaining[0].id);
        else {
          window.history.pushState({}, "", pathForRoute({ view: "chat" }));
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
      }
    } catch {
      setThreadActionError("No pudimos eliminar el hilo.");
    }
  };

  const navigateToProject = (project: Project, destination: "context" | "threads") => {
    const route = destination === "context"
      ? { view: "projects" as const, projectSlug: project.slug }
      : { view: "chat" as const, projectSlug: project.slug };
    window.history.pushState({}, "", pathForRoute(route));
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const updateProjectName = (name: string) => {
    setProjectName(name);
    if (!projectSlugEdited) {
      setProjectSlug(name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-CL").trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
    }
  };

  const resetProjectForm = () => {
    setProjectName("");
    setProjectSlug("");
    setProjectPurpose("");
    setProjectSlugEdited(false);
    setProjectCreateError(null);
  };

  const submitProject = async () => {
    if (!projectName.trim() || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(projectSlug.trim()) || !projectPurpose.trim()) return;
    setProjectSubmitting(true);
    setProjectCreateError(null);
    try {
      const { project } = await createProject({ slug: projectSlug.trim(), name: projectName.trim(), purpose: projectPurpose.trim() });
      setCreateProjectOpen(false);
      resetProjectForm();
      setSearch("");
      setSelectedProject(project.slug);
      await projectsData.retry();
    } catch {
      setProjectCreateError("No pudimos crear el proyecto. Revisa los datos e inténtalo nuevamente.");
    } finally {
      setProjectSubmitting(false);
    }
  };

  return (
    <div
      className={`assistant-workspace${projectsVisible ? " assistant-workspace--projects-visible" : ""}${contextVisible ? " assistant-workspace--context-visible" : ""}`}
      data-testid="assistant-workspace"
    >
      {projectsVisible || contextVisible ? <button type="button" className="assistant-workspace__scrim" aria-label="Cerrar paneles" onClick={() => { setProjectsVisible(false); setContextVisible(false); }} /> : null}
      <aside
        id="assistant-workspace-projects"
        className="assistant-workspace__projects"
        aria-label="Proyectos"
        hidden={!projectsVisible}
      >
        <header className="assistant-workspace__pane-header">
          <h2>Proyectos</h2>
          <Button variant="tertiary" aria-label="Crear proyecto" title="Crear proyecto" onClick={() => { setProjectCreateError(null); setCreateProjectOpen(true); }}><Icon icon={Plus} /></Button>
        </header>
        <SearchInput aria-label="Buscar proyecto" placeholder="Buscar proyecto" onSearch={setSearch} />
        <div className="assistant-workspace__projects-list">
          {projectsData.state === "loading" ? (
            <StateMessage tone="info" role="status" spinner title="Cargando proyectos" />
          ) : projectsData.state === "error" || projectsData.state === "denied" ? (
            <>
              <StateMessage
                tone="danger"
                role="alert"
                title="No pudimos cargar los proyectos"
                detail={projectsData.state === "denied" ? "No tienes permiso para verlos." : undefined}
              />
              {projectsData.state === "error" ? <Button variant="secondary" onClick={projectsData.retry}>Reintentar</Button> : null}
            </>
          ) : projects.length === 0 ? (
            <EmptyState title="No hay proyectos" description="No hay espacios de proyecto registrados para mostrar." />
          ) : visibleProjects.length === 0 ? (
            <EmptyState title="No encontramos proyectos" description="Prueba con otro nombre." />
          ) : (
            visibleProjects.map((project) => {
              const expanded = selectedProject === project.slug;
              return (
                  <div className="assistant-workspace__project-card" key={project.slug}>
                  <div className={`assistant-workspace__project-row${expanded ? " is-selected" : ""}`}>
                    <button
                      type="button"
                      className="assistant-workspace__project-select"
                      aria-label={`${expanded ? "Contraer" : "Expandir"} ${project.name}`}
                      aria-expanded={expanded}
                      onClick={() => setSelectedProject(expanded ? null : project.slug)}
                    >
                      <Icon icon={expanded ? ChevronDown : ChevronRight} size="sm" />
                      <Icon icon={Folder} size="sm" />
                      <span>{project.name}</span>
                    </button>
                  </div>
                  {expanded ? (
                    <div className="assistant-workspace__project-details">
                      <nav aria-label={`Navegación de ${project.name}`}>
                        <a href={pathForRoute({ view: "projects", projectSlug: project.slug })} onClick={(event) => { event.preventDefault(); navigateToProject(project, "context"); }}><Icon icon={FileText} size="sm" />Contexto y archivos</a>
                        <a href={pathForRoute({ view: "chat", projectSlug: project.slug })} onClick={(event) => { event.preventDefault(); navigateToProject(project, "threads"); }}><Icon icon={History} size="sm" />Historial de hilos</a>
                      </nav>
                    </div>
                  ) : null}
                </div>
              );
            })
          )}
        </div>
        <Dialog open={createProjectOpen} onClose={() => { setCreateProjectOpen(false); resetProjectForm(); }} title="Crear proyecto">
          <div className="assistant-workspace__thread-dialog">
            <Input label="Nombre" value={projectName} onChange={(event) => updateProjectName(event.target.value)} autoComplete="off" />
            <Input label="Slug" value={projectSlug} onChange={(event) => { setProjectSlugEdited(true); setProjectSlug(event.target.value); }} autoComplete="off" />
            <Textarea label="Propósito" value={projectPurpose} onChange={(event) => setProjectPurpose(event.target.value)} />
            {projectCreateError ? <p role="alert">{projectCreateError}</p> : null}
            <Button onClick={() => void submitProject()} disabled={projectSubmitting || !projectName.trim() || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(projectSlug.trim()) || !projectPurpose.trim()}>
              {projectSubmitting ? "Creando…" : "Crear proyecto"}
            </Button>
          </div>
        </Dialog>
        <section className="assistant-workspace__agents" aria-label="Agentes del proyecto">
          <header><h3>Agentes del proyecto</h3><span aria-label="Cantidad no disponible">—</span><Button variant="tertiary" aria-label="Agregar agente" disabled><Icon icon={Plus} /></Button></header>
          <EmptyState title="No hay agentes disponibles" description="La gestión de agentes por proyecto todavía no está disponible." />
        </section>
      </aside>

      <section className="assistant-workspace__thread" aria-label="Área del hilo">
        <nav className="assistant-workspace__thread-tabs" aria-label="Hilos recientes">
          <div className="assistant-workspace__thread-tab-list">
            {threads.map((thread) => (
              <div className="assistant-workspace__thread-tab" key={thread.id} data-active={thread.id === activeThreadId}>
                <button type="button" aria-current={thread.id === activeThreadId ? "page" : undefined} onClick={() => navigateToThread(thread.id)}>
                  {thread.title || "Sin título"}
                </button>
                <button type="button" className="assistant-workspace__thread-close" aria-label={`Cerrar ${thread.title || "hilo"}`} onClick={() => { setThreadActionError(null); setDeleteTarget(thread); }}>
                  <Icon icon={X} size="sm" />
                </button>
              </div>
            ))}
          </div>
          <Button variant="tertiary" aria-label="Crear nuevo hilo" title="Crear nuevo hilo" onClick={onCreateThread}>
            <Icon icon={Plus} />
          </Button>
        </nav>
        {threadListError ? <StateMessage tone="danger" role="alert" title={threadListError} /> : null}
        <header className="assistant-workspace__thread-header">
          <div>
            <h1>{activeThread?.title || (activeThreadId ? "Sin título" : "Asistente Lumat")}</h1>
            {activeProject ? <p>Proyecto: {activeProject.name}</p> : null}
          </div>
          <div className="assistant-workspace__header-actions">
          <button type="button" className="assistant-workspace__pane-toggle" aria-label="Mostrar u ocultar proyectos" aria-expanded={projectsVisible} aria-controls="assistant-workspace-projects" onClick={() => setProjectsVisible((visible) => !visible)}><Icon icon={projectsVisible ? PanelLeft : FolderKanban} /></button>
          <button type="button" className="assistant-workspace__pane-toggle" aria-label="Mostrar u ocultar el panel de contexto" aria-expanded={contextVisible} aria-controls="assistant-workspace-context" onClick={() => setContextVisible((visible) => !visible)}><Icon icon={PanelRight} /></button>
          {activeThread ? (
            <Menu
              label="Acciones del hilo"
              trigger="icon"
              items={[{ value: "rename", label: "Renombrar" }, { value: "delete", label: "Eliminar", tone: "danger" }]}
              onSelect={(value) => {
                setThreadActionError(null);
                if (value === "rename") { setRenameTarget(activeThread); setRenameTitle(activeThread.title ?? ""); }
                else setDeleteTarget(activeThread);
              }}
            />
          ) : null}
          </div>
        </header>
        {threadActionError ? <StateMessage tone="danger" role="alert" title={threadActionError} /> : null}
        <Dialog open={renameTarget !== null} onClose={() => setRenameTarget(null)} title="Renombrar hilo">
          <div className="assistant-workspace__thread-dialog">
            <label htmlFor="workspace-thread-title">Nombre del hilo</label>
            <input id="workspace-thread-title" value={renameTitle} onChange={(event) => setRenameTitle(event.target.value)} />
            <Button onClick={() => void renameThread()} disabled={!renameTitle.trim()}>Guardar nombre</Button>
          </div>
        </Dialog>
        <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)} title="Eliminar hilo">
          <div className="assistant-workspace__thread-dialog">
            <p>¿Eliminar “{deleteTarget?.title || "Sin título"}”? Esta acción no se puede deshacer.</p>
            <Button onClick={() => void deleteThread()}>Eliminar hilo</Button>
          </div>
        </Dialog>
        {children}
      </section>

      <aside
        id="assistant-workspace-context"
        className="assistant-workspace__context"
        aria-label="Contexto del hilo"
        hidden={!contextVisible}
      >
        <h2>Actividad del hilo</h2>
        <Tabs
          ariaLabel="Panel del hilo"
          tabs={[{ id: "context", label: "Contexto" }, { id: "activity", label: "Actividad" }]}
        >
          {(tab) => tab === "context" ? <div className="assistant-workspace__context-content">
            <Card title="Proyecto">
              {activeProject ? <><p>{activeProject.name}</p><p>{activeProject.purpose}</p><Badge tone={projectStatusTone(activeProject.status)}>{projectStatusLabel(activeProject.status)}</Badge></> : <EmptyState title="Elige un proyecto" description="Selecciona un proyecto para ver su contexto." />}
            </Card>
            <Card title="Recursos del proyecto"><EmptyState title="Elegir del proyecto" description="La selección de recursos del proyecto todavía no está disponible." /></Card>
            <Card title="Capacidades del asistente">
              {capabilitiesLoading ? <StateMessage tone="info" role="status" spinner title="Cargando capacidades" /> : capabilitiesError ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las capacidades del asistente" /> : capabilities ? <><p>{capabilities.tools?.length ?? 0} herramientas disponibles</p><p>Base de conocimientos: {capabilities.kb_available ? "Disponible" : "No disponible"}</p></> : <EmptyState title="Capacidades no disponibles" description="No hay información de capacidades para mostrar." />}
            </Card>
            <Card title="Archivos del hilo">{attachments.length ? <ul>{attachments.map((attachment) => <li key={attachment.id}>{attachment.filename}</li>)}</ul> : <EmptyState title="Sin archivos adjuntos" description="Los archivos adjuntos a este hilo aparecerán aquí." />}</Card>
            <Card title="Artefactos del hilo">
              {artifacts.length === 0 ? <EmptyState title="Sin artefactos" description="Los archivos que el asistente genere aparecerán aquí." /> : <ul>{artifacts.map((artifact) => <li key={artifact.id}>{artifact.filename}<Button variant="tertiary" aria-label={`Descargar ${artifact.filename}`} disabled={busyArtifactId === artifact.id} onClick={() => void downloadArtifact(artifact)}><Icon icon={Download} size="sm" /></Button></li>)}</ul>}
              {artifactError ? <StateMessage tone="danger" role="alert" title={artifactError} /> : null}
            </Card>
            <Card title="Fuentes del hilo"><EmptyState title="Fuentes no disponibles" description="El hilo no entrega fuentes asociadas a sus respuestas." /></Card>
          </div> : <div className="assistant-workspace__context-content">
            <Card title="Agentes del proyecto"><EmptyState title="Aún no hay agentes disponibles" description="La gestión de agentes por proyecto todavía no está disponible." /></Card>
            <Card title="Actividad del agente">
              {processing ? <StateMessage tone="info" role="status" spinner title={lifecycle || "Ejecución en curso"} /> : null}
              {plan?.tool ? <p><strong>Plan:</strong> {plan.summary || plan.tool}</p> : null}
              {evidence.length ? evidence.map((item, index) => <div className="assistant-workspace__evidence" key={`${item.tool ?? "asistente"}-${index}`}><strong>{item.tool || "Asistente"}</strong><Badge tone={item.status === "error" ? "danger" : item.status === "completed" ? "success" : "neutral"}>{item.status}</Badge>{item.detail ? <p>{item.detail}</p> : null}</div>) : !processing ? <EmptyState title="Sin actividad registrada" description="La actividad de herramientas aparecerá aquí cuando exista." /> : null}
            </Card>
          </div>}
        </Tabs>
      </aside>
    </div>
  );
}
