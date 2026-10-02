import { Badge } from "./Badge";
import type { BadgeTone } from "./Badge";
import { conversationLabel } from "../shared/toneMaps";

export type Status = "bot" | "human" | "closed" | "pending" | "escalated";
export const statusTone: Record<Status, BadgeTone> = {
  bot: "neutral",
  human: "warning",
  closed: "success",
  pending: "warning",
  escalated: "danger",
};

export interface StatusBadgeProps {
  status: Status;
  /** Approved label (Spanish) rendered over the raw state (DS-UI-LABELS).
   *  Defaults to the per-domain map via `conversationLabel`. */
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return <Badge tone={statusTone[status]} className="status-badge"><span className="status-badge__dot" aria-hidden="true" />{label ?? conversationLabel(status)}</Badge>;
}
