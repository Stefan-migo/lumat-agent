import { useEffect, useState } from 'react';
import type { User } from '../../types';
import type { PanelView } from './PanelShell';
import { PanelShell } from './PanelShell';
import { parsePanelPath, pathForRoute, pathForView, type PanelRoute } from './panelRoutes';
import { Dashboard } from '../pages/Dashboard';
import { ClientesList } from '../pages/ClientesList';
import { ClientFicha } from '../pages/ClientFicha';
import { CasesList } from '../pages/CasesList';
import { ConversationsList } from '../pages/ConversationsList';
import { ConversationThread } from '../pages/ConversationThread';
import { KbList } from '../pages/KbList';
import { Settings } from '../pages/Settings';
import { NotificationCenter } from '../pages/NotificationCenter';
import { PushSettings } from '../pages/PushSettings';
import { AgentChat } from '../pages/AgentChat';

/** Top-level SPA views. Client ficha and conversation thread are drill-downs
 * rendered from list views, not top-level nav, so they do not appear here. */
export type View = PanelView;

export interface AppShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
}

/** Application shell: PanelShell frame and native History API navigation. */
export function AppShell({ user, onLogout }: AppShellProps) {
  const [route, setRoute] = useState<PanelRoute>(() => parsePanelPath(window.location.pathname));
  const [conversationRefresh, setConversationRefresh] = useState(0);

  useEffect(() => {
    const parsed = parsePanelPath(window.location.pathname);
    const canonicalPath = pathForRoute(parsed);
    if (window.location.pathname !== canonicalPath) {
      window.history.replaceState({}, '', canonicalPath);
      setRoute(parsed);
    }

    const handlePopState = () => {
      const nextRoute = parsePanelPath(window.location.pathname);
      const nextPath = pathForRoute(nextRoute);
      if (window.location.pathname !== nextPath) window.history.replaceState({}, '', nextPath);
      setRoute(nextRoute);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (nextView: PanelView) => {
    const nextRoute = { view: nextView } satisfies PanelRoute;
    window.history.pushState({}, '', pathForView(nextView));
    setRoute(nextRoute);
  };

  const navigateToRoute = (nextRoute: PanelRoute) => {
    window.history.pushState({}, '', pathForRoute(nextRoute));
    setRoute(nextRoute);
  };

  const view = route.view;
  const clientId = route.clientId ?? null;
  const conversationId = route.conversationId ?? null;

  const page = view === 'dashboard' ? <Dashboard />
      : view === 'clients' ? clientId !== null ? <ClientFicha customerId={clientId} /> : <ClientesList onOpenClient={(id) => navigateToRoute({ view: 'clients', clientId: id })} />
      : view === 'conversations' ? conversationId !== null ? <ConversationThread interactive conversationId={conversationId} refreshKey={conversationRefresh} onMutate={() => setConversationRefresh((value) => value + 1)} onBack={() => window.history.back()} /> : <ConversationsList refreshKey={conversationRefresh} onOpenThread={(id) => navigateToRoute({ view: 'conversations', conversationId: id })} />
      : view === 'cases' ? <CasesList onOpenClient={(id) => navigateToRoute({ view: 'clients', clientId: id })} />
     : view === 'notifications' ? <NotificationCenter />
     : view === 'push' ? <PushSettings />
      : view === 'chat' ? <AgentChat />
     : view === 'kb' ? <KbList />
    : <Settings />;

  return (
    <PanelShell user={user} currentView={view} onNavigate={navigate} onLogout={onLogout}>
      {page}
    </PanelShell>
  );
}
