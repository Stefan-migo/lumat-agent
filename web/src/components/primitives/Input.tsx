import { useId } from 'react';
import type { InputHTMLAttributes } from 'react';
import { FieldShell } from './FieldShell';
import './primitives.css';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label: string;
  /** Control density; the visual size is a token concern, exposed via data-bx-size. */
  size?: 'sm' | 'md';
  /** Inline validation message, linked to the control via aria-describedby. */
  error?: string;
}

/** Labelled text/number/etc. input with token styling and accessible error wiring. */
export function Input({
  label,
  size = 'md',
  error,
  id,
  disabled = false,
  className = '',
  ...rest
}: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const errorId = error ? `${inputId}-error` : undefined;

  const controlClass = [
    'field__control',
    size === 'sm' ? 'field__control--sm' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <FieldShell label={label} id={inputId} errorId={errorId} error={error} disabled={disabled}>
      <input
        {...rest}
        id={inputId}
        className={controlClass}
        disabled={disabled}
        data-bx-size={size}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : rest['aria-describedby']}
      />
    </FieldShell>
  );
}
