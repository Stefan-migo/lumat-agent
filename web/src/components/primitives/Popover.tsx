import { useId, type CSSProperties, type ReactNode } from "react";
import "./primitives.css";

export type PopoverState = "default" | "loading" | "empty" | "error" | "disabled";

export interface PopoverProps {
  title: string;
  triggerLabel: string;
  trigger?: ReactNode;
  children: ReactNode;
  state?: PopoverState;
  hideTitle?: boolean;
  dismissible?: boolean;
}

/** Corporate Popover primitive (CST-PRIM-7): native Popover API ownership.
 *  The browser supplies toggle, Escape dismissal, top-layer placement and focus
 *  return. Anchor positioning is CSS enhancement; this component has no JS
 *  polyfill or dismissal handler. */
export function Popover({ title, triggerLabel, trigger, children, state = "default", hideTitle = false, dismissible = false }: PopoverProps) {
  const id = useId();
  const titleId = `${id}-title`;
  const anchorName = `--pop-anchor-${id.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const disabled = state === "disabled";

  return (
    <div className="popover" style={{ "--pop-anchor": anchorName } as CSSProperties}>
      <button
        type="button"
        className="popover__trigger"
        popoverTarget={id}
        disabled={disabled}
        aria-label={triggerLabel}
      >
        {trigger ?? triggerLabel}
      </button>
      <div id={id} popover="auto" role="dialog" aria-labelledby={titleId} className="popover__panel">
        <div className={`popover__header${hideTitle && dismissible ? " popover__header--hidden-title-dismissible" : ""}`}>
          <h2 id={titleId} className={`popover__title${hideTitle ? " visually-hidden" : ""}`}>{title}</h2>
          {dismissible ? <button type="button" className="popover__close" aria-label="Cerrar" popoverTarget={id} popoverTargetAction="hide">×</button> : null}
        </div>
        {state === "loading" && <p role="status">Cargando</p>}
        {state === "empty" && <p role="status">No hay opciones disponibles</p>}
        {state === "error" && <p role="alert">No fue posible cargar las opciones</p>}
        {state === "default" && children}
      </div>
    </div>
  );
}
