import type { PanelView } from './PanelShell';

export type PanelRoute = {
  view: PanelView;
  clientId?: number;
  conversationId?: number;
  automationRuleId?: number;
};

export const PANEL_BASE_PATH = '/panel/app/';

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
  return PANEL_ROUTES[view as keyof typeof PANEL_ROUTES] ?? COMPATIBILITY_ROUTES[view] ?? PANEL_BASE_PATH;
}

export function pathForRoute(route: PanelRoute): string {
  const base = pathForView(route.view);
  if (route.view === 'clients' && route.clientId !== undefined && Number.isSafeInteger(route.clientId) && route.clientId > 0) {
    return `${base}/${route.clientId}`;
  }
  if (route.view === 'conversations' && route.conversationId !== undefined && Number.isSafeInteger(route.conversationId) && route.conversationId > 0) {
    return `${base}/${route.conversationId}`;
  }
  if (route.view === 'automation-rules' && route.automationRuleId !== undefined && Number.isSafeInteger(route.automationRuleId) && route.automationRuleId > 0) {
    return `${base}/${route.automationRuleId}`;
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
  if (segments.length === 3) return { view };
  if (segments.length !== 4) return fallback();

  const id = positiveId(segments[3]);
  if (id === null || !['clients', 'conversations', 'automation-rules'].includes(view)) return fallback();
  if (view === 'automation-rules') return { view, automationRuleId: id };
  return view === 'clients' ? { view, clientId: id } : { view, conversationId: id };
}
