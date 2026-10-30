import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, ApiError, postJson, deleteKbDocument, deleteUser, archiveCase, unarchiveCase, getClientFicha, listConversations, sendMessage, sendMedia, acknowledgeCase, takeConversation, listChatThreads, fetchClients, createCustomer, updateCustomerProfile, updateCustomerConsent, archiveCustomer, unarchiveCustomer, createChatThread, createProject, fetchMe, updateMe, changePassword, getAdminUser, updateAdminUser, unlockUser, listProjectFiles, uploadProjectFile, downloadProjectFile, downloadAssistantArtifact, deleteProjectFile, moveProjectFile, listProjectFolders, createProjectFolder, renameProjectFolder, deleteProjectFolder, listGlobalSkills, listAutomationRecipes, listAutomationInstallations, createAutomationInstallation, updateAutomationInstallation, enableAutomationInstallation, disableAutomationInstallation, listProjectAgents, setChatThreadProject, attachProjectFileToThread, deleteThreadAttachment, threadAttachmentContentUrl, getTechnicianSchedule, saveTechnicianSchedule, getModelApiKeyStatus, saveModelApiKey, deleteModelApiKey } from './api';
import * as apiModule from './api';
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

describe('model API key contracts', () => {
  afterEach(() => vi.restoreAllMocks());

  it('gets status and posts a key with the typed validation response', async () => {
    const status = { configured: true, source: 'panel', masked: '…1234' } as const;
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({ model_api_key: status }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, validation: 'no_balance', model_api_key: status }), { status: 200 }));
    await expect(getModelApiKeyStatus()).resolves.toEqual(status);
    await expect(saveModelApiKey('sk-test-key')).resolves.toEqual({ ok: true, validation: 'no_balance', model_api_key: status });
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/settings/model_api_key', expect.objectContaining({ method: 'POST', body: '{"api_key":"sk-test-key"}' }));
  });

  it('deletes the panel key with DELETE', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true, model_api_key: { configured: false, source: 'none', masked: '' } }), { status: 200 }));
    await deleteModelApiKey();
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/settings/model_api_key', expect.objectContaining({ method: 'DELETE' }));
  });
});

describe('KB API contracts', () => {
  it('deletes a KB document with DELETE', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true, doc: {} }), { status: 200 }));
    await deleteKbDocument(42);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/kb/42', expect.objectContaining({ method: 'DELETE' }));
  });
});

describe('user API contracts', () => {
  it('deletes a panel user with DELETE', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await deleteUser(42);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/users/42', expect.objectContaining({ method: 'DELETE' }));
  });
});

describe('case archive API contracts', () => {
  it('posts archive and unarchive and optionally includes archived ficha cases', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await archiveCase(42);
    await unarchiveCase(42);
    await getClientFicha(7);
    await getClientFicha(7, true);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/panel/api/cases/42/archive', expect.objectContaining({ method: 'POST' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/cases/42/unarchive', expect.objectContaining({ method: 'POST' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, '/panel/api/clients/7', expect.anything());
    expect(globalThis.fetch).toHaveBeenNthCalledWith(4, '/panel/api/clients/7?include_archived_cases=true', expect.anything());
  });
});

describe('client API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('adds archived clients to the list without requesting archived-only results', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ clients: [] }), { status: 200 }));
    await fetchClients({ includeArchived: true, query: 'Ana Fuentes' });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/clients?q=Ana+Fuentes&include_archived=true', expect.anything());
    expect(globalThis.fetch).not.toHaveBeenCalledWith(expect.stringContaining('only_archived'), expect.anything());
  });

  it('sends consent and creation sort filters to the clients endpoint', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ clients: [] }), { status: 200 }));
    await fetchClients({ consent: false, sort: 'created_asc' });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/clients?consent=false&sort=created_asc', expect.anything());
  });

  it('requests only archived clients independently of includeArchived', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ clients: [] }), { status: 200 }));
    await fetchClients({ onlyArchived: true, includeArchived: true });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/clients?include_archived=true&only_archived=true', expect.anything());
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

