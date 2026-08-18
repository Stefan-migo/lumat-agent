/** Thin JSON fetch layer for the panel SPA (PDW-AUTH-1, PDW-AUTH-3, D4).
 *
 * Same-origin only: `credentials: 'include'` round-trips the HttpOnly session
 * cookie over the Vite proxy in dev and the nginx static host in prod. The
 * JSON-401 deps never issue redirects (D4), so the SPA never follows one to
 * the HTML login page (PDW-AUTH-1). No CORS (D1).
 */

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    let detail = raw.trim();
    try {
      const payload = JSON.parse(raw) as { detail?: unknown };
      if (typeof payload.detail === 'string') {
        detail = payload.detail;
      }
    } catch {
      // keep the raw text when the body is not JSON
    }
    throw new ApiError(res.status, detail || `${res.status} ${res.statusText}`.trim());
  }

  return (await res.json()) as T;
}
