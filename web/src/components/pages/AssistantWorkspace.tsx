import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, Download, FileText, Folder, History, PanelRight, PanelLeft, Plus, X, MessageSquarePlus } from "lucide-react";
import { ApiError, createProject, deleteChatThread, downloadAssistantArtifact, listActiveRuns, listChatThreads, listProjects, renameChatThread } from "../../api";
import type { ActiveRun, AssistantArtifact, AssistantAttachment, AssistantCapabilities, AssistantEvidence, AssistantPlan, InternalChatThreadSummary, Project, Role } from "../../types";
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

export function AssistantWorkspace({ children, onCreateThread, onCreateDefaultThread, role, loadThreadTabs = true, attachments = [], artifacts = [], capabilities, capabilitiesLoading = false, capabilitiesError = false, evidence = [], plan, lifecycle, processing = false }: { children: ReactNode; onCreateThread: () => void; onCreateDefaultThread?: () => void; role?: Role; loadThreadTabs?: boolean; attachments?: AssistantAttachment[]; artifacts?: AssistantArtifact[]; capabilities?: AssistantCapabilities | null; capabilitiesLoading?: boolean; capabilitiesError?: boolean; evidence?: AssistantEvidence[]; plan?: AssistantPlan | null; lifecycle?: string | null; processing?: boolean }) {
  const [projectsVisible, setProjectsVisible] = useState(() => window.innerWidth > 1024);
  const [contextVisible, setContextVisible] = useState(() => window.innerWidth > 1024);
  const [search, setSearch] = useState("");
  const [selectedProject, setSelectedProject] = useState<string | null>(() => new URLSearchParams(window.location.search).get("proyecto"));
  const [projectThreads, setProjectThreads] = useState<Record<string, { state: "loading" | "ready" | "empty" | "error" | "denied"; threads: InternalChatThreadSummary[] }>>({});
  const [historySearch, setHistorySearch] = useState<Record<string, string>>({});
  const [defaultHistoryOpen, setDefaultHistoryOpen] = useState(false);
  const [defaultThreads, setDefaultThreads] = useState<{ state: "idle" | "loading" | "ready" | "empty" | "error" | "denied"; threads: InternalChatThreadSummary[] }>({ state: "idle", threads: [] });
  const [activeRuns, setActiveRuns] = useState<{ state: "loading" | "ready" | "empty" | "error"; runs: ActiveRun[] }>({ state: "loading", runs: [] });
  const [threads, setThreads] = useState<InternalChatThreadSummary[]>([]);
  const [openThreadIds, setOpenThreadIds] = useState<number[]>(() => {
    const threadId = Number(new URLSearchParams(window.location.search).get("thread_id"));
    return threadId ? [threadId] : [];
  });
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

  useEffect(() => {
    let current = true;
    const refresh = async () => {
      try {
        const result = await listActiveRuns();
        if (current) setActiveRuns({ state: result.active_runs.length ? "ready" : "empty", runs: result.active_runs });
      } catch {
        if (current) setActiveRuns({ state: "error", runs: [] });
      }
    };
    void refresh();
    const interval = window.setInterval(() => void refresh(), 5000);
    return () => { current = false; window.clearInterval(interval); };
  }, []);

  const stageLabel = (stage: string) => ({ planning: "Planificando", executing: "Ejecutando", verifying: "Verificando", streaming: "Respondiendo" }[stage] ?? "En curso");

  const loadProjectThreads = async (slug: string) => {
    setProjectThreads((current) => ({ ...current, [slug]: { state: "loading", threads: [] } }));
    try {
      const result = await listChatThreads(20, slug);
      setProjectThreads((current) => ({ ...current, [slug]: { state: result.threads.length ? "ready" : "empty", threads: result.threads } }));
    } catch (error: unknown) {
      setProjectThreads((current) => ({ ...current, [slug]: { state: error instanceof ApiError && error.status === 403 ? "denied" : "error", threads: [] } }));
    }
  };

  const loadDefaultThreads = async () => {
    setDefaultThreads({ state: "loading", threads: [] });
    try {
      const result = await listChatThreads(20, "default");
      setDefaultThreads({ state: result.threads.length ? "ready" : "empty", threads: result.threads });
    } catch (error: unknown) {
      setDefaultThreads({ state: error instanceof ApiError && error.status === 403 ? "denied" : "error", threads: [] });
    }
  };

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
    if (loadThreadTabs && activeThreadId) {
      setOpenThreadIds((current) => current.includes(activeThreadId) ? current : [...current, activeThreadId]);
    }
  }, [activeThreadId, loadThreadTabs]);

  useEffect(() => {
    if (!loadThreadTabs) return;
    const onPopState = () => {
      setLocationKey(`${window.location.pathname}${window.location.search}`);
      const threadId = Number(new URLSearchParams(window.location.search).get("thread_id"));
      if (threadId) setOpenThreadIds((current) => current.includes(threadId) ? current : [...current, threadId]);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [loadThreadTabs]);

  const navigateToThread = (threadId: number, projectSlug = activeProjectSlug) => {
    setOpenThreadIds((current) => current.includes(threadId) ? current : [...current, threadId]);
    window.history.pushState({}, "", pathForRoute({
      view: "chat",
      ...(projectSlug ? { projectSlug } : {}),
      threadId,
    }));
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const closeThreadTab = (threadId: number) => {
    const remaining = openThreadIds.filter((id) => id !== threadId);
    setOpenThreadIds(remaining);
    if (threadId !== activeThreadId) return;
    if (remaining.length) navigateToThread(remaining[remaining.length - 1]);
    else {
      window.history.pushState({}, "", pathForRoute({ view: "chat" }));
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
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
      setOpenThreadIds((ids) => ids.filter((id) => id !== deleteTarget.id));
      setDeleteTarget(null);
      if (deleteTarget.id === activeThreadId) {
        const nextId = openThreadIds.filter((id) => id !== deleteTarget.id).at(-1);
        if (nextId) navigateToThread(nextId);
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
      className={`assistant-workspace${projectsVisible ? " assistant-workspace--projects-visible" : " assistant-workspace--projects-collapsed"}${contextVisible ? " assistant-workspace--context-visible" : " assistant-workspace--context-collapsed"}`}
      data-testid="assistant-workspace"
    >
      {projectsVisible || contextVisible ? <button type="button" className="assistant-workspace__scrim" aria-label="Cerrar paneles" onClick={() => { setProjectsVisible(false); setContextVisible(false); }} /> : null}
      <aside
        id="assistant-workspace-projects"
        className="assistant-workspace__projects"
        aria-label="Proyectos"
        data-collapsed={!projectsVisible}
      >
        <section className="assistant-workspace__sidebar-header" aria-label="Asistente Lumat">
          <header className="assistant-workspace__pane-header">
            {projectsVisible ? <><h2>Asistente Lumat</h2><button type="button" className="assistant-workspace__pane-toggle" aria-label="Contraer panel de proyectos" aria-expanded="true" aria-controls="assistant-workspace-projects" onClick={() => setProjectsVisible(false)}><Icon icon={PanelLeft} /></button></> : <button type="button" className="assistant-workspace__pane-toggle" aria-label="Expandir panel de proyectos" aria-expanded="false" aria-controls="assistant-workspace-projects" onClick={() => setProjectsVisible(true)}><Icon icon={PanelLeft} /></button>}
          </header>
          {(role === "admin" || role === "operador") ? <div className="assistant-workspace__default-actions">
            <Button variant="tertiary" aria-label="Nueva conversación" title="Nueva conversación" onClick={onCreateDefaultThread}><Icon icon={MessageSquarePlus} /><span>Nueva conversación</span></Button>
            <Button variant="tertiary" aria-label="Historial" title="Historial" aria-expanded={defaultHistoryOpen} onClick={() => { const open = !defaultHistoryOpen; setDefaultHistoryOpen(open); if (open) void loadDefaultThreads(); }}><Icon icon={History} /><span>Historial</span></Button>
          </div> : null}
        </section>
        <section className="assistant-workspace__project-section" aria-label="Proyectos" hidden={!projectsVisible}>
          <header className="assistant-workspace__section-header"><h2>Proyectos</h2><Button variant="tertiary" aria-label="Nuevo proyecto" title="Nuevo proyecto" onClick={() => { setProjectCreateError(null); setCreateProjectOpen(true); }}><Icon icon={Plus} /><span>Nuevo proyecto</span></Button></header>
        {projectsVisible && defaultHistoryOpen ? <div className="assistant-workspace__default-history" aria-label="Hilos predeterminados">
          {defaultThreads.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando hilos" /> : null}
          {defaultThreads.state === "error" || defaultThreads.state === "denied" ? <StateMessage tone="danger" role="alert" title={defaultThreads.state === "denied" ? "No tienes permiso para ver estos hilos." : "No pudimos cargar los hilos."} /> : null}
          {defaultThreads.state === "empty" ? <EmptyState title="No hay hilos" description="Todavía no hay hilos en el espacio predeterminado." /> : null}
          {defaultThreads.state === "ready" ? <ul>{defaultThreads.threads.map((thread) => <li key={thread.id}><button type="button" onClick={() => navigateToThread(thread.id, "default")}>{thread.title || "Sin título"}</button></li>)}</ul> : null}
          {defaultThreads.state === "error" ? <Button variant="secondary" onClick={() => void loadDefaultThreads()}>Reintentar</Button> : null}
        </div> : null}
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
                          <button type="button" className="assistant-workspace__history-trigger" aria-expanded={projectThreads[project.slug] !== undefined} onClick={() => { if (projectThreads[project.slug]) setProjectThreads((current) => { const next = { ...current }; delete next[project.slug]; return next; }); else void loadProjectThreads(project.slug); }}><Icon icon={History} size="sm" />Historial de hilos</button>
                          {projectThreads[project.slug] ? <div className="assistant-workspace__project-history">
                            <SearchInput aria-label={`Buscar hilos de ${project.name}`} placeholder="Buscar hilo" onSearch={(value) => setHistorySearch((current) => ({ ...current, [project.slug]: value }))} />
                            {projectThreads[project.slug].state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando hilos" /> : null}
                            {projectThreads[project.slug].state === "error" || projectThreads[project.slug].state === "denied" ? <StateMessage tone="danger" role="alert" title={projectThreads[project.slug].state === "denied" ? "No tienes permiso para ver estos hilos." : "No pudimos cargar los hilos."} /> : null}
                            {projectThreads[project.slug].state === "empty" ? <EmptyState title="No hay hilos" description="Este proyecto aún no tiene hilos." /> : null}
                            {projectThreads[project.slug].state === "ready" ? (() => { const filtered = projectThreads[project.slug].threads.filter((thread) => (thread.title || "Sin título").toLocaleLowerCase().includes((historySearch[project.slug] || "").trim().toLocaleLowerCase())); return filtered.length ? <ul>{filtered.map((thread) => <li key={thread.id}><button type="button" onClick={() => navigateToThread(thread.id, project.slug)}>{thread.title || "Sin título"}</button></li>)}</ul> : <EmptyState title="No encontramos hilos" description="Prueba con otro nombre." />; })() : null}
                            {projectThreads[project.slug].state === "error" ? <Button variant="secondary" onClick={() => void loadProjectThreads(project.slug)}>Reintentar</Button> : null}
                          </div> : null}
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
        </section>
        <section className="assistant-workspace__agents" aria-label="Agentes" hidden={!projectsVisible}>
          <header><h3>Agentes</h3></header>
          {openThreadIds.length === 0 ? <EmptyState title="No hay agentes activos" /> : <ul>{openThreadIds.map((id) => {
            const thread = [...threads, ...defaultThreads.threads, ...Object.values(projectThreads).flatMap((entry) => entry.threads)].find((item) => item.id === id);
            const run = activeRuns.runs.find((item) => item.thread_id === id);
            const slug = thread?.proyecto ?? run?.proyecto;
            const projectName = slug === "default" ? "Conversación rápida" : slug ? projects.find((project) => project.slug === slug)?.name ?? slug : "—";
            return <li key={id}><strong>Orquestador</strong><p>{projectName}</p><span>{run ? stageLabel(run.stage) : "Activo"}</span></li>;
          })}</ul>}
        </section>
      </aside>

      <section className="assistant-workspace__thread" aria-label="Área del hilo">
        <nav className="assistant-workspace__thread-tabs" aria-label="Hilos abiertos">
          <div className="assistant-workspace__thread-tab-list">
            {openThreadIds.map((id) => {
              const thread = [...threads, ...defaultThreads.threads, ...Object.values(projectThreads).flatMap((entry) => entry.threads)].find((item) => item.id === id);
              return <div className="assistant-workspace__thread-tab" key={id} data-active={id === activeThreadId}>
                <button type="button" aria-current={id === activeThreadId ? "page" : undefined} onClick={() => navigateToThread(id, thread?.proyecto)}>
                  {thread?.title || "Sin título"}
                </button>
                <button type="button" className="assistant-workspace__thread-close" aria-label={`Cerrar ${thread?.title || "hilo"}`} onClick={() => closeThreadTab(id)}>
                  <Icon icon={X} size="sm" />
                </button>
              </div>;
            })}
          </div>
          {activeThread ? <Menu
            label="Acciones del hilo"
            trigger="icon"
            items={[{ value: "rename", label: "Renombrar" }, { value: "delete", label: "Eliminar", tone: "danger" }]}
            onSelect={(value) => {
              setThreadActionError(null);
              if (value === "rename") { setRenameTarget(activeThread); setRenameTitle(activeThread.title ?? ""); }
              else setDeleteTarget(activeThread);
            }}
          /> : null}
          <Button variant="tertiary" aria-label="Crear nuevo hilo" title="Crear nuevo hilo" onClick={onCreateThread}>
            <Icon icon={Plus} />
          </Button>
        </nav>
        {threadListError ? <StateMessage tone="danger" role="alert" title={threadListError} /> : null}
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
        data-collapsed={!contextVisible}
      >
        <header className="assistant-workspace__pane-header"><h2>Actividad del hilo</h2><button type="button" className="assistant-workspace__pane-toggle" aria-label={contextVisible ? "Cerrar panel de actividad" : "Abrir panel de actividad"} aria-expanded={contextVisible} aria-controls="assistant-workspace-context" onClick={() => setContextVisible((visible) => !visible)}><Icon icon={contextVisible ? X : PanelRight} /></button></header>
        {contextVisible ? <>
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
        </> : null}
      </aside>
    </div>
  );
}