describe('overdue appointment API contracts', () => {
  afterEach(() => vi.restoreAllMocks());

  it('gets the overdue agenda projection from the operator endpoint', async () => {
    const payload = { appointments: [{ id: 17, customer_name: 'Camila Soto', service: 'Mantención' }] };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

    const listOverdue = (apiModule as Record<string, unknown>).listOverdueAppointments as () => Promise<unknown>;
    expect(listOverdue).toBeTypeOf('function');
    await expect(listOverdue()).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/appointments/overdue', expect.objectContaining({ credentials: 'include' }));
  });

  it('posts the selected ids and one explicit outcome to bulk close', async () => {
    const payload = { closed: 2, failed: 0, results: [{ id: 17, ok: true, outcome: 'completed', error: null }] };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

    const bulkClose = (apiModule as Record<string, unknown>).bulkCloseAppointments as (ids: number[], outcome: 'completed' | 'no_show') => Promise<unknown>;
    expect(bulkClose).toBeTypeOf('function');
    await expect(bulkClose([17, 23], 'completed')).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/appointments/bulk-close', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ appointment_ids: [17, 23], outcome: 'completed', reason: null }),
      credentials: 'include',
    }));
  });
});

describe('technician schedule API contracts', () => {
  afterEach(() => vi.restoreAllMocks());

  it('gets and replaces a technician weekly schedule using the typed routes', async () => {
    const response = { technician_id: 12, schedule: [{ weekday: 1, opens_at: '09:00:00', closes_at: '18:00:00' }] };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify(response), { status: 200 }));

    await expect(getTechnicianSchedule(12)).resolves.toEqual(response);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/panel/api/technicians/12/schedule', expect.objectContaining({ credentials: 'include' }));
    await saveTechnicianSchedule(12, [{ weekday: 1, opens_at: '09:00', closes_at: '18:00' }]);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/technicians/12/schedule', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ schedule: [{ weekday: 1, opens_at: '09:00', closes_at: '18:00' }] }) }));
  });

  it('allows saving an empty schedule to clear availability', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ technician_id: 12, schedule: [] }), { status: 200 }));

    await saveTechnicianSchedule(12, []);

    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/technicians/12/schedule', expect.objectContaining({ method: 'PUT', body: '{"schedule":[]}' }));
  });
});

describe('global skills API contract', () => {
  afterEach(() => vi.restoreAllMocks());

  it('lists the read-only global skills catalog', async () => {
    const payload = { skills: [{ name: 'research', description: 'Research carefully', scope: 'global' as const }] };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    await expect(listGlobalSkills()).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/skills', expect.objectContaining({ credentials: 'include' }));
  });
});

describe('automation recipe API contracts', () => {
  afterEach(() => vi.restoreAllMocks());
  it('uses catalog and installation endpoints with expected verbs and payloads', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ recipes: [], installations: [], installation: {} }), { status: 200 }));
    await listAutomationRecipes();
    await listAutomationInstallations();
    await createAutomationInstallation('recipe-id', { channel: 'email' });
    await updateAutomationInstallation(7, { channel: 'whatsapp' });
    await enableAutomationInstallation(7);
    await disableAutomationInstallation(7);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/panel/api/automation-recipes', expect.objectContaining({ credentials: 'include' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/automation-installations', expect.objectContaining({ credentials: 'include' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, '/panel/api/automation-installations', expect.objectContaining({ method: 'POST', body: '{"recipe_id":"recipe-id","parameters":{"channel":"email"}}' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(4, '/panel/api/automation-installations/7', expect.objectContaining({ method: 'PATCH', body: '{"parameters":{"channel":"whatsapp"}}' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(5, '/panel/api/automation-installations/7/enable', expect.objectContaining({ method: 'POST' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(6, '/panel/api/automation-installations/7/disable', expect.objectContaining({ method: 'POST' }));
  });
});

describe('project agents API contract', () => {
  afterEach(() => vi.restoreAllMocks());

  it('requests project agents using an encoded slug', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ agents: [], latest_run: null }), { status: 200 })));

    await listProjectAgents('project / one');

    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/project%20%2F%20one/agents', expect.objectContaining({ credentials: 'include' }));
  });
});

