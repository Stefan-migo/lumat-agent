import type { Role } from "../../types";
import type { PanelView } from "./PanelShell";

/** Role → panel destinations (D1; task doc S1).
 *
 * The technician's unit of work is the visit, not the CRM: they get the agenda
 * and the assistant, plus notifications and their own profile. The operator is
 * the office surface; admin adds the administrative destinations. Centralising
 * the map here keeps the sidebar, the mobile tabs and the router in agreement —
 * hiding a destination in one surface and not the others is how a role leaks.
 */

const ALL_VIEWS: readonly PanelView[] = [
  "dashboard", "chat", "conversations", "clients", "agenda", "kb",
  "automation-rules", "settings", "users", "notifications", "push",
  "cases", "advanced-dashboard", "projects", "planning-sessions", "profile",
];

const ADMIN_ONLY: readonly PanelView[] = ["kb", "automation-rules", "settings", "users"];

/** The technician surface: agenda, assistant, notifications, profile. */
const TECNICO_VIEWS: readonly PanelView[] = ["agenda", "chat", "notifications", "profile"];

const ROLE_VIEWS: Record<Role, ReadonlySet<PanelView>> = {
  admin: new Set(ALL_VIEWS),
  operador: new Set(ALL_VIEWS.filter((view) => !ADMIN_ONLY.includes(view))),
  tecnico: new Set(TECNICO_VIEWS),
};

/** Views a role may open. Unknown roles fall back to the operator surface. */
export function viewsForRole(role: Role): ReadonlySet<PanelView> {
  return ROLE_VIEWS[role] ?? ROLE_VIEWS.operador;
}

/** Whether a role may open a view. */
export function canOpen(role: Role, view: PanelView): boolean {
  return viewsForRole(role).has(view);
}

/** Where a role lands when it opens a destination it may not see. */
export function defaultViewForRole(role: Role): PanelView {
  return role === "tecnico" ? "agenda" : "dashboard";
}

/** Mobile bottom-tab destinations, short and role-scoped. */
export function footerViewsForRole(role: Role): PanelView[] {
  if (role === "tecnico") return ["agenda", "chat", "notifications", "profile"];
  return ["dashboard", "conversations", "chat", "agenda", "clients"];
}
