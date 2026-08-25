import { useState } from 'react';
import type { User } from '../../types';
import type { PanelView } from './PanelShell';
import { PanelShell } from './PanelShell';

/** Top-level SPA views, switched via AppShell state (D7 — no router; `ponytail:`
 *  no URL shareability, upgrade path = react-router hash router when desired).
 *  Client ficha and conversation thread are drill-downs rendered from list
 *  views, not top-level nav, so they do not appear here. */
export type View = PanelView;

/** Label vocabulary for the placeholder page heading, mirroring the nav labels
 *  owned by PanelShell (which keeps the full NAVIGATION map private). */
const VIEW_LABELS: Record<PanelView, string> = {
  dashboard: 'Panel',
  clients: 'Clientes',
  conversations: 'Conversaciones',
  cases: 'Casos',
  kb: 'Base de conocimientos',
  settings: 'Configuración',
};

export interface AppShellProps {
  user: User;
}

/** Application shell: PanelShell frame (role-gated nav + view switch, B6/T6.4).
 *  PanelShell owns the shell chrome and nav; AppShell owns the active view
 *  state and the placeholder page. Domain views land in B11-B13; until then
 *  the active view renders a placeholder. */
export function AppShell({ user }: AppShellProps) {
  const [view, setView] = useState<PanelView>('dashboard');

  return (
    <PanelShell user={user} currentView={view} onNavigate={setView}>
      <main>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
          Vista {VIEW_LABELS[view]} disponible en un batch posterior.
        </p>
      </main>
    </PanelShell>
  );
}