describe('self-profile API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ id: 1, username: 'ana', role: 'admin', email: null, name: null, phone: null, position: null, user: { name: null, phone: null }, ok: true }), { status: 200 })); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('gets self profile, patches only name and phone, and posts the exact password fields', async () => {
    await fetchMe();
    await updateMe({ name: null, phone: '123' });
    await changePassword({ current_password: 'current', new_password: 'new-password' });
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/panel/api/me', expect.objectContaining({ credentials: 'include' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/panel/api/me', expect.objectContaining({ method: 'PATCH', body: '{"name":null,"phone":"123"}' }));
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, '/panel/api/me/password', expect.objectContaining({ method: 'POST', body: '{"current_password":"current","new_password":"new-password"}' }));
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

    vi.mocked(globalThis.fetch).mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, message: { id: 4 } }), { status: 200 }));
    const file = new File(['image'], 'photo.png', { type: 'image/png' });
    await sendMedia(9, { file, requestId: 'media-req', caption: 'Foto' });
    const form = vi.mocked(globalThis.fetch).mock.calls[2][1]?.body as FormData;
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/conversations/9/media', expect.objectContaining({ method: 'POST', body: expect.any(FormData) }));
    expect(form.get('file')).toBe(file);
    expect(form.get('request_id')).toBe('media-req');
    expect(form.get('caption')).toBe('Foto');
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

describe('admin user ficha API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('uses the typed profile and unlock endpoints', async () => {
    const response = { user: { id: 8, username: 'carlos', role: 'tecnico', active: true, email: null, name: 'Carlos', phone: null, position: null, locked_until: null, failed_logins: 0 } };
    vi.mocked(globalThis.fetch).mockImplementation(async () => new Response(JSON.stringify(response), { status: 200 }));
    await expect(getAdminUser(8)).resolves.toEqual(response);
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/users/8', expect.anything());
    await updateAdminUser(8, { name: null, phone: '123', email: null, position: 'Técnico' });
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/users/8', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: null, phone: '123', email: null, position: 'Técnico' }) }));
    await unlockUser(8);
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/users/8/unlock', expect.objectContaining({ method: 'POST' }));
  });
});

