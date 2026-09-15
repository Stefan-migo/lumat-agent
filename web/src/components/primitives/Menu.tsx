import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import "./primitives.css";

export interface MenuItem {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface MenuProps {
  label: string;
  items: MenuItem[];
  onSelect: (value: string) => void;
  disabled?: boolean;
}

/** Radix-backed menu primitive (CST-PRIM-7): owns menu keyboard semantics. */
export function Menu({ label, items, onSelect, disabled = false }: MenuProps) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="menu__trigger" disabled={disabled}>
        {label}
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu__content" aria-label={label}>
          {items.map((item) => (
            <DropdownMenu.Item
              key={item.value}
              className="menu__item"
              disabled={item.disabled}
              onSelect={() => onSelect(item.value)}
            >
              {item.label}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
