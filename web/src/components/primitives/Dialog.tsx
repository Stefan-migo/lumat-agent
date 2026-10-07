import { useEffect, useId, useRef, type ReactNode } from "react";
import { X, type LucideIcon } from "lucide-react";
import "./primitives.css";
import { Icon } from "./Icon";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Accessible label for the close control (DS-UI-COPY default). */
  closeLabel?: string;
  icon?: LucideIcon;
  description?: string;
  size?: "default" | "wide";
  /** `sheet` rises from the bottom edge on small screens (centered dialog above 40rem). */
  variant?: "default" | "sheet";
}

/** Corporate Dialog primitive (CST-PRIM-7): native modal ownership. */
export function Dialog({ open, onClose, title, children, closeLabel = "Cerrar", icon, description, size = "default", variant = "default" }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const ignoreCloseRef = useRef(false);
  const titleId = useId();
  const supportsModal =
    typeof HTMLDialogElement !== "undefined" &&
    typeof HTMLDialogElement.prototype.showModal === "function";

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open && typeof dialog.showModal === "function") {
      dialog.showModal();
    } else if (!open && dialog.open && typeof dialog.close === "function") {
      ignoreCloseRef.current = true;
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
        ref={dialogRef}
        open={!supportsModal && open ? true : undefined}
        aria-modal="true"
        aria-labelledby={titleId}
        className={["dialog", size === "wide" ? "dialog--wide" : "", variant === "sheet" ? "dialog--sheet" : ""].filter(Boolean).join(" ")}
        onCancel={(event) => {
          event.preventDefault();
          ignoreCloseRef.current = true;
          onClose();
        }}
        onClose={() => {
          if (ignoreCloseRef.current) {
            ignoreCloseRef.current = false;
          } else {
            onClose();
          }
        }}
      >
        <div className="dialog__header">
          <div className="dialog__copy">
            {icon ? <span className="dialog__icon"><Icon icon={icon} /></span> : null}
            <div>
              <h2 id={titleId} className="dialog__title">{title}</h2>
              {description ? <p className="dialog__description">{description}</p> : null}
            </div>
          </div>
          <button
            type="button"
            className="dialog__close"
            aria-label={closeLabel}
            onClick={onClose}
          >
            <Icon icon={X} size="md" />
          </button>
        </div>
        <div className="dialog__body">{children}</div>
    </dialog>
  );
}