describe('project file and artifact API contracts', () => {
  beforeEach(() => { globalThis.fetch = vi.fn(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('lists project files from the encoded project URL', async () => {
    const payload = { files: [{ id: 1, project_id: 3, filename: 'guide.pdf' }] };
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    await expect(listProjectFiles('my project')).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/my%20project/files', expect.anything());
  });

  it('uploads a project file as FormData', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ file: {} }), { status: 201 }));
    await uploadProjectFile('ops', new File(['contents'], 'notes.txt'));
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/ops/files', expect.objectContaining({ method: 'POST', body: expect.any(FormData) }));
    expect(vi.mocked(globalThis.fetch).mock.calls[0][1]?.body).toBeInstanceOf(FormData);
  });

  it('appends the target folder when uploading into one', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ file: {} }), { status: 201 }));
    await uploadProjectFile('ops', new File(['contents'], 'notes.txt'), 12);
    const body = vi.mocked(globalThis.fetch).mock.calls[0][1]?.body as FormData;
    expect(body.get('folder_id')).toBe('12');
  });

  it('deletes a project file without a response body', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(null, { status: 204 }));
    await expect(deleteProjectFile('ops', 7)).resolves.toBeUndefined();
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/ops/files/7', expect.objectContaining({ method: 'DELETE' }));
  });

  it('moves a project file into a folder (or back to the root)', async () => {
    vi.mocked(globalThis.fetch).mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ file: {} }), { status: 200 })));
    await moveProjectFile('ops', 7, 12);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/ops/files/7', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ folder_id: 12 }) }));
    await moveProjectFile('ops', 7, null);
    expect(globalThis.fetch).toHaveBeenLastCalledWith('/panel/api/projects/ops/files/7', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ folder_id: null }) }));
  });

  it('lists project folders from the encoded project URL', async () => {
    const payload = { folders: [{ id: 1, project_id: 3, parent_id: null, name: 'Diseño', created_at: null }] };
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    await expect(listProjectFolders('my project')).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/my%20project/folders', expect.anything());
  });

  it('creates a folder with an optional parent', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ folder: {} }), { status: 201 }));
    await createProjectFolder('ops', { name: 'Reportes', parent_id: 4 });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/ops/folders', expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'Reportes', parent_id: 4 }) }));
  });

  it('renames a folder by PATCHing its name', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ folder: {} }), { status: 200 }));
    await renameProjectFolder('ops', 9, 'Operación');
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/ops/folders/9', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: 'Operación' }) }));
  });

  it('deletes a folder recursively without a response body', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(null, { status: 204 }));
    await expect(deleteProjectFolder('ops', 9)).resolves.toBeUndefined();
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects/ops/folders/9', expect.objectContaining({ method: 'DELETE' }));
  });

  it.each([
    ['project file', () => downloadProjectFile('ops', 7, 'brief.pdf'), '/panel/api/projects/ops/files/7/download'],
    ['assistant artifact', () => downloadAssistantArtifact(12, 8, 'report.csv'), '/panel/api/chat/threads/12/artifacts/8/download'],
  ])('downloads a %s through the binary endpoint', async (_name, download, expectedUrl) => {
    const blob = new Blob(['binary']);
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(blob, { status: 200 }));
    const createObjectURL = vi.fn().mockReturnValue('blob:test-download');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    await download();

    expect(globalThis.fetch).toHaveBeenCalledWith(expectedUrl, { credentials: 'include' });
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test-download');
  });

  it('throws ApiError for a failed binary download', async () => {
    vi.mocked(globalThis.fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'missing file' }), { status: 404 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'missing file' }), { status: 404 }));
    await expect(downloadProjectFile('ops', 7, 'brief.pdf')).rejects.toBeInstanceOf(ApiError);
    await expect(downloadAssistantArtifact(12, 8, 'report.csv')).rejects.toMatchObject({ status: 404, detail: 'missing file' });
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

  it('deletes an attachment and builds its same-origin inline content URL', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await expect(deleteThreadAttachment(12, 8)).resolves.toBeUndefined();

    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/chat/threads/12/attachments/8', expect.objectContaining({ method: 'DELETE' }));
    expect(threadAttachmentContentUrl(12, 8)).toBe('/panel/api/chat/threads/12/attachments/8/content');
  });

  it('preserves the typed navigator fields returned by the API', async () => {
    const payload = { threads: [{ id: 4, title: 'Investigate outage', created_at: null, updated_at: null, run_status: null, approval_status: null }] };
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

    await expect(listChatThreads(1)).resolves.toEqual(payload);
  });

  it('always creates a chat thread with an explicit project', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ thread: {}, messages: [] }), { status: 201 }));
    await createChatThread('ops');
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/chat/threads', expect.objectContaining({ method: 'POST', body: JSON.stringify({ proyecto: 'ops' }) }));
  });

  it('changes a thread project with the PATCH contract', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ thread: {} }), { status: 200 }));
    await setChatThreadProject(12, 'ops');
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/chat/threads/12', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ proyecto: 'ops' }) }));
  });

  it('attaches a project file with the project file identifier', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ attachment: {} }), { status: 201 }));
    await attachProjectFileToThread(12, 34);
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/chat/threads/12/attachments/from-project', expect.objectContaining({ method: 'POST', body: JSON.stringify({ project_file_id: 34 }) }));
  });

  it('creates projects with the bounded API payload', async () => {
    const project = { id: 1, slug: 'ops', name: 'Operations', purpose: 'Run operations', status: 'active', created_at: null, updated_at: null };
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response(JSON.stringify({ project }), { status: 201 }));
    await expect(createProject({ slug: 'ops', name: 'Operations', purpose: 'Run operations' })).resolves.toEqual({ project });
    expect(globalThis.fetch).toHaveBeenCalledWith('/panel/api/projects', expect.objectContaining({ method: 'POST', body: JSON.stringify({ slug: 'ops', name: 'Operations', purpose: 'Run operations' }) }));
  });
});
