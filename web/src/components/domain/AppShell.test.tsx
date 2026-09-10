import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppShell } from './AppShell';
import type { User } from '../../types';

const admin: User = { username: 'ana', role: 'admin' };
const operador: User = { username: 'vero', role: 'operador' };

beforeEach(() => {
  window.history.replaceState({}, '', '/panel/app/');
});

afterEach(() => {
  window.history.replaceState({}, '', '/panel/app/');
});

/** Desktop sidebar landmark. In jsdom the `@media (min-width: 64rem)` rule is
 *  not applied, so the sidebar keeps its base `display: none` and role queries
 *  exclude it; text/attribute queries inside it still work. */
function sidebar(container: HTMLElement) {
  return within(container.querySelector('.panel-shell__sidebar') as HTMLElement);
}

describe('AppShell (T6.4)', () => {
  it('shows the authenticated user (username + role) and the app name', () => {
    const { container } = render(<AppShell user={admin} />);
    expect(sidebar(container).getByLabelText('Lumat, panel operativo').querySelector('.panel-shell__brand-image')).toHaveAttribute('src', '/panel/app/brand/lumat-logo.png');
    expect(sidebar(container).getByText('ana')).toBeInTheDocument();
    expect(sidebar(container).getByText('Administrador')).toBeInTheDocument();
  });

  it('renders admin sections for an admin, but hides them for an operador', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<AppShell user={admin} />);
    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    const adminDrawer = screen.getByRole('dialog', { name: 'Navegación' });
    expect(within(adminDrawer).getByRole('button', { name: /base de conocimientos/i })).toBeInTheDocument();
     expect(within(adminDrawer).getByRole('button', { name: /configuraci[oó]n/i })).toBeInTheDocument();
     expect(within(adminDrawer).getByRole('button', { name: 'Usuarios' })).toBeInTheDocument();
    unmount();

    render(<AppShell user={operador} />);
    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    const operadorDrawer = screen.getByRole('dialog', { name: 'Navegación' });
    expect(
      within(operadorDrawer).queryByRole('button', { name: /base de conocimientos/i }),
    ).not.toBeInTheDocument();
    expect(within(operadorDrawer).queryByRole('button', { name: /configuraci[oó]n/i })).not.toBeInTheDocument();
    expect(within(operadorDrawer).queryByRole('button', { name: 'Asistente Lumat' })).not.toBeInTheDocument();
    expect(within(operadorDrawer).queryByRole('button', { name: 'Automatizaciones' })).not.toBeInTheDocument();
  });

   it('exposes exactly nine approved destinations and keeps legacy routes out of navigation', async () => {
    const user = userEvent.setup();
    render(<AppShell user={admin} />);
    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    const drawer = screen.getByRole('dialog', { name: 'Navegación' });
     expect(drawer.querySelectorAll('.panel-shell__navigation-button')).toHaveLength(9);
    for (const label of [
      'Panel unificado', 'Asistente Lumat', 'Conversaciones', 'Clientes',
       'Agenda', 'Base de Conocimientos', 'Automatizaciones', 'Configuración', 'Usuarios',
    ]) {
      expect(within(drawer).getByRole('button', { name: label })).toBeInTheDocument();
    }
    for (const label of ['Notificaciones', 'Notificaciones push', 'Casos', 'Dashboard avanzado']) {
      expect(within(drawer).queryByRole('button', { name: label })).not.toBeInTheDocument();
    }
  });

  it('keeps the Conversations/Cases segment internal to the destination', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ cases: [], users: [] }), { status: 200 }),
    );
    render(<AppShell user={operador} />);
    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Conversaciones' }));
    const conversationsSegment = screen.getAllByRole('button', { name: /^Conversaciones$/ })
      .find((button) => button.hasAttribute('aria-pressed'))!;
    const casesSegment = screen.getByRole('button', { name: /^Casos$/ });
    expect(conversationsSegment).toHaveAttribute('aria-pressed', 'true');
    await user.click(casesSegment);
    expect(window.location.pathname).toBe('/panel/app/conversations');
    expect(window.location.search).toBe('');
    expect(casesSegment).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('heading', { name: 'Conversaciones' })).toBeInTheDocument();
    fetchMock.mockRestore();
  });

  it('switches views on nav click and marks the active view', async () => {
    const user = userEvent.setup();
    const { container } = render(<AppShell user={operador} />);
    expect(await screen.findByRole('heading', { name: 'Panel', level: 1 })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    const drawer = screen.getByRole('dialog', { name: 'Navegación' });
    const panelBtn = within(drawer).getByRole('button', { name: 'Panel unificado' });
    expect(panelBtn).toHaveAttribute('aria-current', 'page');
    const clientesBtn = within(drawer).getByRole('button', { name: 'Clientes' });
    expect(clientesBtn).not.toHaveAttribute('aria-current', 'page');

    await user.click(clientesBtn);

    // Drawer closes on navigate; the desktop sidebar nav marks the active view.
    expect(sidebar(container).getByText('Panel unificado').closest('button')).not.toHaveAttribute('aria-current', 'page');
    expect(sidebar(container).getByText('Clientes').closest('button')).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('heading', { name: 'Clientes', level: 1 })).toBeInTheDocument();
  });

  it('renders the real dashboard page for the Panel view', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ contacts: 12, motivos: [['consulta', 3]], derived: 2, visit_requests: 1, window_days: 7, window_start: '2026-08-18' }), { status: 200 }),
    );

    render(<AppShell user={operador} />);
    expect(await screen.findByText('Contactos')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.queryByText('disponible en un batch posterior')).not.toBeInTheDocument();

    fetchMock.mockRestore();
  });

  it('renders live data pages for every navigation view', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const path = String(input);
      const bodies: Record<string, unknown> = {
        '/panel/api/clients': { clients: [{ id: 7, name: 'Cliente vivo', phone_e164: '+56911111111', state: 'activo', consent_status: true, created_at: '2026-08-25' }] },
        '/panel/api/cases': { cases: [], users: [] },
        '/panel/api/conversations': { conversations: [{ id: 9, customer_id: 7, wa_phone: '+56911111111', state: 'active', summary: 'Conversación viva', last_message_at: '2026-08-25', created_at: '2026-08-25' }] },
        '/panel/api/kb': { docs: [] },
        '/panel/api/settings': { scope_rules: {}, keywords: [], tone: 'Claro', conversation_limit: 1, daily_limit: 2, meta_cost: 3, snapshot: null },
      };
      const body = bodies[new URL(path, 'http://localhost').pathname] ?? { contacts: 0, motivos: [], derived: 0, visit_requests: 0, window_days: 7, window_start: '2026-08-25' };
      return new Response(JSON.stringify(body), { status: 200 });
    });
    const user = userEvent.setup();
    const { container } = render(<AppShell user={admin} />);
    const drawer = async () => {
      await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
      return screen.getByRole('dialog', { name: 'Navegación' });
    };

    await user.click(within(await drawer()).getByRole('button', { name: 'Clientes' }));
    expect(await screen.findByText('Cliente vivo')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Conversaciones' }));
    await user.click(screen.getByRole('button', { name: /^Casos$/ }));
    expect(await screen.findByText('Conversación viva')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Conversaciones' }));
    expect(await screen.findByText('Conversación viva')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Base de Conocimientos' }));
    expect(await screen.findByText('No hay documentos')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Configuración' }));
    expect(await screen.findByDisplayValue('Claro')).toBeInTheDocument();
    expect(container.querySelector('.panel-shell__content')).not.toHaveTextContent('Vista disponible en un batch posterior.');
    fetchMock.mockRestore();
  });

  it('deep-links to Agenda and exposes it to operadores with an active nav state', async () => {
    window.history.replaceState({}, '', '/panel/app/agenda');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ appointments: [] }), { status: 200 }));

    const { container } = render(<AppShell user={operador} />);
    expect(await screen.findByRole('heading', { name: 'Agenda', level: 1 })).toBeInTheDocument();
    expect(sidebar(container).getByText('Agenda').closest('button')).toHaveAttribute('aria-current', 'page');

    await userEvent.setup().click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    expect(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Agenda' })).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it('deep-links to AdvancedDashboard without exposing a visible navigation item', async () => {
    window.history.replaceState({}, '', '/panel/app/advanced-dashboard');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const path = new URL(String(input), 'http://localhost').pathname;
      if (path.includes('/dashboard/')) return new Response(JSON.stringify({ period: { start: '2026-08-01', end: '2026-08-04', timezone: 'UTC' }, metrics: { contacts: 2, cases: 1, appointments: 0, notification_health: {}, automation_outcomes: {} }, trend: [{ start: '2026-08-01', count: 1 }], drilldown: [] }), { status: 200 });
      return new Response(JSON.stringify({ contacts: 0, motivos: [], derived: 0, visit_requests: 0, window_days: 7, window_start: '2026-08-25' }), { status: 200 });
    });

    const { container } = render(<AppShell user={operador} />);
    expect(await screen.findByText('Indicadores operacionales')).toBeInTheDocument();
    expect(sidebar(container).queryByText('Dashboard avanzado')).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    expect(within(screen.getByRole('dialog', { name: 'Navegación' })).queryByRole('button', { name: 'Dashboard avanzado' })).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it('redirects the bookmarked cases path to the unified conversations section', async () => {
    window.history.replaceState({}, '', '/panel/app/cases');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 20, counts: { all: 0, human: 0, emergency: 0, case: 0, closed: 0 } }), { status: 200 }));
    render(<AppShell user={operador} />);

    expect(window.location.pathname).toBe('/panel/app/conversations');
    expect(screen.getByRole('button', { name: /^Casos$/ })).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('No hay conversaciones')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Casos' })).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it('deep-links to automation rules and renders a forbidden state for operadores', async () => {
    window.history.replaceState({}, '', '/panel/app/automation-rules');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'Forbidden' }), { status: 403 }));

    const { container } = render(<AppShell user={operador} />);
    expect(await screen.findByText(/no tienes permiso|acceso denegado|forbidden/i)).toBeInTheDocument();
    expect(sidebar(container).queryByText('Automatizaciones')).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    const drawer = screen.getByRole('dialog', { name: 'Navegación' });
    expect(within(drawer).queryByRole('button', { name: 'Automatizaciones' })).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it('uses browser back after opening an automation rule detail route', async () => {
    window.history.replaceState({}, '', '/panel/app/automation-rules');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      const body = { rules: [{ id: 12, name: 'Aviso', event_type: 'case.created', conditions: {}, channel: 'whatsapp', template_event: 'case.created', cooldown_seconds: 0, enabled: true, created_by: 'ana', created_at: null, updated_at: null }] };
      return new Response(JSON.stringify(body), { status: 200 });
    });
    render(<AppShell user={admin} />);
    expect(await screen.findByRole('heading', { name: 'Reglas de automatización', level: 1 })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('link', { name: 'Aviso' }));
    expect(window.location.pathname).toBe('/panel/app/automation-rules/12');
    window.history.back();
    window.dispatchEvent(new PopStateEvent('popstate'));
    await waitFor(() => expect(window.location.pathname).toBe('/panel/app/automation-rules'));
    vi.restoreAllMocks();
  });

  it('keeps client and conversation drill-downs inside D7 state navigation', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const path = new URL(String(input), 'http://localhost').pathname;
      const bodies: Record<string, unknown> = {
        '/panel/api/clients': { clients: [{ id: 7, name: 'Cliente vivo', phone_e164: '+56911111111', state: 'activo', consent_status: true, created_at: '2026-08-25' }] },
        '/panel/api/clients/7': { customer: { id: 7, name: 'Cliente vivo', phone_e164: '+56911111111', state: 'activo', consent_status: true, created_at: '2026-08-25' }, memo: '', notes: [], history: { conversations: [], cases: [], messages: [] } },
        '/panel/api/clients/7/memories': { memories: [] },
        '/panel/api/conversations': { conversations: [{ id: 9, customer_id: 7, wa_phone: '+56911111111', state: 'active', summary: 'Conversación viva', last_message_at: '2026-08-25', created_at: '2026-08-25' }] },
        '/panel/api/conversations/9': { conversation: { id: 9, customer_id: 7, state: 'active', created_at: '2026-08-25', summary: 'Conversación viva' }, messages: [{ id: 1, direction: 'inbound', msg_type: 'text', text: 'Hola', created_at: '2026-08-25' }] },
      };
      return new Response(JSON.stringify(bodies[path] ?? { contacts: 0, motivos: [], derived: 0, visit_requests: 0, window_days: 7, window_start: '2026-08-25' }), { status: 200 });
    });
    const user = userEvent.setup();
    render(<AppShell user={admin} />);
    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Clientes' }));
    await user.click(await screen.findByRole('link', { name: 'Cliente vivo' }));
    expect(await screen.findByText('Ficha: Cliente vivo')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Conversaciones' }));
    await user.click(await screen.findByRole('button', { name: 'Abrir conversación #9' }));
    expect(await screen.findByText('# 9')).toBeInTheDocument();
    fetchMock.mockRestore();
  });
});

