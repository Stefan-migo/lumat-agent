import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppShell } from './AppShell';
import type { User } from '../../types';

const admin: User = { username: 'ana', role: 'admin' };
const operador: User = { username: 'vero', role: 'operador' };

describe('AppShell (T6.4)', () => {
  it('shows the authenticated user (username + role) and the app name', () => {
    render(<AppShell user={admin} />);
    expect(screen.getByText('Lumat Panel')).toBeInTheDocument();
    expect(screen.getByText('ana')).toBeInTheDocument();
    expect(screen.getByText(/admin/i)).toBeInTheDocument();
  });

  it('renders admin sections for an admin, but hides them for an operador', () => {
    const { unmount } = render(<AppShell user={admin} />);
    expect(screen.getByRole('button', { name: /base de conocimientos/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /configuraci[oó]n/i })).toBeInTheDocument();
    unmount();

    render(<AppShell user={operador} />);
    expect(
      screen.queryByRole('button', { name: /base de conocimientos/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /configuraci[oó]n/i })).not.toBeInTheDocument();
  });

  it('switches views on nav click and marks the active view', async () => {
    const user = userEvent.setup();
    render(<AppShell user={operador} />);
    const dashboardBtn = screen.getByRole('button', { name: /panel|dashboard/i });
    expect(dashboardBtn).toHaveAttribute('aria-current', 'page');

    await user.click(screen.getByRole('button', { name: /clientes/i }));
    expect(screen.getByRole('button', { name: /clientes/i })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(dashboardBtn).not.toHaveAttribute('aria-current', 'page');
  });
});
