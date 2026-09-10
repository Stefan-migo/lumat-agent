import { expect, it, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationThread } from './ConversationThread';

const thread = { conversation: { id: 9, customer_id: 4, wa_phone: '+5694', state: 'human', responsible_id: 7, version: 2, summary: 'Help', latest_inbound_at: '2026-08-27T10:00:00Z', reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null }, messages: [{ id: 1, conversation_id: 9, direction: 'inbound' as const, msg_type: 'text', text: 'Hola', media_url: null, delivery_status: null, delivery_error: null, delivery_attempts: 0, last_attempt_at: null, delivered_at: null, created_at: '2026-08-27T09:00:00Z' }] };

afterEach(() => vi.restoreAllMocks());

it('shows the composer and disables it outside the customer window', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ...thread, conversation: { ...thread.conversation, reply_window_open: false } }), { status: 200 }));
  render(<ConversationThread interactive conversationId={9} />);
  expect(await screen.findByText('Hola')).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeDisabled();
  expect(screen.getAllByText(/24 horas/i).length).toBeGreaterThan(0);
});

it('permits replying when the API says the customer window is open', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(thread), { status: 200 }));
  render(<ConversationThread interactive conversationId={9} />);
  expect(await screen.findByText('Hola')).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeEnabled();
  expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled();
});

it('fails closed when the API omits the reply-window field', async () => {
  const { conversation, ...withoutWindow } = thread;
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
    ...withoutWindow,
    conversation: { ...conversation, reply_window_open: undefined },
  }), { status: 200 }));
  render(<ConversationThread interactive conversationId={9} />);
  expect(await screen.findByText('Hola')).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeDisabled();
});

it('reports failed delivery and offers retry without optimistic message state', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input).endsWith('/messages')) return new Response(JSON.stringify({ detail: 'failed' }), { status: 502 });
    return new Response(JSON.stringify(thread), { status: 200 });
  });
  const user = userEvent.setup();
  render(<ConversationThread interactive conversationId={9} />);
  await screen.findByText('Hola');
  const composer = screen.getByRole('textbox', { name: /respuesta/i });
  await user.type(composer, 'Respuesta');
  await user.click(screen.getByRole('button', { name: /enviar/i }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/falló/i);
  expect(screen.getByRole('textbox', { name: /respuesta/i })).toHaveValue('Respuesta');
  expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations/9/messages', expect.anything());
});

it('refetches the thread after a successful close command', async () => {
  const closedThread = {
    ...thread,
    conversation: { ...thread.conversation, state: 'closed' },
  };
  let threadRequests = 0;
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const path = String(input);
    if (path.endsWith('/state')) {
      return new Response(JSON.stringify({ ok: true, conversation: closedThread.conversation }), { status: 200 });
    }
    threadRequests += 1;
    return new Response(JSON.stringify(threadRequests === 1 ? thread : closedThread), { status: 200 });
  });
  const user = userEvent.setup();

  render(<ConversationThread interactive conversationId={9} />);
  expect(await screen.findByText(/Atención humana/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Cerrar' }));

  expect(await screen.findByText(/Cerrada/)).toBeInTheDocument();
  expect(threadRequests).toBe(2);
  expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations/9/state', expect.objectContaining({ method: 'POST' }));
});

it('presents directional bubbles with identity and owner status', () => {
  render(<ConversationThread data={{ ...thread, messages: [
    ...thread.messages,
    { ...thread.messages[0], id: 2, direction: 'outbound' as const, text: 'Te ayudamos', delivery_status: 'sent' as const },
  ] }} state="ready" customerName={() => 'María González'} />);

  expect(screen.getByRole('status', { name: 'Atención humana' })).toBeInTheDocument();
  expect(screen.getByLabelText(/mensaje entrante de maría/i)).toHaveClass('ai-agent-grammar__bubble-row');
  expect(screen.getByLabelText(/mensaje saliente de lumat/i)).toHaveClass('ai-agent-grammar__bubble-row--outbound');
  expect(screen.getByText('María González')).toBeInTheDocument();
  expect(screen.getByText('Lumat')).toBeInTheDocument();
});

it('shows truthful handoff and closed-window reply reason', () => {
  render(<ConversationThread data={{ ...thread, conversation: { ...thread.conversation, reply_window_open: false } }} state="ready" interactive />);

  expect(screen.getByRole('status', { name: 'Atención humana' })).toBeInTheDocument();
  expect(screen.getByRole('status', { name: /ventana de 24 horas/i })).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeDisabled();
});

it('shows delivery failure content beside the retry action', () => {
  render(<ConversationThread data={{ ...thread, messages: [{ ...thread.messages[0], delivery_status: 'failed' as const, delivery_error: 'Canal no disponible' }] }} state="ready" interactive />);

  expect(screen.getByText(/canal no disponible/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /reintentar entrega #1/i })).toBeInTheDocument();
});

  it('renders the conversation inspector beside the thread', () => {
  render(<ConversationThread data={{ ...thread, conversation: {
    ...thread.conversation,
    customer: { id: 4, name: 'María González', phone_e164: '+5694' },
    case: { id: 22, service: 'Urgencia', priority: 'high', status: 'open', emergency: true, summary: 'Needs help', acknowledged_at: null, closed_at: null },
    case_id: 22,
    emergency: true,
    acknowledged_at: null,
    case_status: 'open',
    case_priority: 'high',
    captured_data: { preferred_language: 'es', nested: { source: 'web' }, attempts: 2 },
  }}} state="ready" />);

    expect(screen.getByRole('complementary', { name: /inspector de conversación/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Caso' })).toBeInTheDocument();
  expect(screen.getByText('María González')).toBeInTheDocument();
  expect(screen.getByText('Urgencia')).toBeInTheDocument();
  expect(screen.getByText('preferred_language')).toBeInTheDocument();
  expect(screen.getByText('es')).toBeInTheDocument();
  expect(screen.getByText('nested')).toBeInTheDocument();
  expect(screen.getByText('2')).toBeInTheDocument();
});

it('keeps the thread usable without optional case or captured data', () => {
  render(<ConversationThread data={{ ...thread, conversation: { ...thread.conversation, customer: { id: 4, name: 'María González', phone_e164: '+5694' }, case: null, case_id: null, captured_data: null } }} state="ready" />);

  expect(screen.getByText('Hola')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /inspector de conversación/i })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Caso' })).not.toBeInTheDocument();
  expect(screen.queryByText('Datos capturados')).not.toBeInTheDocument();
});