describe('AppShell — desktop sidebar collapse (icon-only ⇄ full nav)', () => {
  /** Nav button lookup by aria-label; the sidebar keeps its base
   *  `display: none` in jsdom (no ≥64rem media query), so role queries
   *  exclude it — attribute queries only, same as the `sidebar()` helper. */
  const navButtonByLabel = (container: HTMLElement, label: string) =>
    Array.from(
      container.querySelectorAll<HTMLButtonElement>('.panel-shell__sidebar .panel-shell__navigation-button'),
    ).find((button) => button.getAttribute('aria-label') === label);

  /** Desktop collapse toggle lives beside the content heading. */
  const collapseButton = (container: HTMLElement) =>
    container.querySelector<HTMLButtonElement>('.panel-shell__collapse-button')!;

  it('toggles aria-expanded, hides labels and keeps icon-only buttons named via aria-label', async () => {
    const user = userEvent.setup();
    const { container } = render(<AppShell user={admin} />);
    const s = sidebar(container);

    // Expanded by default: full labels and a named panel control.
    const toggle = collapseButton(container);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveAttribute('aria-label', 'Colapsar panel lateral');
    expect(toggle.querySelector('svg')).toHaveAttribute('stroke', 'currentColor');
    expect(s.getByText('Clientes')).toBeInTheDocument();
    expect(s.getByText('Conversaciones')).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(toggle).toHaveAttribute('aria-label', 'Expandir panel lateral');
    // Labels are gone, but the icon-only buttons keep an accessible name.
    expect(s.queryByText('Clientes')).not.toBeInTheDocument();
    expect(s.queryByText('Conversaciones')).not.toBeInTheDocument();
    expect(navButtonByLabel(container, 'Clientes')).toHaveAttribute('aria-label', 'Clientes');
    expect(navButtonByLabel(container, 'Clientes')).toHaveAttribute('title', 'Clientes');
    // The compact brand mark is decorative; the Brand container keeps its accessible name.
    expect(s.getByLabelText('Lumat, panel operativo')).toBeInTheDocument();
    expect(s.getByLabelText('ana — Administrador')).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(s.getByText('Clientes')).toBeInTheDocument();
  });

  it('keeps nav reachable and the active state marked while collapsed', async () => {
    const user = userEvent.setup();
    const { container } = render(<AppShell user={operador} />);
    await user.click(collapseButton(container));

    const panelBtn = navButtonByLabel(container, 'Panel unificado');
    expect(panelBtn).toHaveAttribute('aria-current', 'page');
    const clientesBtn = navButtonByLabel(container, 'Clientes')!;
    expect(clientesBtn).not.toHaveAttribute('aria-current', 'page');

    await user.click(clientesBtn);
    expect(screen.getByRole('heading', { name: 'Clientes', level: 1 })).toBeInTheDocument();
    expect(panelBtn).not.toHaveAttribute('aria-current', 'page');
    expect(clientesBtn).toHaveAttribute('aria-current', 'page');
  });

  it('keeps long navigation labels available instead of clipping them', () => {
    const { container } = render(<AppShell user={admin} />);
    const label = within(container.querySelector('.panel-shell__sidebar') as HTMLElement).getByText('Base de Conocimientos');
    expect(label).toHaveTextContent('Base de Conocimientos');
  });
});

