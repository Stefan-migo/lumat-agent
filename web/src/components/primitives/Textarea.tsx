import { useId } from "react";
import type { TextareaHTMLAttributes } from "react";
import { FieldShell } from "./FieldShell";
import "./primitives.css";

export interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  /** Inline validation message, linked to the control via aria-describedby. */
  error?: string;
}

/** Labelled multi-line textarea with token sizing and accessible error wiring. */
export function Textarea({
  label,
  error,
  id,
  disabled = false,
  className = "",
  ...rest
}: TextareaProps) {
  const autoId = useId();
  const textareaId = id ?? autoId;
  const errorId = error ? `${textareaId}-error` : undefined;

  return (
    <FieldShell
      label={label}
      id={textareaId}
      errorId={errorId}
      error={error}
      disabled={disabled}
    >
      <textarea
        {...rest}
        id={textareaId}
        className={["field__control", "field__textarea", className]
          .filter(Boolean)
          .join(" ")}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : rest["aria-describedby"]}
      />
    </FieldShell>
  );
}
