import { afterEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

describe('App /me auth gate (T6.4)', () => {
  it('renders a loading state while /me is in flight', () => {
    stubMePending();
    render(<App />);
    expect(screen.getByText(/cargando|loading/i)).toBeInTheDocument();
  });

  it('renders AppShell after a 200 /me (PDW-AUTH-2)', async () => {
    stubMeOk();
    render(<App />);
    await waitFor(() =>
      expect(screen.getByText('Lumat Panel')).toBeInTheDocument(),
    );
    expect(screen.getByText('ana')).toBeInTheDocument();
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
    render(<App />);

    await waitFor(() => expect(screen.getByText(/no se pudo conectar|error/i)).toBeInTheDocument());

    // Second call succeeds → retry flips the SPA into the authed shell (PDW-AUTH-2)
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ username: 'vero', role: 'operador' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await user.click(screen.getByRole('button', { name: /reintentar|retry/i }));

    await waitFor(() => expect(screen.getByText('Lumat Panel')).toBeInTheDocument());
    expect(screen.getByText('vero')).toBeInTheDocument();
  });
});