describe('AppShell — native History API routing', () => {
  it('derives the initial view from the URL and updates clean paths on navigation', async () => {
    window.history.replaceState({}, '', '/panel/app/clients');
    const user = userEvent.setup();
    const { container } = render(<AppShell user={operador} />);

    expect(screen.getByRole('heading', { name: 'Clientes', level: 1 })).toBeInTheDocument();
    expect(sidebar(container).getByText('Clientes').closest('button')).toHaveAttribute('aria-current', 'page');

    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Conversaciones' }));
    expect(window.location.pathname).toBe('/panel/app/conversations');
    expect(screen.getByRole('heading', { name: 'Conversaciones', level: 1 })).toBeInTheDocument();
  });

  it('supports popstate navigation and falls back unknown paths without leaking listeners', async () => {
    const user = userEvent.setup();
    const addSpy = vi.spyOn(window, 'addEventListener');
    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<AppShell user={operador} />);

    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Clientes' }));
    window.history.pushState({}, '', '/panel/app/conversations');
    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(await screen.findByRole('heading', { name: 'Conversaciones', level: 1 })).toBeInTheDocument();

    window.history.pushState({}, '', '/panel/app/not-a-view');
    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(window.location.pathname).toBe('/panel/app/');
    expect(await screen.findByRole('heading', { name: 'Panel', level: 1 })).toBeInTheDocument();

    unmount();
    expect(addSpy.mock.calls.some(([type]) => type === 'popstate')).toBe(true);
    expect(removeSpy.mock.calls.some(([type]) => type === 'popstate')).toBe(true);
    addSpy.mockRestore();
    removeSpy.mockRestore();
  });
});

