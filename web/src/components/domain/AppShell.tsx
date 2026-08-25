import { useState } from 'react';
import type { User } from '../../types';
import type { PanelView } from './PanelShell';
import { PanelShell } from './PanelShell';
import { Dashboard } from '../pages/Dashboard';
import { ClientesList } from '../pages/ClientesList';
import { ClientFicha } from '../pages/ClientFicha';
import { CasesList } from '../pages/CasesList';
import { ConversationsList } from '../pages/ConversationsList';
import { ConversationThread } from '../pages/ConversationThread';
import { KbList } from '../pages/KbList';
import { Settings } from '../pages/Settings';

/** Top-level SPA views, switched via AppShell state (D7 — no router; `ponytail:`
 *  no URL shareability, upgrade path = react-router hash router when desired).
 *  Client ficha and conversation thread are drill-downs rendered from list
 *  views, not top-level nav, so they do not appear here. */
export type View = PanelView;

export interface AppShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
}

/** Application shell: PanelShell frame and D7 state-based page navigation. */
export function AppShell({ user, onLogout }: AppShellProps) {
  const [view, setView] = useState<PanelView>('dashboard');
  const [clientId, setClientId] = useState<number | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const navigate = (nextView: PanelView) => {
    setClientId(null);
    setConversationId(null);
    setView(nextView);
  };

  const page = view === 'dashboard' ? <Dashboard />
    : view === 'clients' ? clientId !== null ? <ClientFicha customerId={clientId} /> : <ClientesList onOpenClient={setClientId} />
    : view === 'conversations' ? conversationId !== null ? <ConversationThread conversationId={conversationId} /> : <ConversationsList onOpenThread={setConversationId} />
    : view === 'cases' ? <CasesList />
    : view === 'kb' ? <KbList />
    : <Settings />;

  return (
    <PanelShell user={user} currentView={view} onNavigate={navigate} onLogout={onLogout}>
      {page}
    </PanelShell>
  );
}
