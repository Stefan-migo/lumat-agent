import { describe, expect, it, vi, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationThread } from './ConversationThread';
import type { Conversation, Message } from '../../types';

const migratedConversation = (id: number, state: Conversation['state'] = 'human', lastMessageAt = '2026-08-20T08:15:00-04:00'): Conversation => ({ id, customer_id: 1, wa_phone: null, state, responsible_id: null, version: 1, latest_inbound_at: lastMessageAt, reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, summary: null, last_message_at: lastMessageAt, created_at: lastMessageAt, closed_at: null });
const conversations = [migratedConversation(101, 'bot'), migratedConversation(102, 'closed', '2026-08-02T08:15:00-04:00'), migratedConversation(103), migratedConversation(105, 'human', '2026-08-10T14:30:00-04:00')];
const messages: Message[] = [{ id: 1, conversation_id: 101, direction: 'inbound', msg_type: 'text', text: 'Hello', media_url: null, created_at: '2026-08-20T08:15:00-04:00' }, { id: 2, conversation_id: 101, direction: 'outbound', msg_type: 'text', text: 'Reply', media_url: null, created_at: '2026-08-20T08:16:00-04:00' }];

const thread = { conversation: { id: 9, customer_id: 4, wa_phone: '+5694', state: 'human', responsible_id: 7, version: 2, summary: 'Help', latest_inbound_at: '2026-08-27T10:00:00Z', reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null }, messages: [{ id: 1, conversation_id: 9, direction: 'inbound' as const, msg_type: 'text', text: 'Hola', media_url: null, delivery_status: null, delivery_error: null, delivery_attempts: 0, last_attempt_at: null, delivered_at: null, created_at: '2026-08-27T09:00:00Z' }], messages_total: 1 };

it('loads a bounded preview and fetches the full thread when expanded', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ...thread, messages_total: 12 }), { status: 200 }));
  const user = userEvent.setup();
  render(<ConversationThread conversationId={9} />);

  expect(await screen.findByText('Hola')).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations/9?messages_limit=10', expect.anything());
  await user.click(screen.getByRole('button', { name: '2 mensajes anteriores · Ver todos' }));
  expect(await screen.findByRole('button', { name: 'Ver menos' })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/conversations/9', expect.anything());
});

it('does not show message disclosure for ten or fewer messages', () => {
  render(<ConversationThread data={{ ...thread, messages_total: 10 }} />);
  expect(screen.queryByRole('button', { name: /Ver todos/ })).not.toBeInTheDocument();
});

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
  await user.click(screen.getByRole('button', { name: 'Acciones de la conversación' }));
  await user.click(await screen.findByRole('menuitem', { name: 'Cerrar conversación' }));

  expect(await screen.findByText(/Cerrada/)).toBeInTheDocument();
  expect(threadRequests).toBe(2);
  expect(fetchMock).toHaveBeenCalledWith('/panel/api/conversations/9/state', expect.objectContaining({ method: 'POST' }));
});