describe('AppShell — agent shell grammar', () => {
  it('opens the notification popover and navigates to the full center', async () => {
    const user = userEvent.setup();
    const logout = vi.fn();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).includes('/notifications')
      ? new Response(JSON.stringify({ notifications: [{ id: 1, title: 'Aviso', content: 'Caso', source: 'case', channel: 'email', status: 'sent', read_at: null, created_at: null }] }), { status: 200 })
      : new Response(JSON.stringify({ contacts: 0, motivos: [], derived: 0, visit_requests: 0, window_days: 7, window_start: '2026-08-25' }), { status: 200 }));
    render(<AppShell user={admin} onLogout={logout} />);

    const bell = await screen.findByRole('button', { name: 'Notificaciones (1 sin leer)' });

    await user.click(bell);
    const popover = screen.getByRole('dialog', { name: 'Notificaciones' });
    expect(popover).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /abrir menú de usuario/i })).not.toBeInTheDocument();
    await user.click(within(popover).getByRole('button', { name: 'Ver todas las notificaciones' }));
    expect(window.location.pathname).toBe('/panel/app/notifications');
    expect(await screen.findByRole('heading', { name: 'Notificaciones' })).toBeInTheDocument();
    expect(logout).not.toHaveBeenCalled();
  });

  it('shows a truthful notification loading and error state without polling', async () => {
    const requests: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      requests.push(String(input));
      if (String(input).includes('/notifications')) return new Response('failure', { status: 500 });
      return new Response(JSON.stringify({ contacts: 0, motivos: [], derived: 0, visit_requests: 0, window_days: 7, window_start: '2026-08-25' }), { status: 200 });
    });
    render(<AppShell user={admin} />);

    expect(screen.getByRole('button', { name: /cargando notificaciones/i })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /notificaciones no disponibles/i })).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(requests.filter((path) => path.includes('/notifications'))).toHaveLength(1);
  });

  it('renders the responsive footer navigation with an admin-only raised chat action', () => {
    const { container } = render(<AppShell user={admin} />);
    const footer = within(container.querySelector('.panel-shell__footer-nav') as HTMLElement);
    expect(footer.getByRole('button', { name: 'Notificaciones' })).toBeInTheDocument();
    expect(footer.getByRole('button', { name: 'Panel' })).toHaveAttribute('aria-current', 'page');
    expect(footer.getByRole('button', { name: 'Agente Lumat' })).toHaveClass('panel-shell__footer-nav--primary');
    expect(footer.getAllByRole('button')).toHaveLength(5);
  });

  it('renders the optional inspector without active-thread chrome', () => {
    render(
      <AppShell
        user={admin}
        inspector={<div>Contexto del cliente</div>}
      />,
    );

    expect(screen.getByRole('complementary', { name: 'Inspector operacional' })).toHaveTextContent('Contexto del cliente');
    expect(screen.queryByRole('region', { name: 'Conversaciones activas' })).not.toBeInTheDocument();
  });
});
