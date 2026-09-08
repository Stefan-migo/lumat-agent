import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { listActiveConversations, listNotifications } from '../../api';
import { realtimeClient, type ConnectionStatus } from '../../realtime';
import type { ActiveConversationsResponse, NotificationsResponse } from '../../types';
import type { User } from '../../types';
import type { ActiveThreadsState, ConversationTab, NotificationState, PanelView } from './PanelShell';
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
import { AgendaPage } from '../pages/AgendaPage';
import { AutomationRulesPage } from '../pages/AutomationRulesPage';
import { AutomationRuleDetailPage } from '../pages/AutomationRuleDetailPage';
import { AdvancedDashboard } from '../pages/AdvancedDashboard';

/** Top-level SPA views. Client ficha and conversation thread are drill-downs
 * rendered from list views, not top-level nav, so they do not appear here. */
export type View = PanelView;

export interface AppShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
  activeThreads?: ActiveThreadsState;
  loadActiveThreads?: boolean;
  inspector?: ReactNode;
}

/** Application shell: PanelShell frame and native History API navigation. */
export function AppShell({ user, onLogout, activeThreads, loadActiveThreads = false, inspector }: AppShellProps) {
  const [route, setRoute] = useState<PanelRoute>(() => parsePanelPath(window.location.pathname));
  const [conversationTab, setConversationTab] = useState<ConversationTab>(() => parsePanelPath(window.location.pathname).view === 'cases' ? 'cases' : 'conversations');
  const [conversationRefresh, setConversationRefresh] = useState(0);
  const [creatingAutomationRule, setCreatingAutomationRule] = useState(false);
  const [railState, setRailState] = useState<ActiveThreadsState>({ status: 'loading' });
  const [connection, setConnection] = useState<ConnectionStatus>('disconnected');
  const [notificationState, setNotificationState] = useState<NotificationState>({ status: 'loading' });

  useEffect(() => {
    let mounted = true;
    void listNotifications().then((response: NotificationsResponse) => {
      if (mounted) setNotificationState({ status: 'ready', unread: response.notifications.filter((notification) => notification.read_at === null).length });
    }).catch(() => {
      if (mounted) setNotificationState({ status: 'error' });
    });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!loadActiveThreads || activeThreads !== undefined) return;
    let mounted = true;
    const load = async () => {
      setRailState((state) => state.status === 'ready' ? state : { status: 'loading' });
      try {
        const response: ActiveConversationsResponse = await listActiveConversations();
        if (mounted) setRailState(response.conversations.length === 0 ? { status: 'empty' } : {
          status: 'ready',
          threads: response.conversations.map((conversation) => ({
            id: conversation.id,
            label: conversation.customer_name ?? `Cliente #${conversation.id}`,
            status: conversation.state as 'bot' | 'human' | 'closed',
          })),
        });
      } catch {
        if (mounted) setRailState({ status: 'error' });
      }
    };
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.type === 'conversation' || event.type === 'message' || event.type === 'snapshot') void load();
    });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    void load();
    return () => { mounted = false; unsubscribe(); unsubscribeStatus(); };
  }, [activeThreads, loadActiveThreads]);

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
      setConversationTab(nextRoute.view === 'cases' ? 'cases' : 'conversations');
      setCreatingAutomationRule(false);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (nextView: PanelView) => {
    const nextRoute = { view: nextView } satisfies PanelRoute;
    window.history.pushState({}, '', pathForView(nextView));
    setRoute(nextRoute);
    setConversationTab(nextView === 'conversations' ? 'conversations' : conversationTab);
  };

  const navigateToRoute = (nextRoute: PanelRoute) => {
    window.history.pushState({}, '', pathForRoute(nextRoute));
    setRoute(nextRoute);
    if (nextRoute.view === 'cases') setConversationTab('cases');
    if (nextRoute.view === 'conversations') setConversationTab('conversations');
    setCreatingAutomationRule(false);
  };

  const navigateToCreateAutomationRule = () => {
    window.history.pushState({}, '', pathForView('automation-rules'));
    setRoute({ view: 'automation-rules' });
    setCreatingAutomationRule(true);
  };

  const view = route.view;
  const shellView = view === 'cases' ? 'conversations' : view;
  const clientId = route.clientId ?? null;
  const conversationId = route.conversationId ?? null;

  const page = view === 'dashboard' ? <Dashboard />
      : view === 'advanced-dashboard' ? <AdvancedDashboard />
      : view === 'agenda' ? <AgendaPage />
      : view === 'automation-rules' ? route.automationRuleId !== undefined || creatingAutomationRule ? <AutomationRuleDetailPage ruleId={creatingAutomationRule ? null : route.automationRuleId} user={user} onCreated={(id) => navigateToRoute({ view: 'automation-rules', automationRuleId: id })} onBack={() => { setCreatingAutomationRule(false); window.history.back(); }} /> : <AutomationRulesPage user={user} onOpenCreate={navigateToCreateAutomationRule} onOpenRule={(id) => navigateToRoute({ view: 'automation-rules', automationRuleId: id })} />
      : view === 'clients' ? clientId !== null ? <ClientFicha customerId={clientId} /> : <ClientesList onOpenClient={(id) => navigateToRoute({ view: 'clients', clientId: id })} />
       : view === 'conversations' || view === 'cases' ? conversationTab === 'cases' ? <CasesList onOpenClient={(id) => navigateToRoute({ view: 'clients', clientId: id })} /> : conversationId !== null ? <ConversationThread interactive conversationId={conversationId} refreshKey={conversationRefresh} onMutate={() => setConversationRefresh((value) => value + 1)} onBack={() => window.history.back()} /> : <ConversationsList refreshKey={conversationRefresh} onOpenThread={(id) => navigateToRoute({ view: 'conversations', conversationId: id })} />
     : view === 'notifications' ? <NotificationCenter />
     : view === 'push' ? <PushSettings />
      : view === 'chat' ? <AgentChat />
     : view === 'kb' ? <KbList />
    : <Settings />;

  return (
    <PanelShell user={user} currentView={shellView} conversationTab={conversationTab} onConversationTabChange={setConversationTab} onNavigate={navigate} onLogout={onLogout} notificationState={notificationState} activeThreads={activeThreads ?? railState} connectionStatus={connection} onActiveThread={(id) => navigateToRoute({ view: 'conversations', conversationId: id })} inspector={inspector}>
      {page}
    </PanelShell>
  );
}
