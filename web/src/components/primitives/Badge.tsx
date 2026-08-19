import type { ReactNode } from "react";
import "./primitives.css";

export type BadgeTone = "neutral" | "success" | "warning" | "danger";
export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}

export function Badge({
  tone = "neutral",
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`badge badge--${tone} ${className}`.trim()}
      data-tone={tone}
    >
      {children}
    </span>
  );
}
