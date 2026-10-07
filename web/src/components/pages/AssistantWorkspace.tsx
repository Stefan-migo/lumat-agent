import { useEffect, useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { EmptyState } from "../shared/EmptyState";
import "./AssistantWorkspace.css";

export function AssistantWorkspace({ children }: { children: ReactNode }) {
  const [projectsVisible, setProjectsVisible] = useState(() => window.innerWidth > 1024);
  const [contextVisible, setContextVisible] = useState(() => window.innerWidth > 1024);

  useEffect(() => {
    const updateForViewport = () => {
      const wide = window.innerWidth > 1024;
      setProjectsVisible(wide);
      setContextVisible(wide);
    };
    window.addEventListener("resize", updateForViewport);
    return () => window.removeEventListener("resize", updateForViewport);
  }, []);

  return (
    <div
      className={`assistant-workspace${projectsVisible ? " assistant-workspace--projects-visible" : ""}${contextVisible ? " assistant-workspace--context-visible" : ""}`}
      data-testid="assistant-workspace"
    >
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
        <SearchInput aria-label="Buscar proyectos" placeholder="Buscar proyectos" onSearch={() => undefined} />
        <div className="assistant-workspace__projects-list">
          <EmptyState title="Tus proyectos aparecerán aquí" />
        </div>
      </aside>

      <section className="assistant-workspace__thread" aria-label="Área del hilo">
        <div className="assistant-workspace__controls">
          <Button
            variant="tertiary"
            aria-label="Mostrar u ocultar proyectos"
            aria-expanded={projectsVisible}
            aria-controls="assistant-workspace-projects"
            onClick={() => setProjectsVisible((visible) => !visible)}
          >
            Proyectos
          </Button>
          <Button
            variant="tertiary"
            aria-label="Mostrar u ocultar el panel de contexto"
            aria-expanded={contextVisible}
            aria-controls="assistant-workspace-context"
            onClick={() => setContextVisible((visible) => !visible)}
          >
            Contexto
          </Button>
        </div>
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
