import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Icon } from "../primitives/Icon";

/** Empty-state block emitting the tokenized `.empty-state` primitive. */
export interface EmptyStateProps {
  title: string;
  description?: string;
  /** Optional leading icon, shown above the title on the `dashed` variant. */
  icon?: LucideIcon;
  /** Optional call to action rendered below the copy. */
  action?: ReactNode;
  variant?: "default" | "dashed";
}

export function EmptyState({ title, description, icon, action, variant = "default" }: EmptyStateProps) {
  return (
    <div className={`empty-state${variant === "dashed" ? " empty-state--dashed" : ""}`}>
      {icon ? <span className="empty-state__icon"><Icon icon={icon} /></span> : null}
      <p className="empty-state__title">{title}</p>
      {description ? <p className="empty-state__description">{description}</p> : null}
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}
