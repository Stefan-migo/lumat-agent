import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { listNotifications, markAllNotificationsRead } from '../../api';
import type { NotificationsResponse, PanelNotification } from '../../types';
import type { User } from '../../types';
import type { NotificationState, PanelView } from './PanelShell';
import { PanelShell, isAdminOnlyView } from './PanelShell';
import { isDetailRoute, parsePanelPath, pathForRoute, pathForView, type PanelRoute } from './panelRoutes';
import { canOpen, defaultViewForRole } from './panelAccess';
import { Dashboard } from '../pages/Dashboard';
import { ClientesList } from '../pages/ClientesList';
import { ClientFicha } from '../pages/ClientFicha';
import { ConversationsList } from '../pages/ConversationsList';
import { ConversationThread } from '../pages/ConversationThread';
import { KbList } from '../pages/KbList';
import { KbDocumentDetail } from '../pages/KbDocumentDetail';
import { AppointmentDetail } from '../pages/AppointmentDetail';
import { Settings } from '../pages/Settings';
import { NotificationCenter } from '../pages/NotificationCenter';
import { PushSettings } from '../pages/PushSettings';
import { AgentChat } from '../pages/AgentChat';
import { AgendaPage } from '../pages/AgendaPage';
import { TechnicianAgenda } from '../pages/TechnicianAgenda';
import { AutomationRecipesPage } from '../pages/AutomationRecipesPage';
import { AdvancedDashboard } from '../pages/AdvancedDashboard';
import { ChatbotMetrics } from '../pages/ChatbotMetrics';
import { UserManagement } from '../pages/UserManagement';
import { ProjectsPage } from '../pages/ProjectsPage';
import { PlanningSessions } from '../pages/PlanningSessions';
import { SelfProfile } from '../pages/SelfProfile';
import { UserFicha } from '../pages/UserFicha';
import { realtimeClient } from '../../realtime';

/** Top-level SPA views. Client ficha and conversation thread are drill-downs
 * rendered from list views, not top-level nav, so they do not appear here. */
export type View = PanelView;

/** A role can only open the destinations its surface allows (S1/D1). Anything
 *  else — a hand-edited URL, a stale bookmark — falls back to the role's
 *  landing view, so no role ever renders a page it cannot use. */
function routeForRole(route: PanelRoute, role: User['role']): PanelRoute {
  const allowed = canOpen(role, route.view) && (role === 'admin' || !isAdminOnlyView(route.view));
  return allowed ? route : { view: defaultViewForRole(role) };
}

export interface AppShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
  inspector?: ReactNode;
}

