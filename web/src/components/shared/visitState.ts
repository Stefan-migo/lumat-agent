import type { TechnicianVisitState } from '../../types';

/** S5/S9 — the field quick-action labels. They live here so the technician's
 *  actions card and the office semaphore never drift apart. */
export const QUICK_ACTION_LABELS: Record<TechnicianVisitState, string> = {
  en_route: 'Voy en camino',
  arrived: 'Llegué / estoy afuera',
};

/** S9 — how long ago the technician marked the state, for the office board.
 *  It separates "va en camino hace 2 min" from a state that has been sitting
 *  for 40 minutes with nothing closed. Minute resolution is the point, so
 *  seconds buy nothing. `null` when unset or in the future (clock skew).
 *
 *  Deliberately separate from `formatNotificationTime` (domain/PanelShell): that
 *  one is a standalone, capitalized notification stamp; this one is an inline,
 *  lowercase badge suffix. Reusing it would drag the panel shell into the agenda. */
export function fieldStateAge(stateAt: string | null | undefined, now: Date): string | null {
  if (!stateAt) return null;
  const elapsed = now.getTime() - new Date(stateAt).getTime();
  if (!Number.isFinite(elapsed) || elapsed < 0) return null;
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return 'hace menos de 1 min';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `hace ${hours} h` : `hace ${Math.floor(hours / 24)} d`;
}
