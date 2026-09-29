import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Button } from '../primitives/Button';
import type { User } from '../../types';
import type { PanelRoute } from './panelRoutes';
import { parsePanelPath, pathForRoute } from './panelRoutes';
import { AgentChat } from '../pages/AgentChat';
import { AssistantTabs, type AssistantView } from '../pages/AssistantTabs';
import { PlanningSessions } from '../pages/PlanningSessions';
import { ProjectsPage } from '../pages/ProjectsPage';
import { TechnicianAgenda } from '../pages/TechnicianAgenda';

export interface TechnicianShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
  /** Legacy caller content is intentionally ignored; routes own the technician view. */
  children?: ReactNode;
}

const technicianViews = new Set(['agenda', 'chat', 'projects', 'planning-sessions']);

function technicianRoute(path: string): PanelRoute {
  const parsed = parsePanelPath(path);
  return technicianViews.has(parsed.view) ? parsed : { view: 'agenda' };
}

/** Session chrome and URL-backed restricted view routing for the technician surface. */
export function TechnicianShell({ user, onLogout, children }: TechnicianShellProps) {
  const [route, setRoute] = useState(() => technicianRoute(`${window.location.pathname}${window.location.search}`));

  useEffect(() => {
    const canonicalize = (path: string) => {
      const next = technicianRoute(path);
      const canonicalPath = pathForRoute(next);
      if (path !== canonicalPath) window.history.replaceState({}, '', canonicalPath);
      return next;
    };
    setRoute(canonicalize(`${window.location.pathname}${window.location.search}`));
    const onPopState = () => setRoute(canonicalize(`${window.location.pathname}${window.location.search}`));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = (nextRoute: PanelRoute) => {
    const safeRoute = technicianViews.has(nextRoute.view) ? nextRoute : { view: 'agenda' as const };
    window.history.pushState({}, '', pathForRoute(safeRoute));
    setRoute(safeRoute);
  };
  const view = route.view;
  const assistantView: AssistantView = view === 'projects' || view === 'planning-sessions' ? view : 'chat';
  const sectionTabs = <AssistantTabs active={assistantView} onSelect={(target) => navigate({ view: target })} />;
  const page = view === 'chat'
    ? <AgentChat role="tecnico" sectionTabs={sectionTabs} onThreadOpened={(id) => navigate({ view: 'chat', threadId: id })} />
    : view === 'projects'
      ? <ProjectsPage sectionTabs={sectionTabs} projectSlug={route.projectSlug} onOpenProject={(slug) => navigate({ view: 'projects', projectSlug: slug })} onOpenChat={(slug) => navigate({ view: 'chat', projectSlug: slug })} />
      : view === 'planning-sessions'
        ? <PlanningSessions sectionTabs={sectionTabs} sessionSlug={route.planningSessionSlug} onOpenSession={(slug) => navigate({ view: 'planning-sessions', planningSessionSlug: slug })} onOpenThread={(id) => navigate({ view: 'chat', threadId: id })} />
        : children ?? <TechnicianAgenda />;

  return (
    <div className="technician-shell">
      <header className="technician-shell__header">
        <div className="technician-shell__header-inner">
          <div className="technician-shell__brand">
            <img src="/panel/app/brand/lumat-logo.png" alt="Lumat" />
            <span>{user.username}</span>
          </div>
          {onLogout ? <Button variant="secondary" onClick={() => void onLogout()}>Cerrar sesión</Button> : null}
        </div>
      </header>
      <div className="technician-shell__content panel-shell__content">{page}</div>
      <nav className="panel-shell__footer-nav" aria-label="Navegación del técnico">
        {(['agenda', 'chat', 'projects', 'planning-sessions'] as const).map((target) => {
          const label = target === 'agenda' ? 'Agenda' : target === 'chat' ? 'Asistente' : target === 'projects' ? 'Proyectos' : 'Sesiones de planificación';
          return <button key={target} type="button" aria-current={view === target ? 'page' : undefined} onClick={() => navigate({ view: target })}><span>{label}</span></button>;
        })}
      </nav>
    </div>
  );
}
