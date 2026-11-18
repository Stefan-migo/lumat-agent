import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationsList } from './ConversationsList';

const row = (id: number, state: string, responsible_id: number | null, extra: Record<string, unknown> = {}) => ({ id, customer_id: id, wa_phone: `+569${id}`, state, responsible_id, version: 2, summary: 'Needs visit', latest_inbound_at: '2026-08-27T10:00:00Z', reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null, customer: { id, name: `Cliente ${id}`, phone_e164: `+569${id}` }, case: null, case_id: null, emergency: false, acknowledged_at: null, case_status: null, case_priority: null, captured_data: null, ...extra });

const queue = (items: ReturnType<typeof row>[], counts = { all: items.length, human: 0, emergency: 0, case: 0, closed: 0 }) => ({ items, total: items.length, offset: 0, limit: 10, counts });

afterEach(() => vi.restoreAllMocks());

describe('production conversations list', () => {
  it('keeps the fallback subtitle visible while loading', () => {
    render(<ConversationsList state="loading" />);
    expect(screen.getByText('Cola de conversaciones')).toBeInTheDocument();
  });

  it('loads filters and exposes production state and assignee fields', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(queue([row(4, 'human', 7)], { all: 1, human: 1, emergency: 0, case: 0, closed: 0 })), { status: 200 }));
    render(<ConversationsList />);
    await waitFor(() => expect(document.querySelector('.table-card__desktop')).toBeTruthy());
    const desktop = document.querySelector('.table-card__desktop') as HTMLElement;
    expect(await within(desktop).findByText('Needs visit')).toBeInTheDocument();
    expect(within(desktop).getByText('Cliente 4')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /atención humana/i })).toHaveTextContent('1');
    expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations?exclude_closed=true&limit=10&offset=0', expect.anything());
  });

  it('renders markdown summaries as clean plain text', () => {
    render(<ConversationsList data={queue([row(4, 'human', 7, { summary: '**Needs** visit' })])} />);
    expect(screen.getAllByText('Needs visit').length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toContain('**');
  });

  it.each([401, 403, 409, 422])('renders an actionable error for HTTP %s', async (status) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'problem' }), { status }));
    render(<ConversationsList />);
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 401 ? /sesión/i : status === 403 ? /permiso/i : /cargar/i);
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument();
  });

  it('renders a desktop table and marks the selected conversation after opening it', async () => {
    const onOpenThread = vi.fn();
    const user = userEvent.setup();
    render(<ConversationsList data={queue([row(4, 'human', 7), row(5, 'bot', null)])} onOpenThread={onOpenThread} />);

    const desktop = document.querySelector('.table-card__desktop') as HTMLElement;
    expect(within(desktop).getByRole('table')).toBeInTheDocument();
    expect(within(desktop).getAllByRole('row')).toHaveLength(3);
    expect(within(desktop).getByText('Atención humana')).toBeInTheDocument();
    expect(within(desktop).getByText('Agente atendiendo')).toBeInTheDocument();
    await user.click(within(desktop).getByTestId('conversation-row-4'));

    expect(onOpenThread).toHaveBeenCalledWith(4);
    expect(within(desktop).getByTestId('conversation-row-4')).toHaveAttribute('aria-current', 'page');
    const mobile = document.querySelector('.table-cards--mobile') as HTMLElement;
    expect(within(mobile).getByTestId('conversation-card-4')).toBeInTheDocument();
    expect(within(mobile).queryByTestId('conversation-row-4')).not.toBeInTheDocument();
  });

  it('opens a conversation from the compact row or keyboard without opening it from the action menu', async () => {
    const onOpenThread = vi.fn();
    const user = userEvent.setup();
    render(<ConversationsList data={queue([row(4, 'human', 7)])} onOpenThread={onOpenThread} />);

    const card = within(screen.getByTestId('conversation-card-4'));
    const open = card.getByRole('button', { name: 'Abrir conversación de Cliente 4' });
    expect(open).toHaveAccessibleDescription(/Needs visit.*Atención humana/);
    const summary = within(open).getByText('Needs visit');
    await user.click(summary);
    expect(onOpenThread).toHaveBeenCalledExactlyOnceWith(4);
    expect(open).toHaveAttribute('aria-current', 'page');
    onOpenThread.mockClear();
    await user.click(card.getByRole('button', { name: 'Acciones para Cliente 4' }));
    expect(onOpenThread).not.toHaveBeenCalled();
    await user.keyboard('{Escape}');
    open.focus();
    await user.keyboard('{Enter}');
    expect(onOpenThread).toHaveBeenCalledExactlyOnceWith(4);
    expect(open).toHaveAttribute('aria-current', 'page');
  });

  it('labels filters and exposes a page-level conversation region', () => {
    render(<ConversationsList data={queue([])} />);

    expect(document.querySelector('.table-card .table-toolbar')).toBeInTheDocument();
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
    let desktop = document.querySelector('.table-card__desktop') as HTMLElement;
    let rows = within(desktop).getAllByRole('row');
    expect(rows[1]).toHaveTextContent('Cliente 4');
    expect(rows[2]).toHaveTextContent('Cliente 3');
    expect(rows[4]).toHaveTextContent('Cliente 2');
    await userEvent.setup().click(screen.getByRole('tab', { name: /cerradas/i }));
    desktop = document.querySelector('.table-card__desktop') as HTMLElement;
    rows = within(desktop).getAllByRole('row');
    expect(rows).toHaveLength(5);
  });

  it('renders filtered-empty recovery and hides pagination for one page', async () => {
    const user = userEvent.setup();
    render(<ConversationsList data={queue([])} />);
    await user.type(screen.getByRole('searchbox'), 'heater');
    expect(await screen.findByText(/no encontramos conversaciones con estos filtros/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /limpiar búsqueda/i })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /paginación de conversaciones/i })).not.toBeInTheDocument();
  });

  it('keeps applied conversation filters understandable and removes one without clearing the others', async () => {
    const user = userEvent.setup();
    render(<ConversationsList data={queue([])} currentUserId={7} />);

    await user.click(screen.getByRole('tab', { name: /atención humana/i }));
    await user.click(screen.getByRole('button', { name: /filtrar por responsable/i }));
    await user.click(await screen.findByRole('menuitemradio', { name: 'Asignadas a mí' }));
    expect(await screen.findByRole('button', { name: 'Quitar filtro Atención humana' })).toBeInTheDocument();
    expect(screen.queryByText('Atención humana · Asignadas a mí')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Quitar filtros' })).toBeInTheDocument();
    expect(screen.getByText(/no encontramos conversaciones con estos filtros/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Quitar filtro Asignadas a mí' }));
    expect(screen.getByRole('group', { name: 'Filtros aplicados' })).toHaveTextContent('Atención humana');
    expect(screen.queryByText('Atención humana · Asignadas a mí')).not.toBeInTheDocument();
  });

  it('offers scoped filtered-empty recovery without replacing load errors', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ConversationsList data={queue([])} currentUserId={7} initialQueueContext={{ tab: 'human', query: 'heater', assignee: 'mine', page: 1 }} />);

    expect(screen.getByText(/no encontramos conversaciones con estos filtros/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /limpiar búsqueda/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /limpiar búsqueda/i }));
    expect(screen.getByRole('group', { name: 'Filtros aplicados' })).toHaveTextContent('Atención humana');
    expect(screen.getByRole('group', { name: 'Filtros aplicados' })).toHaveTextContent('Asignadas a mí');

    rerender(<ConversationsList state="error" />);
    expect(screen.getByRole('alert')).toHaveTextContent(/cargar las conversaciones/i);
    expect(screen.queryByText(/no encontramos conversaciones con estos filtros/i)).not.toBeInTheDocument();
  });

  it('initializes and reports queue return context without selection state', async () => {
    const onQueueContextChange = vi.fn();
    const user = userEvent.setup();
    render(<ConversationsList data={{ ...queue(Array.from({ length: 10 }, (_, index) => row(index + 1, 'bot', null))), total: 20 }} initialQueueContext={{ tab: 'human', query: 'heater', assignee: 'mine', page: 2 }} onQueueContextChange={onQueueContextChange} currentUserId={7} />);

    expect(screen.getByRole('tab', { name: /atención humana/i })).toHaveAttribute('data-state', 'active');
    expect(screen.getByRole('searchbox')).toHaveValue('heater');
    expect(screen.getByText('Mostrando 11–20 de 20 conversaciones')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /página anterior/i }));
    expect(onQueueContextChange).toHaveBeenLastCalledWith({ tab: 'human', query: 'heater', assignee: 'mine', page: 1 });
  });

  it('refreshes after Tomar and Reconocer actions', async () => {
    const onRetry = vi.fn();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    const emergency = row(8, 'bot', null, { emergency: true, case_id: 44, acknowledged_at: null });
    const user = userEvent.setup();
    render(<ConversationsList data={queue([emergency])} onRetry={onRetry} />);
    const desktop = document.querySelector('.table-card__desktop') as HTMLElement;
    await user.click(within(desktop).getByRole('button', { name: 'Tomar conversación' }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await user.click(within(desktop).getByRole('button', { name: /acciones para cliente 8/i }));
    await user.click(screen.getByRole('menuitem', { name: /reconocer/i }));
    expect(onRetry).toHaveBeenCalledTimes(2);
  });

  it('filters by responsable through the styled dropdown', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(queue([])), { status: 200 }));
    const user = userEvent.setup();
    render(<ConversationsList currentUserId={7} />);
    const trigger = screen.getByRole('button', { name: /filtrar por responsable/i });
    expect(trigger).toHaveTextContent('Responsable:');
    await user.click(trigger);
    await user.click(await screen.findByRole('menuitemradio', { name: 'Asignadas a mí' }));
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/conversations?responsible_id=7&exclude_closed=true&limit=10&offset=0', expect.anything()));
  });

  it('maps each tab to server filters and displays the server page range', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ ...queue(Array.from({ length: 10 }, (_, index) => row(index + 1, 'bot', null))), total: 34 }), { status: 200 }));
    const user = userEvent.setup();
    render(<ConversationsList />);
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/conversations?exclude_closed=true&limit=10&offset=0', expect.anything()));
    expect(await screen.findByText(/Mostrando 1–10 de 34 conversaciones/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /página siguiente/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/conversations?exclude_closed=true&limit=10&offset=10', expect.anything()));
    await user.click(await screen.findByRole('button', { name: /página anterior/i }));
    for (const [name, query] of [
      [/atención humana/i, 'state=human&limit=10&offset=0'],
      [/emergencias/i, 'exclude_closed=true&emergency=true&limit=10&offset=0'],
      [/con caso/i, 'exclude_closed=true&has_case=true&limit=10&offset=0'],
      [/cerradas/i, 'state=closed&limit=10&offset=0'],
    ] as const) {
      await user.click(screen.getByRole('tab', { name }));
      await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(`/panel/api/conversations?${query}`, expect.anything()));
    }
  });

  it('posts emergency acknowledgement to the case acknowledgement route', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    const emergency = row(8, 'bot', null, { emergency: true, case_id: 44, acknowledged_at: null });
    render(<ConversationsList data={queue([emergency])} />);
    const user = userEvent.setup();
    const desktop = document.querySelector('.table-card__desktop') as HTMLElement;
    await user.click(within(desktop).getByRole('button', { name: /acciones para cliente 8/i }));
    await user.click(screen.getByRole('menuitem', { name: /reconocer/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/panel/api/cases/44/ack', expect.anything()));
  });

  it('offers human conversation state actions and posts the selected transition', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    render(<ConversationsList data={queue([row(12, 'human', 7)])} />);
    const user = userEvent.setup();
    const desktop = document.querySelector('.table-card__desktop') as HTMLElement;

    await user.click(within(desktop).getByRole('button', { name: /acciones para cliente 12/i }));
    expect(screen.getByRole('menuitem', { name: 'Devolver al agente' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Cerrar conversación' })).toBeInTheDocument();
    await user.click(screen.getByRole('menuitem', { name: 'Cerrar conversación' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations/12/state', expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"state":"closed"'),
    })));
    const request = fetchMock.mock.calls.find(([url]) => url === '/panel/api/conversations/12/state')?.[1];
    expect(JSON.parse(request?.body as string)).toEqual(expect.objectContaining({ state: 'closed', expected_version: 2 }));
  });
});
