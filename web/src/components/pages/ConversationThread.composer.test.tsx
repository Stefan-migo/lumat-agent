import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationThread } from './ConversationThread';
import { sendMedia } from '../../api';
import type { ConversationThread as ThreadData } from '../../types';

vi.mock('../../api', async (importOriginal) => ({
  ...await importOriginal<typeof import('../../api')>(),
  sendMedia: vi.fn(),
}));

const thread: ThreadData = {
  conversation: { id: 9, customer_id: 4, wa_phone: null, state: 'human', responsible_id: null, version: 1, latest_inbound_at: null, reply_window_open: true, delivery_summary: { failed: 0, pending: 0, sending: 0, sent: 0, unknown: 0 }, summary: null, last_message_at: null, created_at: null, closed_at: null },
  messages: [{ id: 1, conversation_id: 9, direction: 'inbound', msg_type: 'text', text: 'Hola', media_url: null, created_at: null }], messages_total: 1,
};
const result = { ok: true as const, message: { id: 2, conversation_id: 9, direction: 'outbound' as const, msg_type: 'audio', text: null, media_url: null, created_at: null } };
let recorderMimeSupport: string[] = [];
let recorderInstances: FakeRecorder[] = [];
let tracks: Array<{ stop: ReturnType<typeof vi.fn> }> = [];
class FakeRecorder {
  static isTypeSupported = vi.fn((mime: string) => recorderMimeSupport.includes(mime));
  mimeType: string;
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn(() => { this.ondataavailable?.({ data: new Blob(['recorded']) }); this.onstop?.(); });
  constructor(_stream: MediaStream, options?: MediaRecorderOptions) { this.mimeType = options?.mimeType ?? ''; recorderInstances.push(this); }
}

afterEach(() => { vi.restoreAllMocks(); recorderMimeSupport = []; recorderInstances = []; tracks = []; });

describe('conversation media composer', () => {
  it('uploads an attached file with a request id and clears the selection after success', async () => {
    vi.mocked(sendMedia).mockResolvedValue(result);
    const user = userEvent.setup();
    render(<ConversationThread conversationId={9} data={thread} state="ready" interactive />);
    const file = new File(['image-data'], 'photo.png', { type: 'image/png' });
    await user.upload(screen.getByLabelText('Adjuntar archivo', { selector: 'input' }), file);
    expect(screen.getByText(/photo.png/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Enviar archivo' }));
    await waitFor(() => expect(sendMedia).toHaveBeenCalledWith(9, expect.objectContaining({ file, requestId: expect.any(String) })));
    expect(screen.queryByText(/photo.png/)).not.toBeInTheDocument();
  });

  it('keeps a rejected file selected and shows the backend detail', async () => {
    vi.mocked(sendMedia).mockRejectedValue({ status: 422, detail: 'El archivo supera el límite permitido' });
    const user = userEvent.setup();
    render(<ConversationThread conversationId={9} data={thread} state="ready" interactive />);
    await user.upload(screen.getByLabelText('Adjuntar archivo', { selector: 'input' }), new File(['x'], 'large.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Enviar archivo' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El archivo supera el límite permitido');
    expect(screen.getByText(/large.pdf/)).toBeInTheDocument();
  });

  it('disables attachments when the reply window is closed', () => {
    render(<ConversationThread data={{ ...thread, conversation: { ...thread.conversation, reply_window_open: false } }} state="ready" interactive />);
    expect(screen.getByRole('button', { name: 'Adjuntar archivo' })).toBeDisabled();
  });

  it('records in the first supported WhatsApp mime type and sends it', async () => {
    recorderMimeSupport = ['audio/mp4', 'audio/aac'];
    recorderInstances = [];
    Object.defineProperty(globalThis, 'MediaRecorder', { configurable: true, value: FakeRecorder });
    const stream = { getTracks: () => { const track = { stop: vi.fn() }; tracks.push(track); return [track]; } };
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue(stream) } });
    vi.mocked(sendMedia).mockResolvedValue(result);
    render(<ConversationThread conversationId={9} data={thread} state="ready" interactive />);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Grabar audio' }));
    await waitFor(() => expect(recorderInstances).toHaveLength(1));
    expect(recorderInstances[0].mimeType).toBe('audio/mp4');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Detener y enviar audio' }));
    await waitFor(() => expect(sendMedia).toHaveBeenCalledWith(9, expect.objectContaining({ file: expect.objectContaining({ type: 'audio/mp4' }) })));
  });

  it('records in webm when the browser only offers what Chromium supports', async () => {
    recorderMimeSupport = ['audio/webm;codecs=opus'];
    recorderInstances = [];
    Object.defineProperty(globalThis, 'MediaRecorder', { configurable: true, value: FakeRecorder });
    const stream = { getTracks: () => { const track = { stop: vi.fn() }; tracks.push(track); return [track]; } };
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue(stream) } });
    vi.mocked(sendMedia).mockResolvedValue(result);
    render(<ConversationThread conversationId={9} data={thread} state="ready" interactive />);
    const record = screen.getByRole('button', { name: 'Grabar audio' });
    expect(record).toBeEnabled();
    await userEvent.setup().click(record);
    await waitFor(() => expect(recorderInstances).toHaveLength(1));
    expect(recorderInstances[0].mimeType).toBe('audio/webm;codecs=opus');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Detener y enviar audio' }));
    await waitFor(() => expect(sendMedia).toHaveBeenCalledWith(9, expect.objectContaining({ file: expect.objectContaining({ type: 'audio/webm;codecs=opus' }) })));
    const sent = vi.mocked(sendMedia).mock.calls[0][1].file;
    expect(sent.name).toMatch(/\.webm$/);
    expect(screen.queryByText(/grabación de audio no está disponible/i)).not.toBeInTheDocument();
  });

  it('cancels recording, releases microphone tracks, and sends nothing', async () => {
    recorderMimeSupport = ['audio/ogg;codecs=opus'];
    Object.defineProperty(globalThis, 'MediaRecorder', { configurable: true, value: FakeRecorder });
    const track = { stop: vi.fn() };
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) } });
    const user = userEvent.setup();
    render(<ConversationThread conversationId={9} data={thread} state="ready" interactive />);
    await user.click(screen.getByRole('button', { name: 'Grabar audio' }));
    await user.click(await screen.findByRole('button', { name: 'Cancelar grabación' }));
    expect(track.stop).toHaveBeenCalled();
    expect(sendMedia).not.toHaveBeenCalled();
  });

  it('explains that recording is unavailable when no accepted mime is supported', () => {
    recorderMimeSupport = [];
    Object.defineProperty(globalThis, 'MediaRecorder', { configurable: true, value: FakeRecorder });
    render(<ConversationThread data={thread} state="ready" interactive />);
    expect(screen.getByRole('button', { name: 'Grabar audio' })).toBeDisabled();
    expect(screen.getByText(/grabación de audio no está disponible/i)).toBeInTheDocument();
  });
});
