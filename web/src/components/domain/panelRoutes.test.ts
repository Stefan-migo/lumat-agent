import { describe, expect, it } from 'vitest';
import {
  PANEL_BASE_PATH,
  PANEL_ROUTES,
  parsePanelPath,
  pathForRoute,
  pathForView,
  isDetailRoute,
} from './panelRoutes';

describe('panel routes', () => {
  it('identifies only routes with path-segment drill-downs as detail routes', () => {
    expect(isDetailRoute({ view: 'clients' })).toBe(false);
    expect(isDetailRoute({ view: 'clients', clientId: 42 })).toBe(true);
    expect(isDetailRoute({ view: 'conversations', conversationId: 7 })).toBe(true);
    expect(isDetailRoute({ view: 'automation-rules', automationRuleId: 12 })).toBe(true);
    expect(isDetailRoute({ view: 'kb', kbDocId: 3 })).toBe(true);
    expect(isDetailRoute({ view: 'agenda', appointmentId: 9 })).toBe(true);
    expect(isDetailRoute({ view: 'projects', projectSlug: 'ops' })).toBe(true);
    expect(isDetailRoute({ view: 'planning-sessions', planningSessionSlug: 'review' })).toBe(true);
    expect(isDetailRoute({ view: 'chat', projectSlug: 'ops', threadId: 4 })).toBe(false);
  });

  it('maps every top-level view to a clean panel path', () => {
    expect(PANEL_ROUTES).toMatchObject({
      dashboard: '/panel/app/',
      clients: '/panel/app/clients',
      conversations: '/panel/app/conversations',
      chat: '/panel/app/chat',
      agenda: '/panel/app/agenda',
      kb: '/panel/app/kb',
      'automation-rules': '/panel/app/automation-rules',
       settings: '/panel/app/settings',
        users: '/panel/app/users',
        projects: '/panel/app/projects',
    });
    expect(Object.keys(PANEL_ROUTES)).toEqual([
        'dashboard', 'chat', 'conversations', 'clients', 'agenda', 'kb', 'automation-rules', 'settings', 'users', 'profile', 'projects', 'planning-sessions',
    ]);

    expect(pathForView('clients')).toBe('/panel/app/clients');
    expect(pathForView('dashboard')).toBe(PANEL_BASE_PATH);
    expect(parsePanelPath('/panel/app/agenda')).toEqual({ view: 'agenda' });
    expect(pathForView('users')).toBe('/panel/app/users');
    expect(parsePanelPath('/panel/app/users')).toEqual({ view: 'users' });
    expect(pathForView('profile')).toBe('/panel/app/profile');
    expect(parsePanelPath('/panel/app/profile')).toEqual({ view: 'profile' });
    expect(parsePanelPath('/panel/app/projects')).toEqual({ view: 'projects' });
    expect(pathForRoute({ view: 'cases' })).toBe('/panel/app/cases');
    expect(pathForRoute({ view: 'advanced-dashboard' })).toBe('/panel/app/advanced-dashboard');
    expect(parsePanelPath('/panel/app/advanced-dashboard')).toEqual({ view: 'advanced-dashboard' });
    expect(parsePanelPath('/panel/app/cases')).toEqual({ view: 'conversations', conversationTab: 'case' });
  });

  it('builds and parses positive client and conversation drill-down IDs', () => {
    expect(pathForRoute({ view: 'clients', clientId: 42 })).toBe('/panel/app/clients/42');
    expect(pathForRoute({ view: 'conversations', conversationId: 7 })).toBe('/panel/app/conversations/7');
    expect(parsePanelPath('/panel/app/clients/42')).toEqual({ view: 'clients', clientId: 42 });
    expect(parsePanelPath('/panel/app/conversations/7')).toEqual({ view: 'conversations', conversationId: 7 });
  });

  it('builds and parses user ficha routes', () => {
    expect(pathForRoute({ view: 'users', userId: 42 })).toBe('/panel/app/users/42');
    expect(parsePanelPath('/panel/app/users/42')).toEqual({ view: 'users', userId: 42 });
  });

  it('normalizes valid paths and safely falls back for invalid paths or IDs', () => {
    expect(parsePanelPath('/panel/app/clients/42/')).toEqual({ view: 'clients', clientId: 42 });
    expect(parsePanelPath('/panel/app//conversations')).toEqual({ view: 'conversations', conversationTab: 'all' });
    expect(parsePanelPath('/panel/app/clients/0')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/other/app/clients')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/panel/app/conversations?surface=cases')).toEqual({ view: 'conversations', conversationTab: 'all' });
    expect(parsePanelPath('/panel/app/unknown?view=settings#ignored')).toEqual({ view: 'dashboard' });
  });

  it('falls back safely from malformed agenda paths', () => {
    expect(parsePanelPath('/panel/app/agenda/1')).toEqual({ view: 'agenda', appointmentId: 1 });
    expect(parsePanelPath('/panel/app/%E0%A4%A')).toEqual({ view: 'dashboard' });
  });

  it('builds and parses positive appointment detail routes while preserving the register route', () => {
    expect(pathForRoute({ view: 'agenda', appointmentId: 7 })).toBe('/panel/app/agenda/7');
    expect(parsePanelPath('/panel/app/agenda/7')).toEqual({ view: 'agenda', appointmentId: 7 });
    expect(parsePanelPath('/panel/app/agenda')).toEqual({ view: 'agenda' });
    expect(pathForRoute({ view: 'agenda', appointmentId: 0 })).toBe('/panel/app/agenda');
    expect(pathForRoute({ view: 'agenda', appointmentId: 1.5 })).toBe('/panel/app/agenda');
    expect(parsePanelPath('/panel/app/agenda/0')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/panel/app/agenda/1.5')).toEqual({ view: 'dashboard' });
  });

  it('resolves bookmarked cases to the unified conversations route', () => {
    expect(pathForRoute({ view: 'conversations', conversationTab: 'case' })).toBe('/panel/app/cases');
    expect(pathForView('cases')).toBe('/panel/app/cases');
    expect(pathForRoute(parsePanelPath('/panel/app/cases'))).toBe('/panel/app/cases');
    expect(parsePanelPath('/panel/app/conversations')).toEqual({ view: 'conversations', conversationTab: 'all' });
  });

  it.each([
    ['all', '/panel/app/conversations'],
    ['human', '/panel/app/conversations?tab=human'],
    ['emergency', '/panel/app/conversations?tab=emergency'],
    ['case', '/panel/app/cases'],
    ['closed', '/panel/app/conversations?tab=closed'],
  ] as const)('round-trips queue tab %s', (tab, path) => {
    const route = { view: 'conversations', conversationTab: tab } as const;
    expect(pathForRoute(route)).toBe(path);
    expect(parsePanelPath(path)).toEqual(route);
  });

  it.each(['', 'unknown', 'HUMAN', '%ZZ'])('defaults malformed queue tab %s to all', (tab) => {
    expect(parsePanelPath(`/panel/app/conversations?tab=${tab}`)).toEqual({ view: 'conversations', conversationTab: 'all' });
  });

  it('builds and parses canonical automation rule list and detail routes', () => {
    expect(pathForView('automation-rules')).toBe('/panel/app/automation-rules');
    expect(pathForRoute({ view: 'automation-rules', automationRuleId: 12 })).toBe('/panel/app/automation-rules/12');
    expect(parsePanelPath('/panel/app/automation-rules')).toEqual({ view: 'automation-rules' });
    expect(parsePanelPath('/panel/app/automation-rules/12')).toEqual({ view: 'automation-rules', automationRuleId: 12 });
  });

  it('builds and parses planning session routes', () => {
    expect(parsePanelPath('/panel/app/planning-sessions')).toEqual({ view: 'planning-sessions' });
    expect(parsePanelPath('/panel/app/planning-sessions/budget-review-8')).toEqual({ view: 'planning-sessions', planningSessionSlug: 'budget-review-8' });
    expect(pathForRoute({ view: 'planning-sessions', planningSessionSlug: 'budget-review-8' })).toBe('/panel/app/planning-sessions/budget-review-8');
  });

  it('keeps project and thread chat deep links URL-addressable', () => {
    expect(pathForRoute({ view: 'chat', projectSlug: 'ops' })).toBe('/panel/app/chat?proyecto=ops');
    expect(parsePanelPath('/panel/app/chat?proyecto=ops')).toEqual({ view: 'chat', projectSlug: 'ops' });
    expect(pathForRoute({ view: 'chat', threadId: 4 })).toBe('/panel/app/chat?thread_id=4');
    expect(parsePanelPath('/panel/app/chat?thread_id=4')).toEqual({ view: 'chat', threadId: 4 });
  });

  it('falls back to dashboard for malformed automation rule IDs', () => {
    expect(parsePanelPath('/panel/app/automation-rules/0')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/panel/app/automation-rules/not-an-id')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/panel/app/automation-rules/1/extra')).toEqual({ view: 'dashboard' });
  });
});