describe('conversation message media', () => {
  const mediaMessage = (overrides: Partial<Message>): Message => ({
    ...thread.messages[0],
    id: 20,
    msg_type: 'image',
    media_url: 'https://lookaside.facebook.com/temporary-token',
    media_available: true,
    media_download_url: '/panel/api/conversations/9/messages/20/media',
    caption: null,
    ...overrides,
  });

  it('renders images from the authenticated URL with caption alt text', () => {
    render(<ConversationThread data={{ ...thread, messages: [mediaMessage({ caption: 'Foto del calefón' })] }} state="ready" />);
    const image = screen.getByRole('img', { name: 'Foto del calefón' });
    expect(image).toHaveAttribute('src', '/panel/api/conversations/9/messages/20/media');
    expect(image).toHaveAttribute('alt', 'Foto del calefón');
    expect(screen.getByText('Foto del calefón')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /lookaside/i })).not.toBeInTheDocument();
  });

  it('renders videos with controls from the authenticated URL', () => {
    render(<ConversationThread data={{ ...thread, messages: [mediaMessage({ msg_type: 'video' })] }} state="ready" />);
    const video = document.querySelector('video');
    expect(video).toHaveAttribute('src', '/panel/api/conversations/9/messages/20/media');
    expect(video).toHaveAttribute('controls');
    expect(video).toHaveAttribute('aria-label');
  });

  it('renders audio with controls and a compact accessible label', () => {
    render(<ConversationThread data={{ ...thread, messages: [mediaMessage({ msg_type: 'audio' })] }} state="ready" />);
    const audio = document.querySelector('audio');
    expect(audio).toHaveAttribute('src', '/panel/api/conversations/9/messages/20/media');
    expect(audio).toHaveAttribute('controls');
    expect(audio).toHaveAttribute('aria-label');
    expect(screen.getByText('Audio adjunto')).toBeInTheDocument();
  });

  it('renders documents as download links labelled with their caption', () => {
    render(<ConversationThread data={{ ...thread, messages: [mediaMessage({ msg_type: 'document', caption: 'informe.pdf' })] }} state="ready" />);
    const link = screen.getByRole('link', { name: 'informe.pdf' });
    expect(link).toHaveAttribute('href', '/panel/api/conversations/9/messages/20/media');
    expect(link).toHaveAttribute('download');
  });

  it('shows an unavailable notice instead of media when the backend file is missing', () => {
    render(<ConversationThread data={{ ...thread, messages: [mediaMessage({ media_available: false })] }} state="ready" />);
    expect(screen.getAllByRole('status').some((status) => /archivo.*no está disponible/i.test(status.textContent ?? ''))).toBe(true);
    expect(document.querySelector('img, video, audio')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('keeps text messages exactly as before', () => {
    render(<ConversationThread data={{ ...thread, messages: [{ ...thread.messages[0], text: 'Hola', media_url: null }] }} state="ready" />);
    const bubble = screen.getByText('Hola').closest('.ai-agent-grammar__bubble');
    expect(bubble).toHaveTextContent('Hola');
    expect(bubble?.querySelector('img, video, audio, a')).toBeNull();
    // The timestamp lives inside the bubble now (mockup 2026-10-31), so the text is no longer alone.
    expect(bubble?.textContent).toBe('Hola09:00');
  });
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
  // Only the outgoing bubble carries an author label and no longer an avatar; the incoming side is
  // the customer, so it reads without a speaker line.
  expect(inbound.querySelector('.ai-agent-grammar__message-meta')).toBeNull();
  expect(inbound.querySelector('.conversation-thread__bubble-meta')).toHaveTextContent('09:00');
  expect(inbound.querySelector('img, .conversation-thread__bubble-avatar')).toBeNull();
  expect(outbound.querySelector('.ai-agent-grammar__message-meta')).toHaveTextContent('Lumat');
  expect(within(outbound).getByLabelText('Entregado')).toBeInTheDocument();
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

it('keeps conversation actions in the thread header and context actions-free', async () => {
  const user = userEvent.setup();
  render(<ConversationThread data={{ ...thread, conversation: {
    ...thread.conversation,
    customer: { id: 4, name: 'María González', phone_e164: '+5694' },
    case: { id: 22, service: 'Urgencia', priority: 'high', status: 'open', emergency: true, summary: 'Needs help', acknowledged_at: null, closed_at: null },
    case_id: 22,
    emergency: true,
    acknowledged_at: null,
  }, messages: thread.messages }} state="ready" interactive />);

  // The header band is the compact one from the 2026-10-31 mockup; the old two-row identity +
  // actions block and the "Historial de mensajes" band are gone.
  const header = document.querySelector('.conversation-thread__header');
  expect(header).not.toBeNull();
  expect(header).toContainElement(screen.getByRole('button', { name: 'Tomar conversación' }));
  expect(header).toContainElement(screen.getByRole('button', { name: 'Acciones de la conversación' }));
  expect(screen.getByRole('complementary', { name: /inspector de conversación/i })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Acciones' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Acciones de la conversación' }));
  for (const label of ['Devolver al agente', 'Cerrar conversación', 'Reconocer emergencia']) {
    expect(await screen.findByRole('menuitem', { name: label })).toBeInTheDocument();
  }
});

// Native review R3-002 claimed the mobile menu omits emergency acknowledgement. It does not:
// both menus are built by the same `conversationMenuItems`, which appends the acknowledge item
// outside the per-view options. This locks the behaviour so a refactor cannot drop it.
it('offers emergency acknowledgement from the mobile action menu', async () => {
  const user = userEvent.setup();
  render(<ConversationThread data={{ ...thread, conversation: {
    ...thread.conversation,
    customer: { id: 4, name: 'María González', phone_e164: '+5694' },
    case: { id: 22, service: 'Urgencia', priority: 'high', status: 'open', emergency: true, summary: null, acknowledged_at: null, closed_at: null },
    case_id: 22,
    emergency: true,
    acknowledged_at: null,
  }, messages: thread.messages }} state="ready" interactive />);

  await user.click(screen.getByRole('button', { name: 'Más acciones de la conversación' }));
  expect(await screen.findByRole('menuitem', { name: 'Reconocer emergencia' })).toBeInTheDocument();
});

it('gives every inspector details element its own summary', () => {
  render(<ConversationThread data={{ ...thread, conversation: {
    ...thread.conversation,
    customer: { id: 4, name: 'María González', phone_e164: '+5694' },
    case: { id: 22, service: 'Urgencia', priority: 'high', status: 'open', emergency: false, summary: null, acknowledged_at: null, closed_at: null },
    captured_data: { source: 'web' },
  } }} state="ready" />);

  const inspector = screen.getByRole('complementary', { name: /inspector de conversación/i });
  for (const details of inspector.querySelectorAll('details')) {
    expect(details.querySelector(':scope > summary')).not.toBeNull();
  }
  expect(inspector.querySelector('summary')).not.toHaveTextContent(/^Details$/);
});

it('does not hide the conversation inspector at the 64rem breakpoint', () => {
  const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
  const mediaBlock = css.match(/@media \(max-width: 64rem\) \{([\s\S]*?)\n\}/)?.[1] ?? '';
  expect(mediaBlock).not.toMatch(/\.ai-agent-grammar__inspector\s*\{\s*display:\s*none;/);
});

describe('conversation inspector layout CSS contract', () => {
  const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');

  it('preserves the workspace card radius and mobile reset', () => {
    expect(css).toMatch(/\.conversation-workspace\s*\{[^}]*border-radius:\s*var\(--radius-lg\)/s);
    expect(css).toMatch(/@media \(max-width: 39\.99rem\)[\s\S]*?\.conversation-workspace\s*\{[^}]*border-radius:\s*0/s);
  });

  it('gives the inspector column a bounded responsive width', () => {
    expect(css).toMatch(/\.conversation-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(384px, 1fr\)\s+minmax\(288px, 384px\);/);
  });

  it('keeps the workspace height bounds stable at text zoom', () => {
    expect(css).toMatch(/\.conversation-workspace\s*\{[^}]*height:\s*clamp\(480px, calc\(100dvh - 15rem\), 736px\);/);
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
  expect(screen.getByRole('heading', { name: 'Caso vinculado' })).toBeInTheDocument();
  expect(within(screen.getByRole('complementary', { name: /inspector de conversación/i })).getByText('María González')).toBeInTheDocument();
  expect(screen.getByText('Urgencia')).toBeInTheDocument();
  expect(screen.getByText('Preferred language')).toBeInTheDocument();
  expect(screen.getByText('es')).toBeInTheDocument();
  expect(screen.getByText('Nested')).toBeInTheDocument();
  expect(screen.getByText('2')).toBeInTheDocument();
});

it('renders the inspector case summary as markdown', () => {
  render(<ConversationThread data={{ ...thread, conversation: {
    ...thread.conversation,
    case: { id: 22, service: 'Urgencia', priority: 'high', status: 'open', emergency: true, summary: '**Needs** help', acknowledged_at: null, closed_at: null },
    case_id: 22,
  } }} state="ready" />);
  const inspector = screen.getByRole('complementary', { name: /inspector de conversación/i });
  expect(within(inspector).getByText('Needs')).toBeInTheDocument();
  expect(within(inspector).getByText('Needs').tagName).toBe('STRONG');
  expect(inspector.textContent).not.toContain('**');
});

it('keeps the thread usable without optional case or captured data', () => {
  render(<ConversationThread data={{ ...thread, conversation: { ...thread.conversation, customer: { id: 4, name: 'María González', phone_e164: '+5694' }, case: null, case_id: null, captured_data: null } }} state="ready" />);

  expect(screen.getByText('Hola')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /inspector de conversación/i })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Caso vinculado' })).not.toBeInTheDocument();
  expect(screen.queryByText('Datos capturados')).not.toBeInTheDocument();
});

describe('migrated InboxThread scenarios', () => {
  it('keeps reply-window truthfulness and directional message ownership', () => {
    render(<ConversationThread data={{ conversation: { ...conversations[2], customer: { id: 1, name: 'Marcela Fuentes', phone_e164: null } }, messages, messages_total: messages.length }} state="ready" interactive customerName={() => 'Marcela Fuentes'} />);
    expect(screen.getByLabelText(/mensaje entrante de marcela/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mensaje saliente de lumat/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeEnabled();
  });

  it('preserves enabled, closed, bot, and stale composer scenarios', () => {
    const { rerender } = render(<ConversationThread data={{ conversation: conversations[2], messages, messages_total: messages.length }} state="ready" interactive />);
    expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeEnabled();
    rerender(<ConversationThread data={{ conversation: { ...conversations[1], last_message_at: '2026-08-01T08:15:00-04:00', reply_window_open: false }, messages, messages_total: messages.length }} state="ready" interactive />);
    expect(screen.getByRole('status', { name: 'Cerrada' })).toBeInTheDocument();
    rerender(<ConversationThread data={{ conversation: conversations[2], messages, messages_total: messages.length }} state="stale" interactive />);
    expect(screen.getAllByRole('status').some((status) => /desactualizados/i.test(status.textContent ?? ''))).toBe(true);
  });
});

// The 2026-10-31 mockup moved three things that were invisible to the operator before: the
// full-thread control out of the scroller, the client details over the thread instead of beside it,
// and a day separator above each day's messages.
describe('conversation mockup layout', () => {
  it('keeps the full-thread control above the scroller', () => {
    const messages = Array.from({ length: 14 }, (_, index) => ({ ...thread.messages[0], id: index + 1, text: `Mensaje ${index + 1}` }));
    render(<ConversationThread data={{ ...thread, messages, messages_total: messages.length }} state="ready" />);
    const toggle = screen.getByRole('button', { name: /ver todos/i });
    const scroller = document.querySelector('.ai-agent-grammar__thread-area');
    expect(scroller).not.toBeNull();
    expect(scroller).not.toContainElement(toggle);
  });

  it('opens and closes the client details without giving up thread width', async () => {
    const user = userEvent.setup();
    render(<ConversationThread data={{ ...thread, conversation: { ...thread.conversation, customer: { id: 4, name: 'María González', phone_e164: '+56941234567' } } }} state="ready" />);
    expect(screen.getByRole('dialog', { name: 'Detalles del cliente' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cerrar detalles del cliente' }));
    expect(screen.queryByRole('dialog', { name: 'Detalles del cliente' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Detalles del cliente' }));
    expect(screen.getByRole('dialog', { name: 'Detalles del cliente' })).toBeInTheDocument();
  });

  it('separates messages by day and prints the speaker only for outgoing ones', () => {
    const messages = [
      { ...thread.messages[0], id: 1, created_at: '2026-10-09T19:02:00Z' },
      { ...thread.messages[0], id: 2, created_at: '2026-10-09T19:05:00Z' },
      { ...thread.messages[0], id: 3, created_at: '2026-10-10T09:00:00Z', direction: 'outbound' as const, delivery_status: 'sent' as const },
    ];
    render(<ConversationThread data={{ ...thread, messages, messages_total: messages.length }} state="ready" customerName={() => 'María González'} />);
    const separators = screen.getAllByRole('separator');
    expect(separators).toHaveLength(2);
    expect(separators[0]).toHaveTextContent('9 de octubre de 2026');
    expect(separators[1]).toHaveTextContent('10 de octubre de 2026');
    // The customer's name belongs to the header, not to every incoming bubble: only the outgoing
    // side prints a speaker line.
    const speakers = document.querySelectorAll('.ai-agent-grammar__message-meta');
    expect(speakers).toHaveLength(1);
    expect(speakers[0]).toHaveTextContent('Lumat');
  });
});
