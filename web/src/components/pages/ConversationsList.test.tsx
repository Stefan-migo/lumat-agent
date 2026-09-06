import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationsList } from './ConversationsList';

const row = (id: number, state: string, responsible_id: number | null) => ({ id, customer_id: id, wa_phone: `+569${id}`, state, responsible_id, version: 2, summary: 'Needs visit', latest_inbound_at: '2026-08-27T10:00:00Z', reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null });

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

  it('keeps a data table and marks the selected conversation after opening it', async () => {
    const onOpenThread = vi.fn();
    const user = userEvent.setup();
    render(<ConversationsList data={{ conversations: [row(4, 'human', 7), row(5, 'bot', null)] }} onOpenThread={onOpenThread} />);

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Atención humana')).toBeInTheDocument();
    expect(screen.getByText('Agente atendiendo')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /abrir conversación #4/i }));

    expect(onOpenThread).toHaveBeenCalledWith(4);
    expect(screen.getByTestId('conversation-row-4')).toHaveAttribute('aria-current', 'page');
  });

  it('labels filters and exposes a page-level conversation region', () => {
    render(<ConversationsList data={{ conversations: [] }} />);

    expect(screen.getByRole('region', { name: /filtros de conversaciones/i })).toBeInTheDocument();
    expect(screen.getByText(/no existen conversaciones/i)).toBeInTheDocument();
  });
});
