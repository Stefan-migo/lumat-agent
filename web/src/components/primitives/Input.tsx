import { useId, useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Eye, EyeOff, type LucideIcon } from "lucide-react";
import { Icon } from "./Icon";
import { FieldShell } from "./FieldShell";
import "./primitives.css";

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label: string;
  /** Control density; the visual size is a token concern, exposed via data-bx-size. */
  size?: "sm" | "md";
  /** Inline validation message, linked to the control via aria-describedby. */
  error?: string;
  icon?: LucideIcon;
  revealable?: boolean;
  helper?: string;
}

/** Labelled text/number/etc. input with token styling and accessible error wiring. */
export function Input({
  label,
  size = "md",
  error,
  icon,
  revealable = false,
  helper,
  id,
  disabled = false,
  className = "",
  ...rest
}: InputProps) {
  const autoId = useId();
  const [revealed, setRevealed] = useState(false);
  const inputId = id ?? autoId;
  const errorId = error ? `${inputId}-error` : undefined;

  const controlClass = [
    "field__control",
    size === "sm" ? "field__control--sm" : "",
    icon ? "field__control--with-adornment" : "",
    revealable && rest.type === "password" ? "field__control--with-toggle" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <FieldShell
      label={label}
      id={inputId}
      errorId={errorId}
      error={error}
      helper={helper}
      disabled={disabled}
    >
      {icon || (revealable && rest.type === "password") ? (
        <div className="field__control-wrap">
          {icon ? <span className="field__adornment field__adornment--leading"><Icon icon={icon} /></span> : null}
          <input {...rest} type={revealable && rest.type === "password" && revealed ? "text" : rest.type}
            id={inputId} className={controlClass} disabled={disabled} data-bx-size={size}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : rest["aria-describedby"]} />
          {revealable && rest.type === "password" ? (
            <button type="button" className="field__adornment field__adornment--trailing field__toggle" aria-label={revealed ? "Ocultar contraseña" : "Mostrar contraseña"}
              aria-pressed={revealed} onClick={() => setRevealed((current) => !current)}>
              <Icon icon={revealed ? EyeOff : Eye} />
            </button>
          ) : null}
        </div>
      ) : (
        <input {...rest} id={inputId} className={controlClass} disabled={disabled} data-bx-size={size}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : rest["aria-describedby"]} />
      )}
    </FieldShell>
  );
}
