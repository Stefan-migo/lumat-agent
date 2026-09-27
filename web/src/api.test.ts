import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, ApiError, postJson, listConversations, sendMessage, acknowledgeCase, takeConversation, listPlanningSessions, getPlanningSession, openPlanningSession, closePlanningSession, reopenPlanningSession, listChatThreads, fetchClients, createCustomer, updateCustomerProfile, updateCustomerConsent, archiveCustomer, unarchiveCustomer } from './api';
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

  it('preserves structured conflict detail additively', async () => {
    const detail = { code: 'phone_exists', message: 'Phone exists', customer_id: 42 };
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ detail }), { status: 409 }));

    await expect(apiFetch('/panel/api/clients')).rejects.toMatchObject({
      status: 409,
      detail: JSON.stringify({ detail }),
      structuredDetail: detail,
    });
  });
});

describe('client API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('lists clients with encoded search and archive filters', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ clients: [] }), { status: 200 }));
    await fetchClients({ includeArchived: true, query: 'Ana Fuentes' });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/clients?q=Ana+Fuentes&include_archived=true', expect.anything());
  });

  it('uses the customer CRUD routes and payloads', async () => {
    vi.mocked(globalThis.fetch).mockImplementation(async () => new Response(JSON.stringify({ customer: {} }), { status: 200 }));
    await createCustomer({ phone: '+56912345678' });
    await updateCustomerProfile(4, { name: 'Ana' });
    await archiveCustomer(4);
    await unarchiveCustomer(4);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/panel/api/clients', expect.objectContaining({ method: 'POST', body: JSON.stringify({ phone: '+56912345678' }) }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/clients/4', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: 'Ana' }) }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, '/panel/api/clients/4/archive', expect.objectContaining({ method: 'POST' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(4, '/panel/api/clients/4/unarchive', expect.objectContaining({ method: 'POST' }));
  });

  it('posts consent updates to the customer consent route', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ customer: {} }), { status: 200 }));
    await updateCustomerConsent(4, true);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/clients/4/consent', expect.objectContaining({ method: 'POST', body: JSON.stringify({ consent: true }) }));
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

  it('requests the typed queue envelope with search and offset pagination', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0, offset: 20, limit: 20, counts: { all: 0, human: 0, emergency: 0, case: 0, closed: 0 } }), { status: 200 }));
    await listConversations({ q: 'heater & pipe', limit: 20, offset: 20 });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/conversations?q=heater+%26+pipe&limit=20&offset=20', expect.anything());
  });

  it('exposes queue quick actions as typed mutations', async () => {
    vi.mocked(globalThis.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, conversation: {} }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, case: {} }), { status: 200 }));
    await takeConversation(9, 2);
    await acknowledgeCase(12);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/panel/api/conversations/9/state', expect.objectContaining({ method: 'POST', body: expect.stringContaining('"state":"human"') }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/cases/12/ack', expect.objectContaining({ method: 'POST' }));
  });

  it('keeps conflict and policy errors typed for callers', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ detail: 'stale' }), { status: 409 }));
    await expect(sendMessage(9, { text: 'Hola', request_id: 'req-2' })).rejects.toMatchObject({ status: 409, detail: 'stale' });
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ detail: 'window closed' }), { status: 422 }));
    await expect(sendMessage(9, { text: 'Hola', request_id: 'req-3' })).rejects.toMatchObject({ status: 422, detail: 'window closed' });
  });
});

describe('planning session API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });
  it('uses the authenticated planning lifecycle endpoints', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ sessions: [] }), { status: 200 }));
    await listPlanningSessions();
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/planning/sessions', expect.anything());
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ session: {}, thread_id: 8 }), { status: 201 }));
    await openPlanningSession('Budget review');
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/planning/sessions', expect.objectContaining({ method: 'POST', body: JSON.stringify({ topic: 'Budget review' }) }));
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ session: {}, thread: {}, decisions: [], report: null }), { status: 200 }));
    await getPlanningSession('budget-review-8');
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/planning/sessions/budget-review-8', expect.anything());
  });
  it('supports close and reopen lifecycle calls', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ session: {}, report: {}, handoff: {} }), { status: 200 }));
    await closePlanningSession('budget-review-8');
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/planning/sessions/budget-review-8/close', expect.objectContaining({ method: 'POST' }));
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ session: {}, thread_id: 8 }), { status: 200 }));
    await reopenPlanningSession('budget-review-8');
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/planning/sessions/budget-review-8/reopen', expect.objectContaining({ method: 'POST' }));
  });
});

describe('internal chat thread API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('requests the bounded typed thread list', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ threads: [] }), { status: 200 }));

    await listChatThreads(12);

    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/chat/threads?limit=12', expect.anything());
  });

  it('preserves the typed navigator fields returned by the API', async () => {
    const payload = { threads: [{ id: 4, title: 'Investigate outage', created_at: null, updated_at: null, run_status: null, approval_status: null }] };
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

    await expect(listChatThreads(1)).resolves.toEqual(payload);
  });
});
