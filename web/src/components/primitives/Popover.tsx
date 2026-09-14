import { useId, type ReactNode } from "react";
import "./primitives.css";

export type PopoverState = "default" | "loading" | "empty" | "error" | "disabled";

export interface PopoverProps {
  title: string;
  triggerLabel: string;
  children: ReactNode;
  state?: PopoverState;
}

/** Corporate Popover primitive (CST-PRIM-7): native Popover API ownership.
 *  The browser supplies toggle, Escape dismissal, top-layer placement and focus
 *  return. Anchor positioning is CSS enhancement; this component has no JS
 *  polyfill or dismissal handler. */
export function Popover({ title, triggerLabel, children, state = "default" }: PopoverProps) {
  const id = useId();
  const titleId = `${id}-title`;
  const disabled = state === "disabled";

  return (
    <div className="popover">
      <button
        type="button"
        className="popover__trigger"
        popoverTarget={id}
        disabled={disabled}
        aria-label={triggerLabel}
      >
        {triggerLabel}
      </button>
      <div id={id} popover="auto" role="dialog" aria-labelledby={titleId} className="popover__panel">
        <h2 id={titleId} className="popover__title">{title}</h2>
        {state === "loading" && <p role="status">Cargando</p>}
        {state === "empty" && <p role="status">No hay opciones disponibles</p>}
        {state === "error" && <p role="alert">No fue posible cargar las opciones</p>}
        {state === "default" && children}
      </div>
    </div>
  );
}
