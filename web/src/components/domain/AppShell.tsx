import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { listNotifications, markAllNotificationsRead } from '../../api';
import type { NotificationsResponse, PanelNotification } from '../../types';
import type { User } from '../../types';
import type { NotificationState, PanelView } from './PanelShell';
import { PanelShell } from './PanelShell';
import { isDetailRoute, parsePanelPath, pathForRoute, pathForView, type PanelRoute } from './panelRoutes';
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
import { AutomationRecipesPage } from '../pages/AutomationRecipesPage';
import { AdvancedDashboard } from '../pages/AdvancedDashboard';
import { UserManagement } from '../pages/UserManagement';
import { ProjectsPage } from '../pages/ProjectsPage';
import { PlanningSessions } from '../pages/PlanningSessions';
import { SelfProfile } from '../pages/SelfProfile';
import { UserFicha } from '../pages/UserFicha';
import { AssistantTabs, type AssistantView } from '../pages/AssistantTabs';

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
  const [route, setRoute] = useState<PanelRoute>(() => parsePanelPath(`${window.location.pathname}${window.location.search}`));
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

  const markAllRead = async () => {
    await markAllNotificationsRead();
    const now = new Date().toISOString();
    setNotifications((current) => current.map((notification) => ({ ...notification, read_at: notification.read_at ?? now })));
    setNotificationState({ status: 'ready', unread: 0 });
  };

  useEffect(() => {
    const parsed = parsePanelPath(`${window.location.pathname}${window.location.search}`);
    const canonicalPath = pathForRoute(parsed);
    if (`${window.location.pathname}${window.location.search}` !== canonicalPath) {
      window.history.replaceState({}, '', canonicalPath);
      setRoute(parsed);
    }

    const handlePopState = () => {
      const nextRoute = parsePanelPath(`${window.location.pathname}${window.location.search}`);
      const nextPath = pathForRoute(nextRoute);
      if (`${window.location.pathname}${window.location.search}` !== nextPath) window.history.replaceState({}, '', nextPath);
      setRoute(nextRoute);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (nextView: PanelView) => {
    const nextRoute: PanelRoute = nextView === 'cases'
      ? { view: 'conversations', conversationTab: 'case' }
      : { view: nextView };
    window.history.pushState({}, '', pathForRoute(nextRoute));
    setRoute(nextRoute);
  };

  const navigateToRoute = (nextRoute: PanelRoute) => {
    window.history.pushState({}, '', pathForRoute(nextRoute));
    setRoute(nextRoute);
  };

  const view = route.view;
  const onBack = isDetailRoute(route)
    ? () => navigateToRoute({ view, ...(view === 'conversations' && route.conversationTab ? { conversationTab: route.conversationTab } : {}) })
    : undefined;
  const shellView = view === 'cases' ? 'conversations' : view === 'projects' || view === 'planning-sessions' ? 'chat' : view;
  const assistantView: AssistantView = view === 'projects' || view === 'planning-sessions' ? view : 'chat';
  const sectionTabs = <AssistantTabs active={assistantView} onSelect={(target) => navigateToRoute({ view: target })} />;
  const clientId = route.clientId ?? null;
  const userId = route.userId ?? null;
  const conversationId = route.conversationId ?? null;
  const kbDocId = route.kbDocId ?? null;
  const appointmentId = route.appointmentId ?? null;

  const page = view === 'dashboard' ? <Dashboard role={user.role} onNavigate={navigate} />
      : view === 'advanced-dashboard' ? <AdvancedDashboard />
      : view === 'agenda' ? appointmentId !== null ? <AppointmentDetail appointmentId={appointmentId} /> : <AgendaPage />
      : view === 'automation-rules' ? <AutomationRecipesPage />
      : view === 'clients' ? clientId !== null ? <ClientFicha customerId={clientId} initialTab={route.clientTab} /> : <ClientesList onOpenClient={(id) => navigateToRoute({ view: 'clients', clientId: id })} />
        : view === 'conversations' ? conversationId !== null ? <ConversationThread interactive conversationId={conversationId} refreshKey={conversationRefresh} onMutate={() => setConversationRefresh((value) => value + 1)} onBack={() => window.history.back()} /> : <ConversationsList currentUserId={user.id} initialQueueTab={route.conversationTab ?? 'all'} onQueueTabChange={(tab) => navigateToRoute({ view: 'conversations', conversationTab: tab })} refreshKey={conversationRefresh} onOpenThread={(id) => navigateToRoute({ view: 'conversations', conversationId: id })} />
     : view === 'notifications' ? <NotificationCenter />
     : view === 'push' ? <PushSettings />
           : view === 'chat' ? <AgentChat role={user.role} sectionTabs={sectionTabs} onThreadOpened={(id) => navigateToRoute({ view: 'chat', threadId: id })} />
       : view === 'kb' ? kbDocId !== null ? <KbDocumentDetail documentId={kbDocId} /> : <KbList onOpenDocument={(id) => navigateToRoute({ view: 'kb', kbDocId: id })} />
        : view === 'users' ? user.role !== 'admin' ? <div role="alert">No tienes permiso para ver este panel</div> : userId !== null ? <UserFicha userId={userId} /> : <UserManagement currentUser={user} onOpenUser={(id) => navigateToRoute({ view: 'users', userId: id })} />
       : view === 'profile' ? <SelfProfile />
          : view === 'projects' ? <ProjectsPage sectionTabs={sectionTabs} projectSlug={route.projectSlug} role={user.role} onOpenProject={(slug) => navigateToRoute({ view: 'projects', projectSlug: slug })} onOpenChat={(slug) => navigateToRoute({ view: 'chat', projectSlug: slug })} />
        : view === 'planning-sessions' ? <PlanningSessions sectionTabs={sectionTabs} sessionSlug={route.planningSessionSlug} onOpenSession={(slug) => navigateToRoute({ view: 'planning-sessions', planningSessionSlug: slug })} onOpenThread={(id) => { window.history.pushState({}, '', `${pathForView('chat')}?thread_id=${id}`); setRoute({ view: 'chat' }); }} />
      : <Settings />;

  return (
    <PanelShell user={user} currentView={shellView} collapseRail={view === "chat"} breadcrumbView={view} onBack={onBack} onNavigate={navigate} onLogout={onLogout} notificationState={notificationState} notifications={notifications} onMarkAllNotificationsRead={markAllRead} inspector={inspector}>
      {page}
    </PanelShell>
  );
}
