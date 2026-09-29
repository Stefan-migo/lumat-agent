import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Archive, ArrowRightLeft } from "lucide-react";
import { Menu } from "./Menu";

const items = [
  { value: "edit", label: "Editar" },
  { value: "archive", label: "Archivar" },
  { value: "delete", label: "Eliminar", disabled: true },
];

describe("Menu (CST-PRIM-7)", () => {
  it("exposes menu semantics and selects an item", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Menu label="Acciones" items={items} onSelect={onSelect} />);
    const trigger = screen.getByRole("button", { name: "Acciones" });
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    await user.click(trigger);
    expect(screen.getByRole("menu", { name: "Acciones" })).toBeInTheDocument();
    expect(screen.getAllByRole("menuitem")).toHaveLength(3);
    await user.click(screen.getByRole("menuitem", { name: "Editar" }));
    expect(onSelect).toHaveBeenCalledWith("edit");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("moves focus with arrows and activates with Enter", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Menu label="Acciones" items={items} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: "Acciones" }));
    const menuItems = screen.getAllByRole("menuitem");
    await user.keyboard("{ArrowDown}");
    expect(menuItems[0]).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(menuItems[1]).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("archive");
  });

  it("activates the focused item with Space", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Menu label="Acciones" items={items} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: "Acciones" }));
    const firstItem = screen.getByRole("menuitem", { name: "Editar" });
    await user.keyboard("{ArrowDown}");
    expect(firstItem).toHaveFocus();
    await user.keyboard(" ");
    expect(onSelect).toHaveBeenCalledWith("edit");
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<Menu label="Acciones" items={items} onSelect={() => {}} />);
    const trigger = screen.getByRole("button", { name: "Acciones" });
    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("does not activate a disabled item", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Menu label="Acciones" items={items} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: "Acciones" }));
    const disabledItem = screen.getByRole("menuitem", { name: "Eliminar" });
    expect(disabledItem).toHaveAttribute("aria-disabled", "true");
    await user.click(disabledItem);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("does not open from a disabled trigger", () => {
    const onSelect = vi.fn();
    render(<Menu label="Acciones" items={items} onSelect={onSelect} disabled />);
    const trigger = screen.getByRole("button", { name: "Acciones" });

    expect(trigger).toBeDisabled();
    fireEvent.click(trigger);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(onSelect).not.toHaveBeenCalled();
  });
});

// panel-action-affordances — a row action is a single icon trigger whose accessible
// name carries the row identity, and its items may carry an icon and a destructive
// tone (DESIGN_SYSTEM.md:475, 509-510, 541-545).
describe("Menu — row affordances", () => {
  const rowItems = [
    { value: "state", label: "Cambiar estado", icon: ArrowRightLeft },
    { value: "archive", label: "Archivar", icon: Archive, tone: "danger" as const },
  ];

  it("an icon trigger takes its accessible name from the label and renders no visible text", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <Menu
        label="Acciones para Ana Pérez"
        items={rowItems}
        onSelect={onSelect}
        trigger="icon"
      />,
    );

    const trigger = screen.getByRole("button", { name: "Acciones para Ana Pérez" });
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger.textContent).toBe("");

    await user.click(trigger);
    expect(
      screen.getByRole("menu", { name: "Acciones para Ana Pérez" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Cambiar estado" }));
    expect(onSelect).toHaveBeenCalledWith("state");
  });

  it("renders an item icon as a decorative glyph without changing the item's accessible name", async () => {
    const user = userEvent.setup();
    render(<Menu label="Acciones" items={rowItems} onSelect={() => {}} trigger="icon" />);
    await user.click(screen.getByRole("button", { name: "Acciones" }));

    const item = screen.getByRole("menuitem", { name: "Cambiar estado" });
    const glyph = item.querySelector("svg");
    expect(glyph).not.toBeNull();
    expect(glyph).toHaveAttribute("aria-hidden", "true");
  });

  it("marks a destructive item with the danger tone, keeping an icon and its label — never colour alone", async () => {
    const user = userEvent.setup();
    render(<Menu label="Acciones" items={rowItems} onSelect={() => {}} trigger="icon" />);
    await user.click(screen.getByRole("button", { name: "Acciones" }));

    const destructive = screen.getByRole("menuitem", { name: "Archivar" });
    expect(destructive).toHaveClass("menu__item--danger");
    expect(destructive.querySelector("svg")).not.toBeNull();
    expect(destructive).toHaveTextContent("Archivar");
  });

  it("keeps the visible-label trigger by default — the existing contract is unchanged", () => {
    render(<Menu label="Acciones" items={items} onSelect={() => {}} />);
    const trigger = screen.getByRole("button", { name: "Acciones" });
    expect(trigger).toHaveTextContent("Acciones");
    expect(trigger.querySelector("svg")).toBeNull();
  });
});
