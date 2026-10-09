import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import type { LucideIcon } from "lucide-react";
import { EllipsisVertical } from "lucide-react";
import { Icon } from "./Icon";
import "./primitives.css";

export interface MenuItem {
  value: string;
  label: string;
  disabled?: boolean;
  /** Optional leading glyph; decorative, the label stays the accessible name. */
  icon?: LucideIcon;
  /** `danger` marks a destructive item (DESIGN_SYSTEM.md:509-510). */
  tone?: "neutral" | "danger";
}

export interface MenuProps {
  label: string;
  ariaLabel?: string;
  items: MenuItem[];
  onSelect: (value: string) => void;
  disabled?: boolean;
  /**
   * `label` renders the label as the trigger's visible text (the original contract).
   * `icon` renders a compact icon-only trigger whose accessible name is `label`, so a
   * table row can carry one action control without repeating the row's own name
   * (DESIGN_SYSTEM.md:475).
   */
  trigger?: "label" | "icon";
  /** Radix content alignment. `end` opens leftwards — use it for a trigger near the right edge. */
  align?: "start" | "center" | "end";
  /** Radix collision padding in px, keeping the panel off the viewport edge. */
  collisionPadding?: number;
  showChevron?: boolean;
}

/** Radix-backed menu primitive (CST-PRIM-7): owns menu keyboard semantics. */
export function Menu({
  label,
  ariaLabel,
  showChevron = false,
  items,
  onSelect,
  disabled = false,
  trigger = "label",
  align,
  collisionPadding,
}: MenuProps) {
  const iconTrigger = trigger === "icon";
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        className={`${iconTrigger ? "menu__trigger menu__trigger--icon" : "menu__trigger"}${showChevron ? " menu__trigger--chevron" : ""}`}
        disabled={disabled}
        aria-label={ariaLabel ?? (iconTrigger ? label : undefined)}
      >
        {iconTrigger ? <Icon icon={EllipsisVertical} /> : <>{label}{showChevron ? <span className="menu__chevron" aria-hidden="true" /> : null}</>}
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu__content" aria-label={label} align={align} collisionPadding={collisionPadding}>
          {items.map((item) => (
            <DropdownMenu.Item
              key={item.value}
              className={item.tone === "danger" ? "menu__item menu__item--danger" : "menu__item"}
              disabled={item.disabled}
              onSelect={() => onSelect(item.value)}
            >
              {item.icon ? <Icon icon={item.icon} size="sm" /> : null}
              {item.label}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
