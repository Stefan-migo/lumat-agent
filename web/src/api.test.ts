import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, ApiError, postJson, listConversations, sendMessage } from './api';
import type { User } from './types';

describe('apiFetch', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('fetches with credentials:include and JSON and returns parsed data', async () => {
    const user: User = { username: 'admin', role: 'admin' };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(user), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await apiFetch<User>('/panel/api/me');
    expect(result).toEqual(user);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/panel/api/me',
      expect.objectContaining({
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      }),
    );
  });

  it('throws ApiError with status and detail from a non-2xx JSON body', async () => {
    const body = { detail: 'unauthorized' };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(body), { status: 401 }),
    );

    const promise = apiFetch('/panel/api/me');
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({
      status: 401,
      detail: 'unauthorized',
    });
  });

  it('falls back to a generic detail when the error body is not JSON', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response('Internal Server Error', { status: 500 }),
    );

    await expect(apiFetch('/panel/api/kpis')).rejects.toMatchObject({
      status: 500,
      detail: 'Internal Server Error',
    });
  });
});

describe('postJson', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('posts JSON with the session cookie and returns parsed data', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify({ ok: true, role: 'admin' }), { status: 200 }),
    );

    await expect(postJson('/panel/api/login', { username: 'ana', password: 'secret' })).resolves.toEqual({
      ok: true,
      role: 'admin',
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/panel/api/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ username: 'ana', password: 'secret' }),
        credentials: 'include',
      }),
    );
  });

  it('preserves the API error contract for failed POST requests', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Credenciales inválidas' }), { status: 401 }),
    );

    await expect(postJson('/panel/api/login', {})).rejects.toMatchObject({
      status: 401,
      detail: 'Credenciales inválidas',
    });
  });
});

describe('conversation API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('encodes production filters and mutation payloads', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ conversations: [] }), { status: 200 }));
    await listConversations({ state: 'human', responsible_id: 7 });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/conversations?state=human&responsible_id=7', expect.anything());

    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true, message: { id: 3 } }), { status: 200 }));
    await sendMessage(9, { text: 'Hola', request_id: 'req-1' });
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/conversations/9/messages', expect.objectContaining({ method: 'POST', body: JSON.stringify({ text: 'Hola', request_id: 'req-1' }) }));
  });

  it('keeps conflict and policy errors typed for callers', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ detail: 'stale' }), { status: 409 }));
    await expect(sendMessage(9, { text: 'Hola', request_id: 'req-2' })).rejects.toMatchObject({ status: 409, detail: 'stale' });
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ detail: 'window closed' }), { status: 422 }));
    await expect(sendMessage(9, { text: 'Hola', request_id: 'req-3' })).rejects.toMatchObject({ status: 422, detail: 'window closed' });
  });
});
