import type { ReactNode } from 'react';

/**
 * Shared label + error wrapper for the form-control primitives (Input/Select/
 * Textarea). Private helper — NOT part of the 17-primitive public surface.
 *
 * Renders the semantic structure the controls need for accessibility:
 * - an associated `<label>` (htmlFor ↔ control id),
 * - the control itself (children),
 * - an error message linked via `aria-describedby` when `error` is present.
 */
export interface FieldShellProps {
  label: string;
  /** id of the wrapped control; the label's htmlFor points here. */
  id: string;
  /** id used on the error span; the control's aria-describedby points here. */
  errorId?: string;
  error?: string;
  disabled?: boolean;
  children: ReactNode;
}

export function FieldShell({ label, id, errorId, error, disabled, children }: FieldShellProps) {
  const className = `field${disabled ? ' field--disabled' : ''}`;
  return (
    <div className={className}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children}
      {error ? (
        <span className="field__error" id={errorId} role="alert" data-testid="field-error">
          {error}
        </span>
      ) : null}
    </div>
  );
}
