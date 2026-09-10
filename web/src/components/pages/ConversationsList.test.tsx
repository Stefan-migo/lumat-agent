import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationsList } from './ConversationsList';

const row = (id: number, state: string, responsible_id: number | null, extra: Record<string, unknown> = {}) => ({ id, customer_id: id, wa_phone: `+569${id}`, state, responsible_id, version: 2, summary: 'Needs visit', latest_inbound_at: '2026-08-27T10:00:00Z', reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null, customer: { id, name: `Cliente ${id}`, phone_e164: `+569${id}` }, case: null, case_id: null, emergency: false, acknowledged_at: null, case_status: null, case_priority: null, captured_data: null, ...extra });

const queue = (items: ReturnType<typeof row>[], counts = { all: items.length, human: 0, emergency: 0, case: 0, closed: 0 }) => ({ items, total: items.length, offset: 0, limit: 20, counts });

afterEach(() => vi.restoreAllMocks());

describe('production conversations list', () => {
  it('loads filters and exposes production state and assignee fields', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(queue([row(4, 'human', 7)], { all: 1, human: 1, emergency: 0, case: 0, closed: 0 })), { status: 200 }));
    render(<ConversationsList />);
    expect(await screen.findByText('Needs visit')).toBeInTheDocument();
    expect(screen.getByText(/Cliente 4/)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /humanas/i })).toHaveTextContent('1');
    expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations', expect.anything());
  });

  it.each([401, 403, 409, 422])('renders an actionable error for HTTP %s', async (status) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'problem' }), { status }));
    render(<ConversationsList />);
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 401 ? /sesión/i : status === 403 ? /permiso/i : /cargar/i);
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument();
  });

  it('renders row cards and marks the selected conversation after opening it', async () => {
    const onOpenThread = vi.fn();
    const user = userEvent.setup();
    render(<ConversationsList data={queue([row(4, 'human', 7), row(5, 'bot', null)])} onOpenThread={onOpenThread} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('Atención humana')).toBeInTheDocument();
    expect(screen.getByText('Agente atendiendo')).toBeInTheDocument();
    await user.click(screen.getByTestId('conversation-row-4'));

    expect(onOpenThread).toHaveBeenCalledWith(4);
    expect(screen.getByTestId('conversation-row-4')).toHaveAttribute('aria-current', 'page');
  });

  it('labels filters and exposes a page-level conversation region', () => {
    render(<ConversationsList data={queue([])} />);

    expect(screen.getByRole('region', { name: /filtros de conversaciones/i })).toBeInTheDocument();
    expect(screen.getByText(/no existen conversaciones/i)).toBeInTheDocument();
  });

  it('shows operational tabs, priority order, and direct rows', async () => {
    const items = [
      row(1, 'bot', null, { emergency: false, last_message_at: '2026-08-27T12:00:00Z' }),
      row(2, 'closed', null, { closed_at: '2026-08-27T13:00:00Z' }),
      row(3, 'human', 7),
      row(4, 'bot', null, { emergency: true, acknowledged_at: null }),
    ];
    render(<ConversationsList data={queue(items, { all: 4, human: 1, emergency: 1, case: 2, closed: 1 })} />);
    expect(screen.getByRole('tab', { name: /todas.*4/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /emergencias.*1/i })).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')[0]).toHaveTextContent('Cliente 4');
    expect(screen.getAllByRole('listitem')[1]).toHaveTextContent('Cliente 3');
    expect(screen.getAllByRole('listitem')[3]).toHaveTextContent('Cliente 2');
    await userEvent.setup().click(screen.getByRole('tab', { name: /cerradas/i }));
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
    expect(screen.getByText('Cliente 2')).toBeInTheDocument();
  });

  it('requests search and page changes and renders empty state as a DOM row', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(queue([])), { status: 200 }));
    const user = userEvent.setup();
    render(<ConversationsList />);
    await user.type(screen.getByRole('searchbox'), 'heater');
    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(screen.getByText(/no hay conversaciones/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/conversations?q=heater&limit=20&offset=0', expect.anything());
    expect(screen.getByRole('button', { name: /siguiente/i })).toBeInTheDocument();
  });

  it('refreshes after Tomar and Reconocer actions', async () => {
    const onRetry = vi.fn();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    const emergency = row(8, 'bot', null, { emergency: true, case_id: 44, acknowledged_at: null });
    const user = userEvent.setup();
    render(<ConversationsList data={queue([emergency])} onRetry={onRetry} />);
    await user.click(screen.getByRole('button', { name: /tomar/i }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await user.click(screen.getByRole('button', { name: /reconocer/i }));
    expect(onRetry).toHaveBeenCalledTimes(2);
  });
});
