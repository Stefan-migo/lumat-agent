import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppShell } from './AppShell';
import type { User } from '../../types';

const admin: User = { username: 'ana', role: 'admin' };
const operador: User = { username: 'vero', role: 'operador' };

/** Desktop sidebar landmark. In jsdom the `@media (min-width: 64rem)` rule is
 *  not applied, so the sidebar keeps its base `display: none` and role queries
 *  exclude it; text/attribute queries inside it still work. */
function sidebar(container: HTMLElement) {
  return within(container.querySelector('.panel-shell__sidebar') as HTMLElement);
}

describe('AppShell (T6.4)', () => {
  it('shows the authenticated user (username + role) and the app name', () => {
    const { container } = render(<AppShell user={admin} />);
    expect(sidebar(container).getByText('Lumat')).toBeInTheDocument();
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
    expect(screen.getByRole('heading', { name: 'Panel', level: 1 })).toBeInTheDocument();

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
});

describe('AppShell — desktop sidebar collapse (icon-only ⇄ full nav)', () => {
  /** Nav button lookup by aria-label; the sidebar keeps its base
   *  `display: none` in jsdom (no ≥64rem media query), so role queries
   *  exclude it — attribute queries only, same as the `sidebar()` helper. */
  const navButtonByLabel = (container: HTMLElement, label: string) =>
    Array.from(
      container.querySelectorAll<HTMLButtonElement>('.panel-shell__sidebar .panel-shell__navigation-button'),
    ).find((button) => button.getAttribute('aria-label') === label);

  /** Collapse toggle: icon-only button (no visible label); find it by class
   *  since role queries exclude the `display: none` sidebar in jsdom. */
  const collapseButton = (container: HTMLElement) =>
    container.querySelector<HTMLButtonElement>('.panel-shell__collapse-button')!;

  it('toggles aria-expanded, hides labels and keeps icon-only buttons named via aria-label', async () => {
    const user = userEvent.setup();
    const { container } = render(<AppShell user={admin} />);
    const s = sidebar(container);

    // Expanded by default: full labels; the toggle is icon-only, named via aria-label.
    const toggle = collapseButton(container);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveAttribute('aria-label', 'Colapsar menú');
    expect(s.getByText('Clientes')).toBeInTheDocument();
    expect(s.getByText('Conversaciones')).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(toggle).toHaveAttribute('aria-label', 'Expandir menú');
    // Labels are gone, but the icon-only buttons keep an accessible name.
    expect(s.queryByText('Clientes')).not.toBeInTheDocument();
    expect(s.queryByText('Conversaciones')).not.toBeInTheDocument();
    expect(navButtonByLabel(container, 'Clientes')).toHaveAttribute('aria-label', 'Clientes');
    expect(navButtonByLabel(container, 'Clientes')).toHaveAttribute('title', 'Clientes');
    // The compact brand mark keeps its label; the user block its tooltip text.
    expect(s.getByText('L')).toBeInTheDocument();
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
});
