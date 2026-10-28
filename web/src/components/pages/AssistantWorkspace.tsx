import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { BrainCircuit, ChevronDown, ChevronRight, Download, FileText, Folder, History, Info, Link, Menu as MenuIcon, MessageSquarePlus, MessageSquareText, Paperclip, PanelLeft, PanelRight, Pencil, Plus, Share2, SlidersHorizontal, Trash2, Users, X } from "lucide-react";
import { ApiError, createProject, deleteChatThread, downloadAssistantArtifact, getAssistantCapabilities, listActiveRuns, listChatThreads, listProjects, renameChatThread, threadAttachmentContentUrl } from "../../api";
import type { ActiveRun, AssistantArtifact, AssistantAttachment, AssistantCapabilities, InternalChatThreadSummary, Project, Role } from "../../types";
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
import { PageFrame } from "../shared/PageFrame";
import { Input } from "../primitives/Input";
import { Textarea } from "../primitives/Textarea";
import { Avatar } from "../primitives/Avatar";
import { projectStatusLabel, projectStatusTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";
import { mergeWorkspaceTabs, readWorkspaceTabState, workspaceTabIdentity, writeWorkspaceTabs } from "../domain/assistantTabs";
import type { WorkspaceTab } from "../domain/assistantTabs";
import { assistantFileIcon } from "./assistantFileIcon";
import { ProjectsPage } from "./ProjectsPage";
import { ThreadProjectResources } from "./ThreadResources";
import { groupThreadsByDate } from "./threadDateGroups";
import "./AssistantWorkspace.css";

export type { WorkspaceTab } from "../domain/assistantTabs";

function routeWorkspaceTabs(): WorkspaceTab[] {
  const params = new URLSearchParams(window.location.search);
  const threadId = Number(params.get("thread_id"));
  if (Number.isInteger(threadId) && threadId > 0) return [{ kind: "thread", threadId }];
  if (params.get("context")) return [{ kind: "context", projectSlug: params.get("context")! }];
  if (params.get("history")) return [{ kind: "history", projectSlug: params.get("history")! }];
  return [];
}

function useDesktopWorkspace() {
  const [desktop, setDesktop] = useState(() => window.matchMedia?.("(min-width: 64rem)").matches ?? window.innerWidth > 1024);

  useEffect(() => {
    const query = window.matchMedia?.("(min-width: 64rem)");
    const update = () => setDesktop(query?.matches ?? window.innerWidth > 1024);
    update();
    if (query) {
      query.addEventListener("change", update);
      return () => query.removeEventListener("change", update);
    }
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return desktop;
}

export function AssistantWorkspace({ children, onCreateThread, onCreateDefaultThread, role, userId, loadThreadTabs = true, attachments = [], artifacts = [], capabilities, capabilitiesLoading = false, capabilitiesError = false, activeProjectSlug, onChangeProject, onSelectProject }: { children: ReactNode; onCreateThread: () => void; onCreateDefaultThread?: () => void; role?: Role; userId?: number; loadThreadTabs?: boolean; attachments?: AssistantAttachment[]; artifacts?: AssistantArtifact[]; capabilities?: AssistantCapabilities | null; capabilitiesLoading?: boolean; capabilitiesError?: boolean; activeProjectSlug?: string; onChangeProject?: () => void; onSelectProject?: (slug: string) => void }) {
  const desktopWorkspace = useDesktopWorkspace();
  const [projectsVisible, setProjectsVisible] = useState(desktopWorkspace);
  const [contextVisible, setContextVisible] = useState(desktopWorkspace);
  useEffect(() => {
    setProjectsVisible(desktopWorkspace);
    setContextVisible(desktopWorkspace);
  }, [desktopWorkspace]);
  const [search, setSearch] = useState("");
  const [expandedProjectSlug, setExpandedProjectSlug] = useState<string | null>(() => new URLSearchParams(window.location.search).get("proyecto"));
  const [projectThreads, setProjectThreads] = useState<Record<string, { state: "loading" | "ready" | "empty" | "error" | "denied"; threads: InternalChatThreadSummary[] }>>({});
  const [historySearch, setHistorySearch] = useState<Record<string, string>>({});
  const [defaultHistoryOpen, setDefaultHistoryOpen] = useState(false);
  const [agentsExpanded, setAgentsExpanded] = useState(true);
  const [defaultThreads, setDefaultThreads] = useState<{ state: "idle" | "loading" | "ready" | "empty" | "error" | "denied"; threads: InternalChatThreadSummary[] }>({ state: "idle", threads: [] });
  const [activeRuns, setActiveRuns] = useState<{ state: "loading" | "ready" | "empty" | "error"; runs: ActiveRun[] }>({ state: "loading", runs: [] });
  const [threads, setThreads] = useState<InternalChatThreadSummary[]>([]);
  const [threadTitles, setThreadTitles] = useState<Record<number, string>>({});
  const [restoredWorkspace] = useState(() => {
    const persisted = userId === undefined ? { tabs: [], activeTab: null } : readWorkspaceTabState(userId);
    const routeTabs = routeWorkspaceTabs();
    return {
      tabs: mergeWorkspaceTabs(persisted.tabs, routeTabs),
      activeTab: routeTabs[0] ?? persisted.activeTab,
    };
  });
  const [openTabs, setOpenTabs] = useState<WorkspaceTab[]>(restoredWorkspace.tabs);
  const [activeTab, setActiveTab] = useState<WorkspaceTab | null>(restoredWorkspace.activeTab);
  useEffect(() => {
    if (userId !== undefined) writeWorkspaceTabs(userId, openTabs, activeTab);
  }, [activeTab, openTabs, userId]);
  const [threadListError, setThreadListError] = useState<string | null>(null);
  const [, setLocationKey] = useState(() => `${window.location.pathname}${window.location.search}`);
  const [renameTarget, setRenameTarget] = useState<{ id: number; title: string | null } | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; title: string | null } | null>(null);
  const [threadActionError, setThreadActionError] = useState<string | null>(null);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [projectSheetOpen, setProjectSheetOpen] = useState(false);
  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [threadDetailOpen, setThreadDetailOpen] = useState(false);
  // The capabilities section lives in the context panel; fetch it only when that
  // panel is actually visible, and only when no parent controls it via props.
  const contextPanelVisible = contextVisible || threadDetailOpen;
  const controlledCapabilities = capabilities !== undefined;
  const fetchCapabilities = useCallback(async () => {
    const result = await getAssistantCapabilities();
    if (!Array.isArray(result.tools) || !Array.isArray(result.personas) || !Array.isArray(result.prompts)) {
      throw new Error("Invalid assistant capabilities response");
    }
    return result;
  }, []);
  const fetchedCapabilities = useAsyncData(fetchCapabilities, !controlledCapabilities && contextPanelVisible);
  const effectiveCapabilities = controlledCapabilities ? capabilities : fetchedCapabilities.data;
  const effectiveCapabilitiesLoading = controlledCapabilities ? capabilitiesLoading : fetchedCapabilities.state === "loading";
  const effectiveCapabilitiesError = controlledCapabilities ? capabilitiesError : fetchedCapabilities.state === "error" || fetchedCapabilities.state === "denied";
  const [projectName, setProjectName] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [projectPurpose, setProjectPurpose] = useState("");
  const [projectSlugEdited, setProjectSlugEdited] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState<string | null>(null);
  const [projectSubmitting, setProjectSubmitting] = useState(false);
  const [busyArtifactId, setBusyArtifactId] = useState<number | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const [contextSections, setContextSections] = useState<Record<string, boolean>>({ project: true });
  const route = new URLSearchParams(window.location.search);
  const activeThreadId = Number(route.get("thread_id")) || undefined;
  const activeContextSlug = !activeThreadId ? route.get("context") || undefined : undefined;
  const activeHistorySlug = !activeThreadId && !activeContextSlug ? route.get("history") || undefined : undefined;
  const routeProjectSlug = route.get("proyecto") || undefined;
  const panelProjectSlug = activeContextSlug ?? activeProjectSlug ?? routeProjectSlug;
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
  const projectsData = useAsyncData(loadProjects, projectsVisible || navigationOpen || projectSheetOpen || projectPickerOpen || Boolean(panelProjectSlug) || Boolean(activeContextSlug));
  const projects = projectsData.data?.projects ?? [];
  const activeProject = projects.find((project) => project.slug === panelProjectSlug);
  const selectedProject = projects.find((project) => project.slug === (expandedProjectSlug ?? routeProjectSlug ?? activeProjectSlug)) ?? projects[0];
  // The mobile header must show the THREAD's project — the same source the picker
  // checks. `projects` does not contain the implicit `default` project, so
  // falling back to `selectedProject` (which ends in `?? projects[0]`) made the
  // header keep showing an arbitrary project whenever "General" was selected.
  const headerProjectName = activeProjectSlug === "default" ? "General" : (activeProject?.name ?? selectedProject?.name ?? "General");
  const activeThread = [...threads, ...defaultThreads.threads, ...Object.values(projectThreads).flatMap((entry) => entry.threads)].find((thread) => thread.id === activeThreadId);
  const toggleContextSection = (id: string) => setContextSections((current) => ({ ...current, [id]: !(current[id] ?? false) }));
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

  const loadProjectThreads = async (slug: string, limit = 20) => {
    setProjectThreads((current) => ({ ...current, [slug]: { state: "loading", threads: [] } }));
    try {
      const result = await listChatThreads(limit, slug);
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
      setOpenTabs((current) => current.some((tab) => tab.kind === "thread" && tab.threadId === activeThreadId) ? current : [...current, { kind: "thread", threadId: activeThreadId }]);
    }
  }, [activeThreadId, loadThreadTabs]);

  useEffect(() => {
    const onPopState = () => {
      setLocationKey(`${window.location.pathname}${window.location.search}`);
      const routeTab = routeWorkspaceTabs()[0];
      if (routeTab) {
        setActiveTab(routeTab);
        setOpenTabs((current) => mergeWorkspaceTabs(current, [routeTab]));
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [loadThreadTabs]);

  useEffect(() => {
    if (activeHistorySlug) void loadProjectThreads(activeHistorySlug, 50);
  }, [activeHistorySlug]);

  const navigateToThread = (threadId: number, projectSlug = routeProjectSlug) => {
    setOpenTabs((current) => current.some((tab) => tab.kind === "thread" && tab.threadId === threadId) ? current : [...current, { kind: "thread", threadId }]);
    window.history.pushState({}, "", pathForRoute({
      view: "chat",
      ...(projectSlug ? { projectSlug } : {}),
      threadId,
    }));
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const navigateToTab = (tab: WorkspaceTab, replace = false) => {
    const thread = tab.kind === "thread" ? [...threads, ...defaultThreads.threads, ...Object.values(projectThreads).flatMap((entry) => entry.threads)].find((item) => item.id === tab.threadId) : undefined;
    const target = tab.kind === "thread"
      ? pathForRoute({ view: "chat", ...((thread?.proyecto ?? routeProjectSlug) ? { projectSlug: thread?.proyecto ?? routeProjectSlug } : {}), threadId: tab.threadId })
      : tab.kind === "context"
        ? pathForRoute({ view: "chat", contextProjectSlug: tab.projectSlug })
        : pathForRoute({ view: "chat", historyProjectSlug: tab.projectSlug });
    window.history[replace ? "replaceState" : "pushState"]({}, "", target);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  useEffect(() => {
    if (!routeWorkspaceTabs().length && activeTab && openTabs.some((tab) => workspaceTabIdentity(tab) === workspaceTabIdentity(activeTab))) {
      navigateToTab(activeTab, true);
    }
  }, [activeTab, openTabs]);

  const closeTab = (tab: WorkspaceTab) => {
    const sameTab = (candidate: WorkspaceTab) => {
      if (candidate.kind !== tab.kind) return false;
      if (candidate.kind === "thread" && tab.kind === "thread") return candidate.threadId === tab.threadId;
      return (candidate.kind === "context" || candidate.kind === "history") && (tab.kind === "context" || tab.kind === "history") && candidate.projectSlug === tab.projectSlug;
    };
    const remaining = openTabs.filter((candidate) => !sameTab(candidate));
    setOpenTabs(remaining);
    const active = tab.kind === "thread" ? tab.threadId === activeThreadId : tab.kind === "context" ? tab.projectSlug === activeContextSlug : tab.projectSlug === activeHistorySlug;
    if (!active) return;
    if (remaining.length) navigateToTab(remaining[remaining.length - 1]);
    else {
      setActiveTab(null);
      window.history.pushState({}, "", pathForRoute({ view: "chat" }));
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  };

  const navigateToHistory = (slug: string) => {
    setOpenTabs((current) => current.some((tab) => tab.kind === "history" && tab.projectSlug === slug) ? current : [...current, { kind: "history", projectSlug: slug }]);
    window.history.pushState({}, "", pathForRoute({ view: "chat", historyProjectSlug: slug }));
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const renameThread = async () => {
    if (!renameTarget || !renameTitle.trim()) return;
    try {
      const { thread } = await renameChatThread(renameTarget.id, renameTitle.trim());
      setThreadTitles((current) => ({ ...current, [thread.id]: thread.title ?? "" }));
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
      setOpenTabs((tabs) => tabs.filter((tab) => tab.kind !== "thread" || tab.threadId !== deleteTarget.id));
      setDeleteTarget(null);
      if (deleteTarget.id === activeThreadId) {
        const nextTab = openTabs.filter((tab) => tab.kind !== "thread" || tab.threadId !== deleteTarget.id).at(-1);
        if (nextTab) navigateToTab(nextTab);
        else {
          setActiveTab(null);
          window.history.pushState({}, "", pathForRoute({ view: "chat" }));
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
      }
    } catch {
      setThreadActionError("No pudimos eliminar el hilo.");
    }
  };

  const navigateToProject = (project: Project, destination: "context" | "threads") => {
    if (destination === "context") {
      setOpenTabs((tabs) => tabs.some((tab) => tab.kind === "context" && tab.projectSlug === project.slug) ? tabs : [...tabs, { kind: "context", projectSlug: project.slug }]);
      window.history.pushState({}, "", pathForRoute({ view: "chat", contextProjectSlug: project.slug }));
      window.dispatchEvent(new PopStateEvent("popstate"));
      return;
    }
    const route = { view: "chat" as const, projectSlug: project.slug };
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
      setExpandedProjectSlug(project.slug);
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
      <Dialog open={threadDetailOpen} onClose={() => setThreadDetailOpen(false)} title="Detalle del hilo" variant="sheet">
        {threadDetailOpen ? <div className="assistant-workspace__thread-detail-sheet">
          <div className="assistant-workspace__thread-project-row">
            <span>{activeProject?.name ?? (activeProjectSlug === "default" ? "General" : activeProjectSlug ?? "Sin proyecto")}</span>
            <Button variant="tertiary" onClick={() => { setThreadDetailOpen(false); onChangeProject?.(); }}>Cambiar</Button>
          </div>
          <ThreadContextSections activeProject={activeProject} threadId={activeThreadId} capabilities={effectiveCapabilities} capabilitiesLoading={effectiveCapabilitiesLoading} capabilitiesError={effectiveCapabilitiesError} attachments={attachments} artifacts={artifacts} contextSections={contextSections} toggleContextSection={toggleContextSection} busyArtifactId={busyArtifactId} artifactError={artifactError} downloadArtifact={downloadArtifact} mobile />
        </div> : null}
      </Dialog>
      <Dialog open={navigationOpen} onClose={() => setNavigationOpen(false)} title="Navegación" variant="sheet">
        <div className="assistant-workspace__navigation-sheet">
          {(role === "admin" || role === "operador") ? <Button variant="primary" onClick={() => { setNavigationOpen(false); onCreateDefaultThread?.(); }}>Nueva conversación</Button> : null}
          <button type="button" className="assistant-workspace__history-trigger" onClick={() => { setNavigationOpen(false); navigateToHistory(routeProjectSlug ?? "default"); }}>Historial de conversaciones <Icon icon={ChevronRight} size="sm" /></button>
          <section aria-labelledby="assistant-navigation-workspace-title">
            <h3 id="assistant-navigation-workspace-title">Espacio de trabajo</h3>
            <button type="button" className="assistant-workspace__history-trigger" onClick={() => { setNavigationOpen(false); setProjectSheetOpen(true); }}>Proyectos ({projects.length}) <Icon icon={ChevronRight} size="sm" /></button>
          </section>
        </div>
      </Dialog>
      <Dialog open={projectSheetOpen} onClose={() => setProjectSheetOpen(false)} title="Proyecto" variant="sheet">
        {projectSheetOpen ? <div className="assistant-workspace__project-sheet">
          <SearchInput aria-label="Buscar proyecto" placeholder="Buscar proyecto" onSearch={setSearch} />
          <div className="assistant-workspace__project-sheet-list" aria-label="Lista de proyectos">
            {projectsData.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyectos" /> : null}
            {projectsData.state === "error" || projectsData.state === "denied" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los proyectos" /> : null}
            {projectsData.state === "ready" && visibleProjects.length === 0 ? <EmptyState title={projects.length ? "No encontramos proyectos" : "No hay proyectos"} description={projects.length ? "Prueba con otro nombre." : "No hay espacios de proyecto registrados para mostrar."} /> : null}
            {projectsData.state === "ready" ? visibleProjects.map((project) => {
              const selected = selectedProject?.slug === project.slug;
              return <button type="button" key={project.slug} className={`assistant-workspace__project-sheet-option${selected ? " is-selected" : ""}`} aria-pressed={selected} onClick={() => { setExpandedProjectSlug(project.slug); }}>
                <span>{project.name}</span>{selected ? <span aria-label="Seleccionado">✓</span> : null}
              </button>;
            }) : null}
          </div>
          {selectedProject ? <section className="assistant-workspace__project-sheet-details" aria-label={`Opciones de ${selectedProject.name}`}>
            <h3>{selectedProject.name}</h3>
            <button type="button" className="assistant-workspace__history-trigger" onClick={() => { setProjectSheetOpen(false); navigateToProject(selectedProject, "context"); }}>Contexto y archivos <Icon icon={ChevronRight} size="sm" /></button>
            <button type="button" className="assistant-workspace__history-trigger" onClick={() => { setProjectSheetOpen(false); navigateToHistory(selectedProject.slug); }}>Historial de hilos <Icon icon={ChevronRight} size="sm" /></button>
          </section> : null}
          <Button variant="secondary" onClick={() => { setProjectCreateError(null); setCreateProjectOpen(true); }}><Icon icon={Plus} size="sm" />Crear proyecto</Button>
        </div> : null}
      </Dialog>
      <Dialog open={projectPickerOpen} onClose={() => setProjectPickerOpen(false)} title="Elegir proyecto" variant="sheet">
        <div className="assistant-workspace__project-picker">
          <button type="button" aria-pressed={activeProjectSlug === "default"} onClick={() => { setProjectPickerOpen(false); onSelectProject?.("default"); }}>General{activeProjectSlug === "default" ? <span aria-label="Seleccionado">✓</span> : null}</button>
          {projects.filter((project) => project.slug !== "default").map((project) => <button type="button" key={project.slug} aria-pressed={activeProjectSlug === project.slug} onClick={() => { setProjectPickerOpen(false); onSelectProject?.(project.slug); }}>{project.name}{activeProjectSlug === project.slug ? <span aria-label="Seleccionado">✓</span> : null}</button>)}
          <Button variant="secondary" onClick={() => { setProjectPickerOpen(false); setProjectCreateError(null); setCreateProjectOpen(true); }}><Icon icon={Plus} size="sm" />Crear proyecto</Button>
        </div>
      </Dialog>
      {projectsVisible || contextVisible ? <button type="button" className="assistant-workspace__scrim" aria-label="Cerrar paneles" onClick={() => { setProjectsVisible(false); setContextVisible(false); }} /> : null}
      <header className="assistant-workspace__mobile-header" aria-label="Controles del asistente">
        <button type="button" aria-label="Abrir navegación del asistente" aria-haspopup="dialog" onClick={() => setNavigationOpen(true)}><MenuIcon aria-hidden="true" /></button>
        <button type="button" className="assistant-workspace__mobile-project" aria-label={`Elegir proyecto: ${headerProjectName}`} onClick={() => setProjectPickerOpen(true)}>
          <Icon icon={Folder} size="sm" />
          <span>{headerProjectName}</span>
          <Icon icon={ChevronDown} size="sm" />
        </button>
        <button type="button" aria-label="Detalle del hilo" aria-haspopup="dialog" onClick={() => setThreadDetailOpen(true)}><Info aria-hidden="true" /></button>
      </header>
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
          {!projectsVisible ? <div className="assistant-workspace__rail-separator" aria-hidden="true" /> : null}
          {(role === "admin" || role === "operador") ? <div className="assistant-workspace__default-actions">
            <Button variant="primary" aria-label="Nueva conversación" title="Nueva conversación" onClick={onCreateDefaultThread}><Icon icon={MessageSquarePlus} /><span>Nueva conversación</span></Button>
            <Button variant="secondary" aria-label="Historial de conversaciones" title="Historial de conversaciones" aria-expanded={defaultHistoryOpen} onClick={() => { const open = !defaultHistoryOpen; setDefaultHistoryOpen(open); if (open) void loadDefaultThreads(); }}><Icon icon={History} /><span>Historial de conversaciones</span></Button>
            {projectsVisible && defaultHistoryOpen ? <div className="assistant-workspace__default-history" aria-label="Hilos predeterminados">
              {defaultThreads.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando hilos" /> : null}
              {defaultThreads.state === "error" || defaultThreads.state === "denied" ? <StateMessage tone="danger" role="alert" title={defaultThreads.state === "denied" ? "No tienes permiso para ver estos hilos." : "No pudimos cargar los hilos."} /> : null}
              {defaultThreads.state === "empty" ? <EmptyState title="No hay hilos" description="Todavía no hay hilos en el espacio predeterminado." /> : null}
              {defaultThreads.state === "ready" ? <ul>{defaultThreads.threads.map((thread) => <li key={thread.id}><button type="button" onClick={() => navigateToThread(thread.id, "default")}>{thread.title || "Sin título"}</button></li>)}</ul> : null}
              {defaultThreads.state === "error" ? <Button variant="secondary" onClick={() => void loadDefaultThreads()}>Reintentar</Button> : null}
            </div> : null}
          </div> : null}
          {!projectsVisible ? <>
            <div className="assistant-workspace__rail-separator" aria-hidden="true" />
            <nav className="assistant-workspace__rail-actions" aria-label="Navegación del panel de proyectos">
              <button type="button" aria-label="Proyectos" title="Proyectos" onClick={() => setProjectsVisible(true)}><Icon icon={Folder} /></button>
              <button type="button" aria-label="Agentes" title="Agentes" onClick={() => { setAgentsExpanded(true); setProjectsVisible(true); }}><Icon icon={Users} /></button>
            </nav>
            <div className="assistant-workspace__rail-separator" aria-hidden="true" />
          </> : null}
          </section>
        <section className="assistant-workspace__project-section" aria-label="Proyectos" hidden={!projectsVisible}>
          <header className="assistant-workspace__section-header"><h2>Proyectos</h2><Menu label="Acciones de proyectos" trigger="icon" items={[{ value: "create", label: "Nuevo proyecto", icon: Plus }, { value: "manage", label: "Administrar proyectos", icon: SlidersHorizontal }]} onSelect={(value) => { if (value === "create") { setProjectCreateError(null); setCreateProjectOpen(true); } else { window.history.pushState({}, "", pathForRoute({ view: "projects" })); window.dispatchEvent(new PopStateEvent("popstate")); } }} /></header>
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
              const expanded = expandedProjectSlug === project.slug;
              return (
                  <div className="assistant-workspace__project-card" key={project.slug}>
                  <div className={`assistant-workspace__project-row${expanded ? " is-selected" : ""}`}>
                    <button
                      type="button"
                      className="assistant-workspace__project-select"
                      aria-label={`${expanded ? "Contraer" : "Expandir"} ${project.name}`}
                      aria-expanded={expanded}
                      onClick={() => { setExpandedProjectSlug(expanded ? null : project.slug); }}
                    >
                      <Icon icon={expanded ? ChevronDown : ChevronRight} size="sm" />
                      <Icon icon={Folder} size="sm" />
                      <span>{project.name}</span>
                    </button>
                    <button type="button" className="assistant-workspace__project-chat" aria-label={`Iniciar chat en ${project.name}`} title={`Iniciar chat en ${project.name}`} onClick={() => navigateToProject(project, "threads")}><Icon icon={MessageSquarePlus} size="sm" /></button>
                  </div>
                  {expanded ? (
                    <div className="assistant-workspace__project-details">
                      <nav aria-label={`Navegación de ${project.name}`}>
                      <button type="button" className="assistant-workspace__history-trigger" onClick={() => navigateToProject(project, "context")}><Icon icon={FileText} size="sm" />Contexto y archivos</button>
                          <button type="button" className="assistant-workspace__history-trigger" aria-expanded={projectThreads[project.slug] !== undefined} onClick={() => { if (projectThreads[project.slug]) setProjectThreads((current) => { const next = { ...current }; delete next[project.slug]; return next; }); else void loadProjectThreads(project.slug); }}><Icon icon={History} size="sm" />Historial de hilos</button>
                          {projectThreads[project.slug] ? <div className="assistant-workspace__project-history">
                            {projectThreads[project.slug].state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando hilos" /> : null}
                            {projectThreads[project.slug].state === "error" || projectThreads[project.slug].state === "denied" ? <StateMessage tone="danger" role="alert" title={projectThreads[project.slug].state === "denied" ? "No tienes permiso para ver estos hilos." : "No pudimos cargar los hilos."} /> : null}
                            {projectThreads[project.slug].state === "empty" ? <p className="assistant-workspace__inline-empty">No hay hilos. Este proyecto aún no tiene hilos.</p> : null}
                            {projectThreads[project.slug].state === "ready" ? <GroupedThreadList projectName={project.name} threads={projectThreads[project.slug].threads} search={historySearch[project.slug] || ""} onSearch={(value) => setHistorySearch((current) => ({ ...current, [project.slug]: value }))} onOpen={(thread) => navigateToThread(thread.id, project.slug)} onThreadAction={(thread, action) => { setThreadActionError(null); if (action === "rename") { setRenameTarget({ id: thread.id, title: thread.title }); setRenameTitle(thread.title ?? ""); } else setDeleteTarget({ id: thread.id, title: thread.title }); }} /> : null}
                            {projectThreads[project.slug].state === "error" ? <Button variant="secondary" onClick={() => void loadProjectThreads(project.slug)}>Reintentar</Button> : null}
                            <a className="assistant-workspace__view-all-history" href={pathForRoute({ view: "chat", historyProjectSlug: project.slug })} onClick={(event) => { event.preventDefault(); navigateToHistory(project.slug); }}>Ver todos los hilos →</a>
                          </div> : null}
                      </nav>
                    </div>
                  ) : null}
                </div>
              );
            })
          )}
        </div>
        </section>
        <section className="assistant-workspace__agents" aria-label="Agentes" hidden={!projectsVisible}>
          {(() => {
            const agentTabs = openTabs.filter((tab): tab is Extract<WorkspaceTab, { kind: "thread" }> => tab.kind === "thread");
            return <><header><h3>Agentes <span className="assistant-workspace__agent-count">{agentTabs.length}</span></h3><button type="button" className="assistant-workspace__agents-toggle" aria-label={agentsExpanded ? "Contraer Agentes" : "Expandir Agentes"} aria-expanded={agentsExpanded} onClick={() => setAgentsExpanded((expanded) => !expanded)}><Icon icon={agentsExpanded ? ChevronDown : ChevronRight} size="sm" /></button></header>
          {agentsExpanded ? <>
          {agentTabs.length === 0 ? <p className="assistant-workspace__agents-empty">No hay agentes activos</p> : <ul>{agentTabs.map(({threadId: id}) => {
            const thread = [...threads, ...defaultThreads.threads, ...Object.values(projectThreads).flatMap((entry) => entry.threads)].find((item) => item.id === id);
            const run = activeRuns.runs.find((item) => item.thread_id === id);
            const slug = thread?.proyecto ?? run?.proyecto ?? (id === activeThreadId ? activeProjectSlug : undefined);
            const projectName = slug === "default" ? projects.find((project) => project.slug === slug)?.name ?? "General" : slug ? projects.find((project) => project.slug === slug)?.name ?? slug : "—";
            return <li key={id}><Avatar name="Orquestador" /><div className="assistant-workspace__agent-copy"><strong>Orquestador</strong><span className="assistant-workspace__agent-status"><i aria-hidden="true" />{run ? stageLabel(run.stage) : "Activo"}</span><p>{projectName}</p></div></li>;
          })}</ul>}
          </> : null}</>;
          })()}
        </section>
      </aside>

      <Dialog open={createProjectOpen} onClose={() => { setCreateProjectOpen(false); resetProjectForm(); }} title="Crear proyecto" variant="sheet">
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

      <section className="assistant-workspace__thread" aria-label="Área del hilo">
        {openTabs.length > 0 ? <nav className="assistant-workspace__thread-tabs" aria-label="Pestañas abiertas">
          <div className="assistant-workspace__thread-tab-list">
            {openTabs.map((tab) => {
              if (tab.kind === "context") {
                const project = projects.find((item) => item.slug === tab.projectSlug);
                const active = tab.projectSlug === activeContextSlug;
                const label = `Configuración · ${project?.name ?? tab.projectSlug}`;
                return <div className="assistant-workspace__thread-tab" key={`context:${tab.projectSlug}`} data-active={active}>
                  <button type="button" aria-current={active ? "page" : undefined} onClick={() => navigateToTab(tab)}>{label}</button>
                  <Menu label={`Acciones de ${label}`} trigger="icon" items={[{ value: "close", label: "Cerrar pestaña", icon: X }]} onSelect={(value) => { if (value === "close") closeTab(tab); }} />
                </div>;
              }
              if (tab.kind === "history") {
                const project = projects.find((item) => item.slug === tab.projectSlug);
                const label = `Historial · ${project?.name ?? tab.projectSlug}`;
                return <div className="assistant-workspace__thread-tab" key={`history:${tab.projectSlug}`} data-active={tab.projectSlug === activeHistorySlug}>
                  <button type="button" aria-current={tab.projectSlug === activeHistorySlug ? "page" : undefined} onClick={() => navigateToTab(tab)}>{label}</button>
                  <Menu label={`Acciones de ${label}`} trigger="icon" items={[{ value: "close", label: "Cerrar pestaña", icon: X }]} onSelect={(value) => { if (value === "close") closeTab(tab); }} />
                </div>;
              }
              const id = tab.threadId;
              const thread = [...threads, ...defaultThreads.threads, ...Object.values(projectThreads).flatMap((entry) => entry.threads)].find((item) => item.id === id);
              return <div className="assistant-workspace__thread-tab" key={id} data-active={id === activeThreadId}>
                <button type="button" aria-current={id === activeThreadId ? "page" : undefined} onClick={() => navigateToThread(id, thread?.proyecto)}>
                  {threadTitles[id] ?? thread?.title ?? "Sin título"}
                </button>
                <Menu
                  label={`Acciones de ${thread?.title || "hilo"}`}
                  trigger="icon"
                  items={[{ value: "rename", label: "Renombrar", icon: Pencil }, { value: "close", label: "Cerrar pestaña", icon: X }, { value: "delete", label: "Eliminar hilo", icon: Trash2, tone: "danger" }]}
                  onSelect={(value) => {
                    setThreadActionError(null);
                    if (value === "rename") { setRenameTarget({ id, title: thread?.title ?? null }); setRenameTitle(thread?.title ?? ""); }
                    else if (value === "close") closeTab(tab);
                    else setDeleteTarget({ id, title: thread?.title ?? null });
                  }}
                />
              </div>;
            })}
          </div>
          <Button variant="tertiary" aria-label="Crear nuevo hilo" title="Crear nuevo hilo" onClick={onCreateThread}>
            <Icon icon={Plus} />
          </Button>
        </nav> : null}
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
        {activeContextSlug ? <ProjectsPage projectSlug={activeContextSlug} role={role} onOpenChat={() => closeTab({ kind: "context", projectSlug: activeContextSlug })} onOpenThread={(threadId, slug) => navigateToThread(threadId, slug)} onOpenHistory={navigateToHistory} embedded /> : activeHistorySlug ? <ProjectHistory projectSlug={activeHistorySlug} projectName={projects.find((item) => item.slug === activeHistorySlug)?.name ?? activeHistorySlug} history={projectThreads[activeHistorySlug]} search={historySearch[activeHistorySlug] || ""} onSearch={(value) => setHistorySearch((current) => ({ ...current, [activeHistorySlug]: value }))} onOpen={(thread) => navigateToThread(thread.id, activeHistorySlug)} onThreadAction={(thread, action) => { setThreadActionError(null); if (action === "rename") { setRenameTarget({ id: thread.id, title: thread.title }); setRenameTitle(thread.title ?? ""); } else setDeleteTarget({ id: thread.id, title: thread.title }); }} onRetry={() => void loadProjectThreads(activeHistorySlug, 50)} /> : children}
      </section>

      <aside
        id="assistant-workspace-context"
        className="assistant-workspace__context"
        aria-label="Contexto del hilo"
        data-collapsed={!contextVisible}
      >
        <header className="assistant-workspace__pane-header assistant-workspace__context-header">
          <div className="assistant-workspace__context-title"><div><h2>Detalle del hilo</h2><p>{threadTitles[activeThreadId ?? 0] ?? activeThread?.title ?? "Sin título"}</p></div></div>
          <button type="button" className="assistant-workspace__pane-toggle" aria-label={contextVisible ? "Cerrar panel del hilo" : "Abrir panel del hilo"} aria-expanded={contextVisible} aria-controls="assistant-workspace-context" onClick={() => setContextVisible((visible) => !visible)}><Icon icon={PanelRight} /></button>
        </header>
        {contextVisible ? <>
        <Tabs
          ariaLabel="Panel del hilo"
          tabs={[{ id: "context", label: "Contexto" }]}
        >
          {() => <ThreadContextSections activeProject={activeProject} threadId={activeThreadId} capabilities={effectiveCapabilities} capabilitiesLoading={effectiveCapabilitiesLoading} capabilitiesError={effectiveCapabilitiesError} attachments={attachments} artifacts={artifacts} contextSections={contextSections} toggleContextSection={toggleContextSection} busyArtifactId={busyArtifactId} artifactError={artifactError} downloadArtifact={downloadArtifact} />}
        </Tabs>
        </> : null}
      </aside>
    </div>
  );
}

function ProjectHistory({ projectSlug, projectName, history, search, onSearch, onOpen, onThreadAction, onRetry }: { projectSlug: string; projectName: string; history?: { state: "loading" | "ready" | "empty" | "error" | "denied"; threads: InternalChatThreadSummary[] }; search: string; onSearch: (value: string) => void; onOpen: (thread: InternalChatThreadSummary) => void; onThreadAction: (thread: InternalChatThreadSummary, action: "rename" | "delete") => void; onRetry: () => void }) {
  return <section className="assistant-workspace__full-history" aria-label={`Historial de ${projectName}`} data-project={projectSlug}>
    <PageFrame title={`Historial · ${projectName}`}>
      <Card title="Hilos" className="assistant-workspace__history-card">
    {!history || history.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando hilos" /> : null}
    {history?.state === "error" || history?.state === "denied" ? <><StateMessage tone="danger" role="alert" title={history.state === "denied" ? "No tienes permiso para ver estos hilos." : "No pudimos cargar los hilos."} /><Button variant="secondary" onClick={onRetry}>Reintentar</Button></> : null}
    {history?.state === "empty" ? <EmptyState title="No hay hilos" description="Este proyecto aún no tiene hilos." /> : null}
    {history?.state === "ready" ? <GroupedThreadList projectName={projectName} projectSlug={projectSlug} threads={history.threads} search={search} onSearch={onSearch} onOpen={onOpen} onThreadAction={onThreadAction} paginate /> : null}
      </Card>
    </PageFrame>
  </section>;
}

function GroupedThreadList({ projectName, projectSlug, threads, search, onSearch, onOpen, onThreadAction, paginate = false }: { projectName: string; projectSlug?: string; threads: InternalChatThreadSummary[]; search: string; onSearch: (value: string) => void; onOpen: (thread: InternalChatThreadSummary) => void; onThreadAction: (thread: InternalChatThreadSummary, action: "rename" | "delete") => void; paginate?: boolean }) {
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [projectSlug, search]);
  const filtered = threads
    .filter((thread) => (thread.title || "Sin título").toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
    .sort((a, b) => activityTime(b) - activityTime(a));
  const pageSize = 20;
  const pageCount = Math.ceil(filtered.length / pageSize);
  const pageThreads = paginate ? filtered.slice((page - 1) * pageSize, page * pageSize) : filtered;
  const groups = groupThreadsByDate(pageThreads);
  return <>
    <SearchInput aria-label={`Buscar hilos de ${projectName}`} placeholder="Buscar hilo" onSearch={onSearch} />
      {groups.length ? <div className="assistant-workspace__thread-date-groups">{groups.map((group) => <section key={group.label} aria-label={group.label}>
      <h4>{group.label}</h4>
      <ul>{group.threads.map((thread) => <li key={thread.id} className="assistant-workspace__thread-row"><button type="button" className="assistant-workspace__thread-row-open" onClick={() => onOpen(thread)}><Icon icon={MessageSquareText} size="sm" /><span>{thread.title || "Sin título"}</span></button><Menu label={`Acciones de ${thread.title || "hilo"}`} trigger="icon" items={[{ value: "rename", label: "Renombrar", icon: Pencil }, { value: "delete", label: "Eliminar hilo", icon: Trash2, tone: "danger" }]} onSelect={(value) => onThreadAction(thread, value as "rename" | "delete")} /></li>)}</ul>
      </section>)}</div> : <p className="assistant-workspace__inline-empty">No encontramos hilos. Prueba con otro nombre.</p>}
     {paginate && pageCount > 1 ? <nav className="assistant-workspace__history-pagination" aria-label={`Paginación del historial de ${projectName}`}>
       <Button variant="secondary" aria-label="Página anterior" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>Anterior</Button>
       <span aria-live="polite">Página {page} de {pageCount}</span>
       <Button variant="secondary" aria-label="Página siguiente" disabled={page === pageCount} onClick={() => setPage((current) => current + 1)}>Siguiente</Button>
     </nav> : null}
   </>;
}

function activityTime(thread: InternalChatThreadSummary): number {
  const value = thread.updated_at || thread.created_at;
  const time = value ? new Date(value).getTime() : Number.NEGATIVE_INFINITY;
  return Number.isNaN(time) ? Number.NEGATIVE_INFINITY : time;
}

function ThreadContextSections({ activeProject, threadId, capabilities, capabilitiesLoading, capabilitiesError, attachments, artifacts, contextSections, toggleContextSection, busyArtifactId, artifactError, downloadArtifact, mobile = false }: { activeProject?: Project; threadId?: number; capabilities?: AssistantCapabilities | null; capabilitiesLoading: boolean; capabilitiesError: boolean; attachments: AssistantAttachment[]; artifacts: AssistantArtifact[]; contextSections: Record<string, boolean>; toggleContextSection: (id: string) => void; busyArtifactId: number | null; artifactError: string | null; downloadArtifact: (artifact: AssistantArtifact) => Promise<void>; mobile?: boolean }) {
  return <div className={mobile ? "assistant-workspace__thread-detail-sections" : "assistant-workspace__context-content"}>
    <ContextSection id={mobile ? "mobile-project" : "project"} title={mobile ? "Contexto del proyecto" : "Proyecto"} icon={Folder} expanded={contextSections.project ?? true} onToggle={() => toggleContextSection("project")}>
      {activeProject ? <div className="assistant-workspace__context-box"><div className="assistant-workspace__project-summary"><Icon icon={Folder} size="sm" /><strong>{activeProject.name}</strong><Badge tone={projectStatusTone(activeProject.status)}>{projectStatusLabel(activeProject.status)}</Badge></div><p>{activeProject.purpose}</p></div> : <EmptyState title="Elige un proyecto" description="Selecciona un proyecto para ver su contexto." />}
    </ContextSection>
    <ContextSection id={mobile ? "mobile-resources" : "resources"} title="Recursos del proyecto" icon={Share2} expanded={contextSections.resources ?? false} onToggle={() => toggleContextSection("resources")}><ThreadProjectResources threadId={threadId} expanded={contextSections.resources ?? false} /></ContextSection>
    <ContextSection id={mobile ? "mobile-capabilities" : "capabilities"} title="Capacidades del asistente" icon={BrainCircuit} count={capabilities ? undefined : "Sin datos"} expanded={contextSections.capabilities ?? false} onToggle={() => toggleContextSection("capabilities")}>
      {capabilitiesLoading ? <StateMessage tone="info" role="status" spinner title="Cargando capacidades" /> : capabilitiesError ? <StateMessage tone="danger" role="alert" title="No pudimos cargar las capacidades del asistente" /> : capabilities ? <div className="assistant-workspace__context-box"><p>{capabilities.tools?.length ?? 0} herramientas disponibles</p><p>Base de conocimientos: {capabilities.kb_available ? "Disponible" : "No disponible"}</p></div> : <div className="assistant-workspace__context-box">Sin información disponible.</div>}
    </ContextSection>
    <ContextSection id={mobile ? "mobile-attachments" : "attachments"} title="Archivos del hilo" icon={Paperclip} count={attachments.length} expanded={contextSections.attachments ?? false} onToggle={() => toggleContextSection("attachments")}>
      {attachments.length ? <ul className="assistant-workspace__file-list">{attachments.map((attachment) => <li key={attachment.id}><Icon icon={assistantFileIcon(attachment.filename, attachment.content_type)} size="sm" className={`assistant-workspace__file-icon assistant-workspace__file-icon--${fileTone(attachment.filename)}`} /><span className="assistant-workspace__file-copy"><strong title={attachment.filename}>{attachment.filename}</strong><small>{attachment.content_type?.split("/").at(-1)?.toLocaleUpperCase("es-CL") ?? "Archivo"} · Adjunto</small></span><a className="assistant-workspace__file-action" href={threadAttachmentContentUrl(attachment.thread_id, attachment.id)} target="_blank" rel="noreferrer" aria-label={`Abrir ${attachment.filename}`}>Abrir</a></li>)}</ul> : <div className="assistant-workspace__context-box assistant-workspace__context-box--empty"><Icon icon={Paperclip} size="sm" />Aún no hay archivos adjuntos.</div>}
    </ContextSection>
    <ContextSection id={mobile ? "mobile-artifacts" : "artifacts"} title="Artefactos del hilo" icon={FileText} count={artifacts.length} expanded={contextSections.artifacts ?? false} onToggle={() => toggleContextSection("artifacts")}>
      {artifacts.length ? <ul className="assistant-workspace__file-list">{artifacts.map((artifact) => <li key={artifact.id}><Icon icon={assistantFileIcon(artifact.filename, artifact.content_type)} size="sm" className={`assistant-workspace__file-icon assistant-workspace__file-icon--${fileTone(artifact.filename)}`} /><span className="assistant-workspace__file-copy"><strong title={artifact.filename}>{artifact.filename}</strong><small>Generado en este hilo</small></span><Button variant="tertiary" aria-label={`Descargar ${artifact.filename}`} disabled={busyArtifactId === artifact.id} onClick={() => void downloadArtifact(artifact)}><Icon icon={Download} size="sm" /></Button></li>)}</ul> : <div className="assistant-workspace__context-box">Los archivos que el asistente genere aparecerán aquí.</div>}
      {artifactError ? <StateMessage tone="danger" role="alert" title={artifactError} /> : null}
    </ContextSection>
    <ContextSection id={mobile ? "mobile-sources" : "sources"} title="Fuentes del hilo" icon={Link} count={0} expanded={contextSections.sources ?? false} onToggle={() => toggleContextSection("sources")}><div className="assistant-workspace__context-box">El hilo no entrega fuentes asociadas a sus respuestas.</div></ContextSection>
    <p className="assistant-workspace__context-note"><Icon icon={Info} size="sm" />Los adjuntos y resultados pertenecen a este hilo.</p>
  </div>;
}

function ContextSection({ id, title, icon, count, expanded = false, onToggle, children }: { id: string; title: string; icon: typeof Folder; count?: number | string; expanded?: boolean; onToggle: (id: string) => void; children: ReactNode }) {
  const panelId = `assistant-context-${id}`;
  return <section className="assistant-workspace__context-section">
    <button type="button" className="assistant-workspace__context-row" aria-expanded={expanded} aria-controls={panelId} onClick={() => onToggle(id)}>
      <Icon icon={icon} size="sm" /><span>{title}</span>{count !== undefined ? <span className="assistant-workspace__context-count">{count}</span> : null}<Icon icon={expanded ? ChevronDown : ChevronRight} size="sm" />
    </button>
    <div id={panelId} className="assistant-workspace__context-section-content" hidden={!expanded}>{children}</div>
  </section>;
}

function fileTone(filename: string): "pdf" | "sheet" | "document" | "neutral" {
  const extension = filename.split(".").pop()?.toLocaleLowerCase("en-US");
  if (extension === "pdf") return "pdf";
  if (["xlsx", "xls", "csv"].includes(extension ?? "")) return "sheet";
  if (["doc", "docx", "md", "markdown", "txt"].includes(extension ?? "")) return "document";
  return "neutral";
}
