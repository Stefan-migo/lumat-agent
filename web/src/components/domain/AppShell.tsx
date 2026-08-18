import { useState } from 'react';
import type { User } from '../../types';

/** Top-level SPA views, switched via AppShell state (D7 — no router; `ponytail:`
 *  no URL shareability, upgrade path = react-router hash router when desired).
 *  Client ficha and conversation thread are drill-downs rendered from list
 *  views, not top-level nav, so they do not appear here. */
export type View = 'dashboard' | 'clients' | 'conversations' | 'cases' | 'kb' | 'settings';

interface NavEntry {
  label: string;
  adminOnly?: boolean;
}

const NAV: Record<View, NavEntry> = {
  dashboard: { label: 'Panel' },
  clients: { label: 'Clientes' },
  conversations: { label: 'Conversaciones' },
  cases: { label: 'Casos' },
  kb: { label: 'Base de conocimientos', adminOnly: true },
  settings: { label: 'Configuración', adminOnly: true },
};

export interface AppShellProps {
  user: User;
}

/** Application shell: role-gated nav + view switch (B6/T6.4). Domain views
 *  land in B11-B13; until then the active view renders a placeholder. */
export function AppShell({ user }: AppShellProps) {
  const [view, setView] = useState<View>('dashboard');
  const isAdmin = user.role === 'admin';

  const navItems = (Object.keys(NAV) as View[]).filter(
    (key) => NAV[key].adminOnly === undefined || isAdmin,
  );

  return (
    <div className="app-shell" style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        className="app-shell__nav"
        style={{
          width: 'calc(var(--space-8) * 6)',
          padding: 'var(--space-4)',
          background: 'var(--surface)',
          borderRight: '1px solid var(--border)',
        }}
      >
        <h1 className="app-shell__title" style={{ fontSize: 'var(--text-lg)', color: 'var(--text)' }}>
          Lumat Panel
        </h1>
        <nav aria-label="Vistas del panel">
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--space-1)' }}>
            {navItems.map((key) => (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => setView(key)}
                  aria-current={view === key ? 'page' : undefined}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: 'var(--space-2)',
                    background: view === key ? 'var(--primary-100)' : 'transparent',
                    color: 'var(--text)',
                    border: '1px solid transparent',
                    borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: 'var(--text-sm)',
                    cursor: 'pointer',
                  }}
                >
                  {NAV[key].label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <p className="app-shell__user" style={{ marginTop: 'var(--space-6)', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
          <span data-testid="app-shell-username">{user.username}</span> ·{' '}
          <span data-testid="app-shell-role">{user.role}</span>
        </p>
      </aside>

      <main className="app-shell__content" style={{ flex: 1, padding: 'var(--space-4)' }}>
        <h2 style={{ color: 'var(--text)' }}>
          {NAV[view].label}
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
          Vista {NAV[view].label} disponible en un batch posterior.
        </p>
      </main>
    </div>
  );
}
