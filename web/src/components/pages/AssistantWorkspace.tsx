import { useCallback, useMemo, useState, type ReactNode } from "react";
import { FolderKanban, MessageSquarePlus, PanelRight, Plus } from "lucide-react";
import { createChatThread, listProjects } from "../../api";
import type { Project } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";
import { projectStatusLabel, projectStatusTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";
import "./AssistantWorkspace.css";

export function AssistantWorkspace({ children }: { children: ReactNode }) {
  const [projectsVisible, setProjectsVisible] = useState(() => window.innerWidth > 1024);
  const [contextVisible, setContextVisible] = useState(() => window.innerWidth > 1024);
  const [creatingThread, setCreatingThread] = useState(false);
  const [threadError, setThreadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const loadProjects = useCallback(() => listProjects(), []);
  const projectsData = useAsyncData(loadProjects, projectsVisible);
  const projects = projectsData.data?.projects ?? [];
  const visibleProjects = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return query ? projects.filter((project) => project.name.toLocaleLowerCase().includes(query)) : projects;
  }, [projects, search]);

  const navigateToProject = (project: Project, destination: "context" | "threads") => {
    const route = destination === "context"
      ? { view: "projects" as const, projectSlug: project.slug }
      : { view: "chat" as const, projectSlug: project.slug };
    window.history.pushState({}, "", pathForRoute(route));
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const createThread = async () => {
    const project = projects.find((item) => item.slug === selectedProject);
    if (!project || creatingThread) return;
    setCreatingThread(true);
    setThreadError(null);
    try {
      const result = await createChatThread(project.slug);
      window.history.pushState({}, "", pathForRoute({ view: "chat", projectSlug: project.slug, threadId: result.thread.id }));
      window.dispatchEvent(new PopStateEvent("popstate"));
    } catch {
      setThreadError("No pudimos crear el hilo.");
    } finally {
      setCreatingThread(false);
    }
  };

  return (
    <div
      className={`assistant-workspace${projectsVisible ? " assistant-workspace--projects-visible" : ""}${contextVisible ? " assistant-workspace--context-visible" : ""}`}
      data-testid="assistant-workspace"
    >
      <nav className="assistant-workspace__rail" aria-label="Controles del espacio de trabajo">
        <button type="button" className="assistant-workspace__rail-button" aria-label="Mostrar u ocultar proyectos" aria-expanded={projectsVisible} aria-controls="assistant-workspace-projects" title="Proyectos" onClick={() => setProjectsVisible((visible) => !visible)}>
          <Icon icon={FolderKanban} />
        </button>
        <button type="button" className="assistant-workspace__rail-button" aria-label="Mostrar u ocultar el panel de contexto" aria-expanded={contextVisible} aria-controls="assistant-workspace-context" title="Contexto" onClick={() => setContextVisible((visible) => !visible)}>
          <Icon icon={PanelRight} />
        </button>
        <button type="button" className="assistant-workspace__rail-button" aria-label="Crear hilo" title={selectedProject ? "Crear hilo" : "Selecciona un proyecto para crear un hilo"} disabled={!selectedProject || creatingThread} onClick={() => void createThread()}>
          <Icon icon={MessageSquarePlus} />
        </button>
      </nav>
      {projectsVisible || contextVisible ? <button type="button" className="assistant-workspace__scrim" aria-label="Cerrar paneles" onClick={() => { setProjectsVisible(false); setContextVisible(false); }} /> : null}
      <aside
        id="assistant-workspace-projects"
        className="assistant-workspace__projects"
        aria-label="Proyectos"
        hidden={!projectsVisible}
      >
        <header className="assistant-workspace__pane-header">
          <h2>Proyectos</h2>
          <Button variant="tertiary" aria-label="Crear proyecto" disabled>
            <Icon icon={Plus} />
          </Button>
        </header>
        <SearchInput aria-label="Buscar proyectos" placeholder="Buscar proyectos" onSearch={setSearch} />
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
                <Card className="assistant-workspace__project-card" key={project.slug}>
                  <div className="assistant-workspace__project-row">
                    <button
                      type="button"
                      className="assistant-workspace__project-select"
                      aria-expanded={expanded}
                      onClick={() => setSelectedProject(expanded ? null : project.slug)}
                    >
                      <span>{project.name}</span>
                      <Badge tone={projectStatusTone(project.status)}>{projectStatusLabel(project.status)}</Badge>
                    </button>
                    <Menu
                      label={`Acciones de ${project.name}`}
                      trigger="icon"
                      items={[
                        { value: "context", label: "Contexto y archivos" },
                        { value: "threads", label: "Historial de hilos" },
                      ]}
                      onSelect={(value) => navigateToProject(project, value === "context" ? "context" : "threads")}
                    />
                  </div>
                  {expanded ? (
                    <div className="assistant-workspace__project-details">
                      <nav aria-label={`Navegación de ${project.name}`}>
                        <a href={pathForRoute({ view: "projects", projectSlug: project.slug })}>Contexto y archivos</a>
                        <a href={pathForRoute({ view: "chat", projectSlug: project.slug })}>Historial de hilos</a>
                      </nav>
                      <section aria-label="Agentes del proyecto">
                        <h3>Agentes del proyecto</h3>
                        <EmptyState title="Aún no hay agentes disponibles" description="La gestión de agentes por proyecto todavía no está disponible." />
                      </section>
                    </div>
                  ) : null}
                </Card>
              );
            })
          )}
        </div>
      </aside>

      <section className="assistant-workspace__thread" aria-label="Área del hilo">
        {threadError ? <StateMessage tone="danger" role="alert" title={threadError} /> : null}
        {children}
      </section>

      <aside
        id="assistant-workspace-context"
        className="assistant-workspace__context"
        aria-label="Contexto del hilo"
        hidden={!contextVisible}
      >
        <h2>Contexto del hilo</h2>
        <Tabs
          ariaLabel="Panel del hilo"
          tabs={[{ id: "agents", label: "Agentes" }, { id: "context", label: "Contexto" }]}
        >
          {(tab) => tab === "agents" ? (
            <Card title="Agentes">
              <EmptyState title="No hay agentes activos" description="La actividad del hilo aparecerá aquí." />
            </Card>
          ) : (
            <Card title="Contexto">
              <EmptyState title="Sin contexto adicional" description="Los recursos del hilo aparecerán aquí." />
            </Card>
          )}
        </Tabs>
      </aside>
    </div>
  );
}
