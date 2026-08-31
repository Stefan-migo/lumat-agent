import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationsList } from './ConversationsList';

const row = (id: number, state: string, responsible_id: number | null) => ({ id, customer_id: id, wa_phone: `+569${id}`, state, responsible_id, version: 2, summary: 'Needs visit', last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null });

afterEach(() => vi.restoreAllMocks());

describe('production conversations list', () => {
  it('loads filters and exposes production state and assignee fields', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ conversations: [row(4, 'human', 7)] }), { status: 200 }));
    const user = userEvent.setup();
    render(<ConversationsList />);
    expect(await screen.findByText('Needs visit')).toBeInTheDocument();
    expect(screen.getByText(/Responsable: 7/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Filtrar por estado'), 'human');
    expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/conversations?state=human', expect.anything());
  });

  it.each([401, 403, 409, 422])('renders an actionable error for HTTP %s', async (status) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'problem' }), { status }));
    render(<ConversationsList />);
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 401 ? /sesión/i : status === 403 ? /permiso/i : /cargar/i);
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument();
  });
});
