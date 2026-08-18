import { useCallback, useEffect, useState } from 'react';
import { apiFetch, ApiError } from './api';
import type { User } from './types';
import { AppShell } from './components/domain/AppShell';

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
  | { kind: 'anon' }
  | { kind: 'error'; detail: string };

export default function App() {
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

  useEffect(() => {
    void probe();
  }, [probe]);

  if (state.kind === 'loading') {
    return <p>Cargando…</p>;
  }

  if (state.kind === 'authed') {
    return <AppShell user={state.user} />;
  }

  if (state.kind === 'anon') {
    return (
      <main>
        <h1>Lumat Panel</h1>
        <p>Para continuar debes iniciar sesión.</p>
      </main>
    );
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
