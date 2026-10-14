import type { Role } from "../../types";
import type { PanelView } from "./PanelShell";

/** Role → panel destinations (D1; task doc S1).
 *
 * This file owns ONLY the technician restriction. The administrative
 * destinations live with the navigation they belong to
 * (`NAVIGATION[].adminOnly`, exposed as `isAdminOnlyView`) so a destination
 * another branch marks admin-only is respected without editing this file —
 * one source of truth, never two lists that can drift.
 */

/** The technician surface: agenda, assistant, notifications, profile. */
const TECNICO_VIEWS: ReadonlySet<PanelView> = new Set(["agenda", "chat", "notifications", "profile"]);

/** Whether a role may open a view. The technician is the only restricted role;
 *  admin/operador visibility of administrative destinations is decided by the
 *  navigation's own `adminOnly` flag. */
export function canOpen(role: Role, view: PanelView): boolean {
  return role === "tecnico" ? TECNICO_VIEWS.has(view) : true;
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
