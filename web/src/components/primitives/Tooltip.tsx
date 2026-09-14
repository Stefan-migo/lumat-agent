import { useId, useRef, useState, type ReactNode } from "react";
import "./primitives.css";

export interface TooltipProps {
  label: string;
  children: ReactNode;
  disabled?: boolean;
}

/** Corporate Tooltip primitive (CST-PRIM-7): a native `popover="hint"`
 *  connected with `aria-describedby`. Hover and keyboard focus are explicit
 *  trigger paths; the platform owns the top layer and native popover model. */
export function Tooltip({ label, children, disabled = false }: TooltipProps) {
  const id = useId();
  const hintRef = useRef<HTMLSpanElement>(null);
  const [visible, setVisible] = useState(false);

  /** ponytail: the Popover API is a platform feature, not a polyfill target.
   *  jsdom and older engines do not implement `showPopover`, so the call is
   *  feature-guarded; `aria-hidden` is still driven by state so unsupported
   *  engines degrade honestly instead of throwing. */
  const setHint = (next: boolean) => {
    setVisible(next);
    const hint = hintRef.current;
    if (!hint || typeof hint.showPopover !== "function") return;
    if (next) hint.showPopover();
    else hint.hidePopover();
  };

  return (
    <span className="tooltip">
      <button
        type="button"
        className="tooltip__trigger"
        aria-describedby={disabled ? undefined : id}
        disabled={disabled}
        onFocus={() => setHint(true)}
        onBlur={() => setHint(false)}
        onMouseEnter={() => setHint(true)}
        onMouseLeave={() => setHint(false)}
      >
        {children}
      </button>
      <span
        ref={hintRef}
        id={id}
        popover="hint"
        role="tooltip"
        aria-hidden={disabled || !visible}
        className="tooltip__content"
      >
        {label}
      </span>
    </span>
  );
}
