import { useId } from 'react';
import type { SelectHTMLAttributes } from 'react';
import { FieldShell } from './FieldShell';
import './primitives.css';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label: string;
  options: SelectOption[];
  size?: 'sm' | 'md';
  error?: string;
}

/** Labelled dropdown (native `<select>` + `<option>`) with token styling. */
export function Select({
  label,
  options,
  size = 'md',
  error,
  id,
  disabled = false,
  className = '',
  ...rest
}: SelectProps) {
  const autoId = useId();
  const selectId = id ?? autoId;
  const errorId = error ? `${selectId}-error` : undefined;

  const controlClass = [
    'field__control',
    size === 'sm' ? 'field__control--sm' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <FieldShell label={label} id={selectId} errorId={errorId} error={error} disabled={disabled}>
      <select
        {...rest}
        id={selectId}
        className={controlClass}
        disabled={disabled}
        data-bx-size={size}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : rest['aria-describedby']}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}
