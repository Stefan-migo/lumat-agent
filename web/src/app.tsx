import { useCallback, useEffect, useState } from 'react';
import { apiFetch, ApiError, fetchMe, postJson } from './api';
import type { LoginResponse, User } from './types';
import { AppShell } from './components/domain/AppShell';
import { LoginAuth } from './components/pages/LoginAuth';
import { ToastProvider } from './components/primitives/Toast';

/** Auth gate for the panel SPA (B6/T6.4; PDW-AUTH-1/2, D4).
 *
 * On mount: GET /panel/api/me (same-origin, credentials cookie).
 *   200       → authenticated → AppShell (role-gated nav).
 *   401 JSON  → unauthenticated → inline "sign in required" stub. LoginForm
 *               replaces it in T11.1 (B11).
 *   network   → EmptyState-with-retry equivalent (inline until the EmptyState
 *               primitive lands in T10.1); the retry re-runs the /me probe.
 */

type GateState =
  | { kind: 'loading' }
  | { kind: 'authed'; user: User }
  | { kind: 'anon'; error?: string }
  | { kind: 'error'; detail: string };

export default function App() {
  return (
    <ToastProvider>
      <AppGate />
    </ToastProvider>
  );
}

function AppGate() {
  const [state, setState] = useState<GateState>({ kind: 'loading' });

  const probe = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      const user = await apiFetch<User>('/panel/api/me');
      setState({ kind: 'authed', user });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setState({ kind: 'anon' });
      } else {
        const detail = e instanceof Error ? e.message : String(e);
        setState({ kind: 'error', detail });
      }
    }
  }, []);

  const login = async ({ username, password }: { username: string; password: string }) => {
    setState({ kind: 'anon' });
    try {
      const result = await postJson<LoginResponse>('/panel/api/login', { username, password });
      const user: User = { id: result.id, username, role: result.role };
      setState({ kind: 'authed', user });
      void fetchMe().then((profile) => setState({ kind: 'authed', user: { ...user, name: profile.name } })).catch(() => {});
    } catch (e) {
      const detail = e instanceof ApiError ? e.detail.toLowerCase() : '';
      setState({ kind: 'anon', error: detail.includes('locked') ? 'Cuenta bloqueada. Intenta más tarde.' : 'Credenciales inválidas' });
    }
  };

  const logout = async () => {
    await postJson('/panel/api/logout');
    setState({ kind: 'anon' });
  };

  useEffect(() => {
    void probe();
  }, [probe]);

  if (state.kind === 'loading') {
    return <p>Cargando…</p>;
  }

  if (state.kind === 'authed') {
    return <AppShell user={state.user} onLogout={logout} />;
  }

  if (state.kind === 'anon') {
    return <LoginAuth error={state.error} onSubmit={login} />;
  }

  return (
    <main role="alert">
      <h1>Lumat Panel</h1>
      <p>No se pudo conectar con el servidor: {state.detail}</p>
      <button type="button" onClick={() => void probe()}>
        Reintentar
      </button>
    </main>
  );
}
