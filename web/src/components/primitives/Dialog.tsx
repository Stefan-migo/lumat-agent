import { useEffect, useId, useRef, type ReactNode } from "react";
import "./primitives.css";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Accessible label for the close control (DS-UI-COPY default). */
  closeLabel?: string;
}

/** Corporate Dialog primitive (CST-PRIM-7): native modal ownership. */
export function Dialog({ open, onClose, title, children, closeLabel = "Cerrar" }: DialogProps) {
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
        className="dialog"
        onCancel={() => {
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
          <h2 id={titleId} className="dialog__title">
            {title}
          </h2>
          <button
            type="button"
            className="dialog__close"
            aria-label={closeLabel}
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        <div className="dialog__body">{children}</div>
    </dialog>
  );
}
