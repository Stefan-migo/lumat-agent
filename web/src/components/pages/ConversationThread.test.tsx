import { describe, expect, it, vi, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationThread } from './ConversationThread';
import type { Conversation, Message } from '../../types';

const migratedConversation = (id: number, state: Conversation['state'] = 'human', lastMessageAt = '2026-08-20T08:15:00-04:00'): Conversation => ({ id, customer_id: 1, wa_phone: null, state, responsible_id: null, version: 1, latest_inbound_at: lastMessageAt, reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, summary: null, last_message_at: lastMessageAt, created_at: lastMessageAt, closed_at: null });
const conversations = [migratedConversation(101, 'bot'), migratedConversation(102, 'closed', '2026-08-02T08:15:00-04:00'), migratedConversation(103), migratedConversation(105, 'human', '2026-08-10T14:30:00-04:00')];
const messages: Message[] = [{ id: 1, conversation_id: 101, direction: 'inbound', msg_type: 'text', text: 'Hello', media_url: null, created_at: '2026-08-20T08:15:00-04:00' }, { id: 2, conversation_id: 101, direction: 'outbound', msg_type: 'text', text: 'Reply', media_url: null, created_at: '2026-08-20T08:16:00-04:00' }];

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
  const inbound = screen.getByLabelText(/mensaje entrante de maría/i);
  const outbound = screen.getByLabelText(/mensaje saliente de lumat/i);
  expect(inbound).toHaveClass('ai-agent-grammar__bubble-row');
  expect(outbound).toHaveClass('ai-agent-grammar__bubble-row--outbound');
  expect(inbound.querySelector('.ai-agent-grammar__bubble')).toBeTruthy();
  expect(inbound.querySelector('.ai-agent-grammar__message-meta')).toHaveTextContent('María González');
  expect(inbound.querySelector('.ai-agent-grammar__message-time')).toHaveTextContent('09:00');
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

it('keeps conversation actions in the thread header and context actions-free', () => {
  render(<ConversationThread data={{ ...thread, conversation: {
    ...thread.conversation,
    customer: { id: 4, name: 'María González', phone_e164: '+5694' },
    case: { id: 22, service: 'Urgencia', priority: 'high', status: 'open', emergency: true, summary: 'Needs help', acknowledged_at: null, closed_at: null },
    case_id: 22,
    emergency: true,
    acknowledged_at: null,
  }, messages: thread.messages }} state="ready" interactive />);

  const header = document.querySelector('.ai-agent-grammar__header');
  expect(header).not.toBeNull();
  for (const label of ['Tomar', 'Devolver', 'Cerrar', 'Reconocer emergencia']) {
    const button = screen.getByRole('button', { name: label });
    expect(header).toContainElement(button);
  }
  expect(screen.getByRole('complementary', { name: /inspector de conversación/i }).querySelector('details')).toBeTruthy();
  expect(screen.queryByRole('heading', { name: 'Acciones' })).not.toBeInTheDocument();
});

it('does not hide the conversation inspector at the 64rem breakpoint', () => {
  const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
  const mediaBlock = css.match(/@media \(max-width: 64rem\) \{([\s\S]*?)\n\}/)?.[1] ?? '';
  expect(mediaBlock).not.toMatch(/\.ai-agent-grammar__inspector\s*\{\s*display:\s*none;/);
});

describe('conversation inspector layout CSS contract', () => {
  const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');

  it('gives the inspector column a bounded responsive width', () => {
    expect(css).toMatch(/\.conversation-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)\s+minmax\(18rem, 24rem\);/);
  });

  it('allows inspector detail rows to wrap', () => {
    expect(css).toMatch(/\.ai-agent-grammar__detail\s*\{[^}]*flex-wrap:\s*wrap;/);
  });

  it('breaks long inspector detail values anywhere', () => {
    expect(css).toMatch(/\.ai-agent-grammar__detail dd\s*\{[^}]*overflow-wrap:\s*anywhere;/);
  });

  it('prevents the inspector from scrolling horizontally', () => {
    expect(css).toMatch(/\.conversation-workspace \.ai-agent-grammar__inspector\s*\{[^}]*overflow-x:\s*hidden;/);
  });
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

describe('migrated InboxThread scenarios', () => {
  it('keeps reply-window truthfulness and directional message ownership', () => {
    render(<ConversationThread data={{ conversation: { ...conversations[2], customer: { id: 1, name: 'Marcela Fuentes', phone_e164: null } }, messages }} state="ready" interactive customerName={() => 'Marcela Fuentes'} />);
    expect(screen.getByLabelText(/mensaje entrante de marcela/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mensaje saliente de lumat/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeEnabled();
  });

  it('preserves enabled, closed, bot, and stale composer scenarios', () => {
    const { rerender } = render(<ConversationThread data={{ conversation: conversations[2], messages }} state="ready" interactive />);
    expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeEnabled();
    rerender(<ConversationThread data={{ conversation: { ...conversations[1], last_message_at: '2026-08-01T08:15:00-04:00', reply_window_open: false }, messages }} state="ready" interactive />);
    expect(screen.getByRole('status', { name: 'Cerrada' })).toBeInTheDocument();
    rerender(<ConversationThread data={{ conversation: conversations[2], messages }} state="stale" interactive />);
    expect(screen.getAllByRole('status').some((status) => /desactualizados/i.test(status.textContent ?? ''))).toBe(true);
  });
});
