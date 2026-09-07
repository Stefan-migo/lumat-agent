import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AppShell } from './AppShell';

const user = { username: 'vero', role: 'operador' as const };

afterEach(() => vi.restoreAllMocks());

describe('active conversation rail', () => {
  it('loads customer names from the active-summary endpoint', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({
      conversations: [{ id: 7, customer_name: 'María González', state: 'human', last_message_at: '2026-09-07T10:00:00Z' }],
    }), { status: 200 }));

    render(<AppShell user={user} loadActiveThreads />);

    expect(await screen.findByRole('button', { name: /María González/ })).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/conversations/active', expect.anything());
  });

  it('announces loading and request failure without fabricating rows', async () => {
    let rejectRequest!: (reason: Error) => void;
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise((_, reject) => { rejectRequest = reject; }));
    render(<AppShell user={user} loadActiveThreads />);
    expect(screen.getByRole('status', { name: 'Conversaciones activas' })).toHaveTextContent('Cargando');

    rejectRequest(new Error('network down'));
    await waitFor(() => expect(screen.getByRole('alert', { name: 'Conversaciones activas' })).toHaveTextContent('No se pudieron cargar'));
    expect(screen.queryByRole('button', { name: /María González/ })).not.toBeInTheDocument();
  });

  it('keeps active rows visible and announces a disconnected socket', () => {
    render(<AppShell user={user} activeThreads={{ status: 'ready', threads: [{ id: 7, label: 'María González', status: 'human' }] }} />);
    expect(screen.getByRole('button', { name: /María González/ })).toBeInTheDocument();
    expect(document.querySelector('.panel-shell__active-threads-connection')).toHaveTextContent('desconectada');
  });
});
