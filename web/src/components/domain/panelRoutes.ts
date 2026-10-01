import type { PanelView } from './PanelShell';

export type PanelRoute = {
  view: PanelView;
  conversationTab?: 'all' | 'human' | 'emergency' | 'case' | 'closed';
  clientId?: number;
  userId?: number;
  conversationId?: number;
  automationRuleId?: number;
  kbDocId?: number;
  appointmentId?: number;
  projectSlug?: string;
  threadId?: number;
  planningSessionSlug?: string;
};

export const PANEL_BASE_PATH = '/panel/app/';

export function isDetailRoute(route: PanelRoute): boolean {
  return (route.view === 'clients' && route.clientId !== undefined && Number.isSafeInteger(route.clientId) && route.clientId > 0)
    || (route.view === 'conversations' && route.conversationId !== undefined && Number.isSafeInteger(route.conversationId) && route.conversationId > 0)
    || (route.view === 'automation-rules' && route.automationRuleId !== undefined && Number.isSafeInteger(route.automationRuleId) && route.automationRuleId > 0)
    || (route.view === 'kb' && route.kbDocId !== undefined && Number.isSafeInteger(route.kbDocId) && route.kbDocId > 0)
    || (route.view === 'agenda' && route.appointmentId !== undefined && Number.isSafeInteger(route.appointmentId) && route.appointmentId > 0)
    || (route.view === 'projects' && Boolean(route.projectSlug))
    || (route.view === 'planning-sessions' && Boolean(route.planningSessionSlug));
}

export const PANEL_ROUTES = {
  dashboard: PANEL_BASE_PATH,
  chat: '/panel/app/chat',
  conversations: '/panel/app/conversations',
  clients: '/panel/app/clients',
  agenda: '/panel/app/agenda',
  kb: '/panel/app/kb',
  'automation-rules': '/panel/app/automation-rules',
  settings: '/panel/app/settings',
  users: '/panel/app/users',
  profile: '/panel/app/profile',
  projects: '/panel/app/projects',
  'planning-sessions': '/panel/app/planning-sessions',
} as const satisfies Readonly<Partial<Record<PanelView, string>>>;

const COMPATIBILITY_ROUTES: Readonly<Partial<Record<PanelView, string>>> = {
  cases: '/panel/app/cases',
  notifications: '/panel/app/notifications',
  push: '/panel/app/push',
  'advanced-dashboard': '/panel/app/advanced-dashboard',
};

const panelViews = new Set<PanelView>([
  ...(Object.keys(PANEL_ROUTES) as PanelView[]),
  ...(Object.keys(COMPATIBILITY_ROUTES) as PanelView[]),
]);

export function pathForView(view: PanelView): string {
  if (view === 'cases') return COMPATIBILITY_ROUTES.cases!;
  return PANEL_ROUTES[view as keyof typeof PANEL_ROUTES] ?? COMPATIBILITY_ROUTES[view] ?? PANEL_BASE_PATH;
}

export function pathForRoute(route: PanelRoute): string {
  if (route.view === 'conversations' && route.conversationTab === 'case') return COMPATIBILITY_ROUTES.cases!;
  const base = pathForView(route.view);
  if (route.view === 'conversations' && route.conversationTab && route.conversationTab !== 'all') {
    return `${base}?tab=${route.conversationTab}`;
  }
  if (route.view === 'clients' && route.clientId !== undefined && Number.isSafeInteger(route.clientId) && route.clientId > 0) {
    return `${base}/${route.clientId}`;
  }
  if (route.view === 'users' && route.userId !== undefined && Number.isSafeInteger(route.userId) && route.userId > 0) {
    return `${base}/${route.userId}`;
  }
  if (route.view === 'conversations' && route.conversationId !== undefined && Number.isSafeInteger(route.conversationId) && route.conversationId > 0) {
    return `${base}/${route.conversationId}`;
  }
  if (route.view === 'automation-rules' && route.automationRuleId !== undefined && Number.isSafeInteger(route.automationRuleId) && route.automationRuleId > 0) {
    return `${base}/${route.automationRuleId}`;
  }
  if (route.view === 'kb' && route.kbDocId !== undefined && Number.isSafeInteger(route.kbDocId) && route.kbDocId > 0) {
    return `${base}/${route.kbDocId}`;
  }
  if (route.view === 'agenda' && route.appointmentId !== undefined && Number.isSafeInteger(route.appointmentId) && route.appointmentId > 0) {
    return `${base}/${route.appointmentId}`;
  }
  if (route.view === 'projects' && route.projectSlug) return `${base}/${encodeURIComponent(route.projectSlug)}`;
  if (route.view === 'planning-sessions' && route.planningSessionSlug) return `${base}/${encodeURIComponent(route.planningSessionSlug)}`;
  if (route.view === 'chat' && (route.projectSlug || route.threadId !== undefined)) {
    const params = new URLSearchParams();
    if (route.projectSlug) params.set('proyecto', route.projectSlug);
    if (route.threadId !== undefined) params.set('thread_id', String(route.threadId));
    return `${base}?${params.toString()}`;
  }
  return base;
}

export function isConversationRoute(route: PanelRoute): boolean {
  return route.view === 'conversations';
}

function fallback(): PanelRoute {
  return { view: 'dashboard' };
}

function positiveId(value: string): number | null {
  if (!/^[1-9]\d*$/.test(value)) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) ? id : null;
}

export function parsePanelPath(pathname: string): PanelRoute {
  const query = new URLSearchParams(pathname.split('?')[1]?.split('#')[0] ?? '');
  let segments: string[];
  try {
    segments = pathname.split(/[?#]/, 1)[0].split('/').filter(Boolean).map((segment) => decodeURIComponent(segment));
  } catch {
    return fallback();
  }
  if (segments[0] !== 'panel' || segments[1] !== 'app' || segments.length > 4) return fallback();
  if (segments.length === 2) return fallback();

  const view = segments[2] as PanelView;
  if (!panelViews.has(view)) return fallback();
  if (segments.length === 3) {
    if (view === 'cases') return { view: 'conversations', conversationTab: 'case' };
    if (view === 'conversations') {
      const tab = query.get('tab');
      return { view, conversationTab: tab && ['all', 'human', 'emergency', 'case', 'closed'].includes(tab) ? tab as PanelRoute['conversationTab'] : 'all' };
    }
    if (view === 'chat') {
      const projectSlug = query.get('proyecto') || undefined;
      const threadId = query.get('thread_id') ? positiveId(query.get('thread_id')!) : null;
      return { view, ...(projectSlug ? { projectSlug } : {}), ...(threadId ? { threadId } : {}) };
    }
    return { view };
  }
  if (segments.length !== 4) return fallback();

  const id = positiveId(segments[3]);
  if (view === 'projects') return { view, projectSlug: segments[3] };
  if (view === 'planning-sessions') return { view, planningSessionSlug: segments[3] };
  if (id === null || !['clients', 'users', 'conversations', 'automation-rules', 'kb', 'agenda'].includes(view)) return fallback();
  if (view === 'automation-rules') return { view, automationRuleId: id };
  if (view === 'kb') return { view, kbDocId: id };
  if (view === 'agenda') return { view, appointmentId: id };
  if (view === 'clients') return { view, clientId: id };
  if (view === 'users') return { view, userId: id };
  return { view, conversationId: id };
}