/** Application shell: PanelShell frame and native History API navigation. */
export function AppShell({ user, onLogout, inspector }: AppShellProps) {
  const [route, setRoute] = useState<PanelRoute>(() => routeForRole(parsePanelPath(`${window.location.pathname}${window.location.search}`), user.role));
  const [conversationRefresh, setConversationRefresh] = useState(0);
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

  useEffect(() => {
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.type !== 'notification') return;
      void listNotifications().then((response) => {
        setNotifications(response.notifications);
        setNotificationState({ status: 'ready', unread: response.notifications.filter((notification) => notification.read_at === null).length });
      }).catch(() => setNotificationState({ status: 'error' }));
    });
    realtimeClient.connect();
    return () => { unsubscribe(); };
  }, []);

  const markAllRead = async () => {
    await markAllNotificationsRead();
    const now = new Date().toISOString();
    setNotifications((current) => current.map((notification) => ({ ...notification, read_at: notification.read_at ?? now })));
    setNotificationState({ status: 'ready', unread: 0 });
  };

  useEffect(() => {
    const parsed = routeForRole(parsePanelPath(`${window.location.pathname}${window.location.search}`), user.role);
    const canonicalPath = pathForRoute(parsed);
    if (`${window.location.pathname}${window.location.search}` !== canonicalPath) {
      window.history.replaceState({}, '', canonicalPath);
      setRoute(parsed);
    }

    const handlePopState = () => {
      const nextRoute = routeForRole(parsePanelPath(`${window.location.pathname}${window.location.search}`), user.role);
      const nextPath = pathForRoute(nextRoute);
      if (`${window.location.pathname}${window.location.search}` !== nextPath) window.history.replaceState({}, '', nextPath);
      setRoute(nextRoute);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [user.role]);

  const navigate = (nextView: PanelView) => {
    const requested: PanelRoute = nextView === 'cases'
      ? { view: 'conversations', conversationTab: 'case' }
      : { view: nextView };
    const nextRoute = routeForRole(requested, user.role);
    window.history.pushState({}, '', pathForRoute(nextRoute));
    setRoute(nextRoute);
  };

  const navigateToRoute = (requested: PanelRoute) => {
    const nextRoute = routeForRole(requested, user.role);
    window.history.pushState({}, '', pathForRoute(nextRoute));
    setRoute(nextRoute);
  };

  const view = route.view;
  const onBack = isDetailRoute(route)
    ? () => navigateToRoute({ view, ...(view === 'conversations' && route.conversationTab ? { conversationTab: route.conversationTab } : {}) })
    : undefined;
  const shellView = view === 'cases' ? 'conversations' : view === 'projects' || view === 'planning-sessions' ? 'chat' : view;
  const clientId = route.clientId ?? null;
  const userId = route.userId ?? null;
  const conversationId = route.conversationId ?? null;
  const kbDocId = route.kbDocId ?? null;
  const appointmentId = route.appointmentId ?? null;

  const page = view === 'dashboard' ? <Dashboard role={user.role} onNavigate={navigate} onOpenRoute={navigateToRoute} />
      : view === 'advanced-dashboard' ? <AdvancedDashboard />
      : view === 'chatbot-metrics' ? <ChatbotMetrics onOpenConversation={(id) => navigateToRoute({ view: 'conversations', conversationId: id })} />
      : view === 'agenda' ? appointmentId !== null ? <AppointmentDetail appointmentId={appointmentId} role={user.role} /> : user.role === 'tecnico' ? <TechnicianAgenda /> : <AgendaPage />
      : view === 'automation-rules' ? <AutomationRecipesPage />
      : view === 'clients' ? clientId !== null ? <ClientFicha customerId={clientId} initialTab={route.clientTab} /> : <ClientesList onOpenClient={(id) => navigateToRoute({ view: 'clients', clientId: id })} />
        : view === 'conversations' ? conversationId !== null ? <ConversationThread interactive conversationId={conversationId} refreshKey={conversationRefresh} onMutate={() => setConversationRefresh((value) => value + 1)} onBack={() => window.history.back()} /> : <ConversationsList currentUserId={user.id} initialQueueTab={route.conversationTab ?? 'all'} onQueueTabChange={(tab) => navigateToRoute({ view: 'conversations', conversationTab: tab })} refreshKey={conversationRefresh} onOpenThread={(id) => navigateToRoute({ view: 'conversations', conversationId: id })} />
     : view === 'notifications' ? <NotificationCenter />
     : view === 'push' ? <PushSettings />
                : view === 'chat' ? <AgentChat role={user.role} userName={user.name?.trim() || user.username} onThreadOpened={(id) => navigateToRoute({ view: 'chat', threadId: id })} />
       : view === 'kb' ? kbDocId !== null ? <KbDocumentDetail documentId={kbDocId} /> : <KbList onOpenDocument={(id) => navigateToRoute({ view: 'kb', kbDocId: id })} />
        : view === 'users' ? user.role !== 'admin' ? <div role="alert">No tienes permiso para ver este panel</div> : userId !== null ? <UserFicha userId={userId} /> : <UserManagement currentUser={user} onOpenUser={(id) => navigateToRoute({ view: 'users', userId: id })} />
       : view === 'profile' ? <SelfProfile />
            : view === 'projects' ? <ProjectsPage projectSlug={route.projectSlug} role={user.role} onOpenProject={(slug) => navigateToRoute({ view: 'projects', projectSlug: slug })} onOpenChat={(slug) => navigateToRoute({ view: 'chat', projectSlug: slug })} onOpenThread={(threadId) => navigateToRoute({ view: 'chat', threadId })} onOpenHistory={(slug) => navigateToRoute({ view: 'chat', historyProjectSlug: slug })} />
         : view === 'planning-sessions' ? <PlanningSessions projectSlug={route.projectSlug} sessionSlug={route.planningSessionSlug} onOpenSession={(slug) => navigateToRoute({ view: 'planning-sessions', planningSessionSlug: slug })} onOpenThread={(id) => { window.history.pushState({}, '', `${pathForView('chat')}?thread_id=${id}`); setRoute({ view: 'chat' }); }} />
      : <Settings />;

  return (
    <PanelShell user={user} currentView={shellView} collapseRail={view === "chat"} breadcrumbView={view} onBack={onBack} onNavigate={navigate} onLogout={onLogout} notificationState={notificationState} notifications={notifications} onMarkAllNotificationsRead={markAllRead} inspector={inspector}>
      {page}
    </PanelShell>
  );
}
