import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { listNotifications, markAllNotificationsRead } from '../../api';
import type { NotificationsResponse, PanelNotification } from '../../types';
import type { User } from '../../types';
import type { ConversationTab, NotificationState, PanelView } from './PanelShell';
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
  inspector?: ReactNode;
}

/** Application shell: PanelShell frame and native History API navigation. */
export function AppShell({ user, onLogout, inspector }: AppShellProps) {
  const [route, setRoute] = useState<PanelRoute>(() => parsePanelPath(window.location.pathname));
  const [conversationTab, setConversationTab] = useState<ConversationTab>(() => parsePanelPath(window.location.pathname).view === 'cases' ? 'cases' : 'conversations');
  const [conversationRefresh, setConversationRefresh] = useState(0);
  const [creatingAutomationRule, setCreatingAutomationRule] = useState(false);
  const [notificationState, setNotificationState] = useState<NotificationState>({ status: 'loading' });
  const [notifications, setNotifications] = useState<PanelNotification[]>([]);

  useEffect(() => {
    let mounted = true;
    void listNotifications().then((response: NotificationsResponse) => {
       if (mounted) {
         setNotifications(response.notifications);
         setNotificationState({ status: 'ready', unread: response.notifications.filter((notification) => notification.read_at === null).length });
       }
    }).catch(() => {
      if (mounted) setNotificationState({ status: 'error' });
    });
    return () => { mounted = false; };
  }, []);

  const markAllRead = async () => {
    await markAllNotificationsRead();
    const now = new Date().toISOString();
    setNotifications((current) => current.map((notification) => ({ ...notification, read_at: notification.read_at ?? now })));
    setNotificationState({ status: 'ready', unread: 0 });
  };

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
    <PanelShell user={user} currentView={shellView} conversationTab={conversationTab} onConversationTabChange={setConversationTab} onNavigate={navigate} onLogout={onLogout} notificationState={notificationState} notifications={notifications} onMarkAllNotificationsRead={markAllRead} inspector={inspector}>
      {page}
    </PanelShell>
  );
}
