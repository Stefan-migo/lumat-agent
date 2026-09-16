import type { ButtonHTMLAttributes, ReactNode, MouseEvent } from "react";
import "./primitives.css";

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> {
  /** Visual variant; colors come from tokens only (PDW-TKN-2). */
  variant?: "primary" | "secondary" | "tertiary";
  /** When provided, renders an `<a>` instead of a `<button>` (e.g. CSV links). */
  href?: string;
  /** Render target interaction type. `button` by default; ignored when `href` is set. */
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  children: ReactNode;
  className?: string;
  onClick?: (e: MouseEvent<HTMLButtonElement | HTMLAnchorElement>) => void;
}

/** Primary bulk/emphasis button; toggles to an anchor when `href` is given. */
export function Button({
  variant = "primary",
  href,
  type = "button",
  disabled = false,
  children,
  className = "",
  onClick,
}: ButtonProps) {
  const classes = ["btn", `btn--${variant}`, className]
    .filter(Boolean)
    .join(" ");

  if (href !== undefined) {
    // CSV export links and other navigation stay plain anchors (PDW-TST-3):
    // a disabled link is not a real HTML concept, so disabled is dropped here.
    return (
      <a
        className={classes}
        href={href}
        aria-disabled={disabled || undefined}
        onClick={onClick}
      >
        {children}
      </a>
    );
  }

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
