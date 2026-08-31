import { expect, it, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationThread } from './ConversationThread';

const thread = { conversation: { id: 9, customer_id: 4, wa_phone: '+5694', state: 'human', responsible_id: 7, version: 2, summary: 'Help', last_message_at: '2026-08-27T10:00:00Z', created_at: '2026-08-27T09:00:00Z', closed_at: null }, messages: [{ id: 1, conversation_id: 9, direction: 'inbound' as const, msg_type: 'text', text: 'Hola', media_url: null, delivery_status: null, delivery_error: null, delivery_attempts: 0, last_attempt_at: null, delivered_at: null, created_at: '2026-08-27T09:00:00Z' }] };

afterEach(() => vi.restoreAllMocks());

it('shows the composer and disables it outside the customer window', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ...thread, conversation: { ...thread.conversation, reply_window_open: false } }), { status: 200 }));
  render(<ConversationThread interactive conversationId={9} />);
  expect(await screen.findByText('Hola')).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /respuesta/i })).toBeDisabled();
  expect(screen.getByText(/24 horas/i)).toBeInTheDocument();
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
