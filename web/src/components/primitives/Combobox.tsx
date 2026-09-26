import { useEffect, useId, useState, type KeyboardEvent } from "react";
import { FieldShell } from "./FieldShell";
import "./primitives.css";

export interface ComboboxOption { value: string; label: string }

export interface ComboboxProps {
  value: string | null;
  onChange: (value: string) => void;
  options: ComboboxOption[];
  label: string;
  id?: string;
  placeholder?: string;
  disabled?: boolean;
  emptyLabel?: string;
  onCreate?: (query: string) => void;
}

export function Combobox({
  value, onChange, options, label, id, placeholder, disabled = false, onCreate,
  emptyLabel = "Sin coincidencias",
}: ComboboxProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const listboxId = `${inputId}-listbox`;
  const selected = options.find((option) => option.value === value);
  const [text, setText] = useState(selected?.label ?? "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<number | null>(null);
  const matches = options
    .map((option, index) => ({ option, index }))
    .filter(({ option }) => option.label.toLocaleLowerCase().includes(text.toLocaleLowerCase()));

  useEffect(() => setText(selected?.label ?? ""), [value, selected?.label]);

  const choose = (option: ComboboxOption) => {
    onChange(option.value);
    setText(option.label);
    setOpen(false);
    setActive(null);
  };

  const activeMatch = active === null ? null : matches[active] ?? null;
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setOpen(false);
      setActive(null);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = event.key === "ArrowDown"
        ? (active === null ? 0 : Math.min(active + 1, matches.length - 1))
        : (active === null ? matches.length - 1 : Math.max(active - 1, 0));
      if (matches.length) {
        setActive(next);
        setOpen(true);
      }
    } else if (event.key === "Enter" && open && activeMatch) {
      event.preventDefault();
      choose(activeMatch.option);
    } else if (event.key === "Enter" && open && onCreate && text.trim() && !matches.length) {
      event.preventDefault();
      onCreate(text.trim());
      setOpen(false);
    }
  };

  useEffect(() => {
    if (!activeMatch) return;
    const option = document.getElementById(`${inputId}-option-${activeMatch.index}`);
    if (option && typeof option.scrollIntoView === "function") option.scrollIntoView({ block: "nearest" });
  }, [activeMatch?.index, inputId]);

  const canCreate = Boolean(onCreate && text.trim() && !matches.length);
  const showList = !disabled && open && (matches.length > 0 || canCreate);
  return (
    <FieldShell label={label} id={inputId} disabled={disabled}>
      <div className="combobox">
        <input
          id={inputId}
          role="combobox"
          className="field__control combobox__input"
          value={text}
          placeholder={placeholder}
          disabled={disabled}
          aria-expanded={showList}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={showList && activeMatch ? `${inputId}-option-${activeMatch.index}` : undefined}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setText(event.target.value);
            setActive(0);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            setOpen(false);
            setActive(null);
          }}
        />
        {showList ? (
          <ul id={listboxId} role="listbox" className="combobox__listbox">
            {matches.map(({ option, index }) => {
              return (
                <li
                  key={`${option.value}-${index}`}
                  id={`${inputId}-option-${index}`}
                  role="option"
                  aria-selected={option.value === value}
                  className="combobox__option"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(option)}
                >
                  {option.label}
                </li>
              );
            })}
            {canCreate ? (
              <li role="option" aria-selected="false" className="combobox__option" onMouseDown={(event) => event.preventDefault()} onClick={() => { onCreate?.(text.trim()); setOpen(false); }}>
                Crear «{text.trim()}»
              </li>
            ) : null}
          </ul>
        ) : text && !matches.length && !disabled ? (
          <span className="combobox__empty">{emptyLabel}</span>
        ) : null}
      </div>
    </FieldShell>
  );
}
