import { afterEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './app';

// App mounts → GET /panel/api/me via apiFetch (native fetch, credentials:include).
// All three SPA auth states are exercised by stubbing global fetch (PDW-AUTH-1/2).
afterEach(() => {
  vi.unstubAllGlobals();
});

function stubMeOk() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ username: 'ana', role: 'admin' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })),
  );
}

function stubMeUnauthorized() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ detail: 'unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    })),
  );
}

function stubMePending() {
  // A fetch that never settles keeps /me in flight so the loading state stays
  // the current render (avoids an un-act'ed state update in the loader test).
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
}

// PanelShell renders three brand nodes (desktop sidebar, mobile bar, closed
// drawer), so app-name/username assertions are scoped to the sidebar.
function sidebar(container: HTMLElement) {
  return within(container.querySelector('.panel-shell__sidebar') as HTMLElement);
}

describe('App /me auth gate (T6.4)', () => {
  it('renders a loading state while /me is in flight', () => {
    stubMePending();
    render(<App />);
    expect(screen.getByText(/cargando|loading/i)).toBeInTheDocument();
  });

  it('renders AppShell after a 200 /me (PDW-AUTH-2)', async () => {
    stubMeOk();
    const { container } = render(<App />);
    await waitFor(() =>
      expect(container.querySelector('.panel-shell__sidebar .panel-shell__brand-image')).toBeInTheDocument(),
    );
    expect(sidebar(container).getByText('ana')).toBeInTheDocument();
  });

  it('renders the sign-in placeholder after a 401 /me (PDW-AUTH-1)', async () => {
    stubMeUnauthorized();
    render(<App />);
    await waitFor(() =>
      expect(screen.getByText(/iniciar sesi[oó]n|sign in required/i)).toBeInTheDocument(),
    );
  });

  it('renders an error with retry after a network failure, and retry recovers', async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch'));

    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await waitFor(() => expect(screen.getByText(/no se pudo conectar|error/i)).toBeInTheDocument());

    // Second call succeeds → retry flips the SPA into the authed shell (PDW-AUTH-2)
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ username: 'vero', role: 'operador' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await user.click(screen.getByRole('button', { name: /reintentar|retry/i }));

    await waitFor(() => expect(container.querySelector('.panel-shell__sidebar .panel-shell__brand-image')).toBeInTheDocument());
    expect(sidebar(container).getByText('vero')).toBeInTheDocument();
  });

  it('logs in successfully and renders the returned role', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'unauthorized' }), { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, role: 'admin' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ username: 'ana', role: 'admin' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await user.type(await screen.findByLabelText(/usuario/i), 'ana');
    await user.type(screen.getByLabelText(/contraseña/i), 'secret');
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => expect(sidebar(container).getByText('ana')).toBeInTheDocument());
    expect(sidebar(container).getByText('Administrador')).toBeInTheDocument();
  });

  it('keeps the username and shows a generic error for invalid or locked login', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'unauthorized' }), { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'account locked' }), { status: 401 }));
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    render(<App />);

    const username = await screen.findByLabelText(/usuario/i);
    await user.type(username, 'ana');
    await user.type(screen.getByLabelText(/contraseña/i), 'secret');
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/cuenta bloqueada/i));
    expect((screen.getByLabelText(/usuario/i) as HTMLInputElement).value).toBe('ana');
    expect(screen.getByRole('alert')).not.toHaveTextContent(/no existe|no encontrado/i);
  });

  it('returns to the login gate after logout', async () => {
    // Dispatch by URL: the authed shell fires mount fetches (notifications,
    // active threads, dashboard) whose order is an implementation detail, so an
    // ordered mock chain would leave logout without a response and reject.
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input), 'http://localhost').pathname;
      if (path.endsWith('/panel/api/me')) {
        return new Response(JSON.stringify({ username: 'ana', role: 'admin' }), { status: 200 });
      }
      if (path.endsWith('/panel/api/notifications')) {
        return new Response(JSON.stringify({ notifications: [] }), { status: 200 });
      }
      if (path.endsWith('/panel/api/conversations')) {
        return new Response(JSON.stringify({ conversations: [] }), { status: 200 });
      }
      if (path.endsWith('/panel/api/logout')) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      return new Response(JSON.stringify({ contacts: 0, motivos: [], derived: 0, visit_requests: 0, window_days: 7, window_start: '2026-08-25' }), { status: 200 });
    });
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await waitFor(() => expect(sidebar(container).getByText('ana')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    await user.click(within(screen.getByRole('dialog', { name: 'Navegación' })).getByRole('button', { name: /cerrar sesión/i }));

    expect(await screen.findByLabelText(/usuario/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith('/panel/api/logout', expect.objectContaining({ method: 'POST' }));
  });
});
