import { Badge } from "./Badge";
import type { BadgeTone } from "./Badge";

export type Status = "bot" | "human" | "closed" | "pending" | "escalated";
export const statusTone: Record<Status, BadgeTone> = {
  bot: "neutral",
  human: "warning",
  closed: "success",
  pending: "warning",
  escalated: "danger",
};

export function StatusBadge({ status }: { status: Status }) {
  return <Badge tone={statusTone[status]}>{status}</Badge>;
}
