import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Icon } from "./Icon";
import "./primitives.css";

export interface HelpPanelProps {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
  tone?: "soft" | "info";
}

export function HelpPanel({ icon, title, children, tone = "soft" }: HelpPanelProps) {
  return (
    <aside className={`help-panel help-panel--${tone}`}>
      <header className="help-panel__header">
        <Icon icon={icon} />
        <h2 className="help-panel__title">{title}</h2>
      </header>
      <div className="help-panel__body">{children}</div>
    </aside>
  );
}
