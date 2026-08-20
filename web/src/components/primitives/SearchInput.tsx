import { useEffect, useRef } from "react";
import type { InputHTMLAttributes } from "react";
import "./primitives.css";

export interface SearchInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  onSearch: (query: string) => void;
  delay?: number;
}

export function SearchInput({
  onSearch,
  delay = 300,
  "aria-label": ariaLabel = "Buscar",
  className = "",
  ...rest
}: SearchInputProps) {
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  return (
    <div className="search-input">
      <span aria-hidden="true">⌕</span>
      <input
        {...rest}
        type="search"
        aria-label={ariaLabel}
        className={`search-input__control ${className}`.trim()}
        onChange={(event) => {
          clearTimeout(timer.current);
          const query = event.target.value;
          timer.current = setTimeout(() => onSearch(query), delay);
        }}
      />
    </div>
  );
}
