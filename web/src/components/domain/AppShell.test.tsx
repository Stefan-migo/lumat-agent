import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
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
    await user.click(screen.getByRole('button', { name: 'Menú' }));
    const adminDrawer = screen.getByRole('dialog', { name: 'Navegación' });
    expect(within(adminDrawer).getByRole('button', { name: /base de conocimientos/i })).toBeInTheDocument();
    expect(within(adminDrawer).getByRole('button', { name: /configuraci[oó]n/i })).toBeInTheDocument();
    unmount();

    render(<AppShell user={operador} />);
    await user.click(screen.getByRole('button', { name: 'Menú' }));
    const operadorDrawer = screen.getByRole('dialog', { name: 'Navegación' });
    expect(
      within(operadorDrawer).queryByRole('button', { name: /base de conocimientos/i }),
    ).not.toBeInTheDocument();
    expect(within(operadorDrawer).queryByRole('button', { name: /configuraci[oó]n/i })).not.toBeInTheDocument();
  });

  it('switches views on nav click and marks the active view', async () => {
    const user = userEvent.setup();
    const { container } = render(<AppShell user={operador} />);
    expect(await screen.findByRole('heading', { name: 'Panel', level: 1 })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Menú' }));
    const drawer = screen.getByRole('dialog', { name: 'Navegación' });
    const panelBtn = within(drawer).getByRole('button', { name: 'Panel' });
    expect(panelBtn).toHaveAttribute('aria-current', 'page');
    const clientesBtn = within(drawer).getByRole('button', { name: 'Clientes' });
    expect(clientesBtn).not.toHaveAttribute('aria-current', 'page');

    await user.click(clientesBtn);

    // Drawer closes on navigate; the desktop sidebar nav marks the active view.
    expect(sidebar(container).getByText('Panel').closest('button')).not.toHaveAttribute('aria-current', 'page');
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
      await user.click(screen.getByRole('button', { name: 'Menú' }));
      return screen.getByRole('dialog', { name: 'Navegación' });
    };

    await user.click(within(await drawer()).getByRole('button', { name: 'Clientes' }));
    expect(await screen.findByText('Cliente vivo')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Casos' }));
    expect(await screen.findByText('No hay registros')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Conversaciones' }));
    expect(await screen.findByText('Conversación viva')).toBeInTheDocument();
    await user.click(within(await drawer()).getByRole('button', { name: 'Base de conocimientos' }));
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

    await userEvent.setup().click(screen.getByRole('button', { name: 'Menú' }));
    expect(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Agenda' })).toBeInTheDocument();
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
    await user.click(screen.getByRole('button', { name: 'Menú' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Clientes' }));
    await user.click(await screen.findByRole('link', { name: 'Cliente vivo' }));
    expect(await screen.findByText('Ficha: Cliente vivo')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Menú' }));
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

    const panelBtn = navButtonByLabel(container, 'Panel');
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
    const label = within(container.querySelector('.panel-shell__sidebar') as HTMLElement).getByText('Base de conocimientos');
    expect(label).toHaveTextContent('Base de conocimientos');
  });
});

describe('AppShell — native History API routing', () => {
  it('derives the initial view from the URL and updates clean paths on navigation', async () => {
    window.history.replaceState({}, '', '/panel/app/clients');
    const user = userEvent.setup();
    const { container } = render(<AppShell user={operador} />);

    expect(screen.getByRole('heading', { name: 'Clientes', level: 1 })).toBeInTheDocument();
    expect(sidebar(container).getByText('Clientes').closest('button')).toHaveAttribute('aria-current', 'page');

    await user.click(screen.getByRole('button', { name: 'Menú' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: 'Conversaciones' }));
    expect(window.location.pathname).toBe('/panel/app/conversations');
    expect(screen.getByRole('heading', { name: 'Conversaciones', level: 1 })).toBeInTheDocument();
  });

  it('supports popstate navigation and falls back unknown paths without leaking listeners', async () => {
    const user = userEvent.setup();
    const addSpy = vi.spyOn(window, 'addEventListener');
    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<AppShell user={operador} />);

    await user.click(screen.getByRole('button', { name: 'Menú' }));
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
