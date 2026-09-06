import { describe, expect, it } from 'vitest';
import {
  PANEL_BASE_PATH,
  PANEL_ROUTES,
  parsePanelPath,
  pathForRoute,
  pathForView,
} from './panelRoutes';

describe('panel routes', () => {
  it('maps every top-level view to a clean panel path', () => {
    expect(PANEL_ROUTES).toEqual({
      dashboard: '/panel/app/',
      clients: '/panel/app/clients',
      conversations: '/panel/app/conversations',
      cases: '/panel/app/cases',
      notifications: '/panel/app/notifications',
      push: '/panel/app/push',
      chat: '/panel/app/chat',
      kb: '/panel/app/kb',
      settings: '/panel/app/settings',
      agenda: '/panel/app/agenda',
    });

    expect(pathForView('clients')).toBe('/panel/app/clients');
    expect(pathForView('dashboard')).toBe(PANEL_BASE_PATH);
    expect(parsePanelPath('/panel/app/agenda')).toEqual({ view: 'agenda' });
  });

  it('builds and parses positive client and conversation drill-down IDs', () => {
    expect(pathForRoute({ view: 'clients', clientId: 42 })).toBe('/panel/app/clients/42');
    expect(pathForRoute({ view: 'conversations', conversationId: 7 })).toBe('/panel/app/conversations/7');
    expect(parsePanelPath('/panel/app/clients/42')).toEqual({ view: 'clients', clientId: 42 });
    expect(parsePanelPath('/panel/app/conversations/7')).toEqual({ view: 'conversations', conversationId: 7 });
  });

  it('normalizes valid paths and safely falls back for invalid paths or IDs', () => {
    expect(parsePanelPath('/panel/app/clients/42/')).toEqual({ view: 'clients', clientId: 42 });
    expect(parsePanelPath('/panel/app//conversations')).toEqual({ view: 'conversations' });
    expect(parsePanelPath('/panel/app/clients/0')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/other/app/clients')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/panel/app/unknown?view=settings#ignored')).toEqual({ view: 'dashboard' });
  });

  it('falls back safely from malformed agenda paths', () => {
    expect(parsePanelPath('/panel/app/agenda/1')).toEqual({ view: 'dashboard' });
    expect(parsePanelPath('/panel/app/%E0%A4%A')).toEqual({ view: 'dashboard' });
  });
});
