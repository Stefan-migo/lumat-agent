import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Accessible label for the close control (DS-UI-COPY default). */
  closeLabel?: string;
}

const FOCUSABLE =
  'button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])';

/** Corporate Dialog primitive (CORP-DIALOG-1..3): renders `role="dialog"` with
 *  `aria-modal`, sets meaningful initial focus on open, traps Tab focus, closes
 *  on Escape, and restores focus to the trigger on close. Overlay click does
 *  NOT close: destructive/blocking tasks need an explicit action or Escape. */
export function Dialog({ open, onClose, title, children, closeLabel = "Cerrar" }: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const restoreRef = useRef<Element | null>(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    restoreRef.current = document.activeElement;
    const first = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? dialogRef.current)?.focus();
    return () => {
      (restoreRef.current as HTMLElement | null)?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  const trap = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusables = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [],
    ).filter((el) => el.tabIndex !== -1);
    if (focusables.length === 0) {
      event.preventDefault();
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && active === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="dialog-overlay">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="dialog"
        onKeyDown={trap}
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
      </div>
    </div>
  );
}