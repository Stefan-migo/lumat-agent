import type { UserRef } from "../../../../types";

/** Canonical assignee UserRef mock matching to_user_dict() (R2; design D3).
 *  Single source of truth for panel assignee rows — cases.ts re-exports these
 *  same rows so responsible_id lookups stay consistent across pages. Ids
 *  7/8/9 mirror the historical cases.ts users (admin/karla/manuel). */
export const users: UserRef[] = [
  { id: 7, username: "admin" },
  { id: 8, username: "karla" },
  { id: 9, username: "manuel" },
];
