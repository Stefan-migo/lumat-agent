import type { LucideIcon } from "lucide-react";
import "./primitives.css";

export type IconSize = "sm" | "md" | "lg";

export interface IconProps {
  icon: LucideIcon;
  size?: IconSize;
  className?: string;
}

export function Icon({ icon: Glyph, size = "md", className = "" }: IconProps) {
  return (
    <Glyph
      aria-hidden="true"
      className={`icon icon--${size} ${className}`.trim()}
    />
  );
}
