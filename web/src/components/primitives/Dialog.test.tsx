import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Dialog } from "./Dialog";

function dialogMarkup(open: boolean, onClose: () => void) {
  return (
    <>
      <button type="button">Abrir</button>
      <Dialog open={open} onClose={onClose} title="Eliminar registro">
        <button type="button">Confirmar</button>
        <button type="button">Cancelar</button>
      </Dialog>
    </>
  );
}

describe("Dialog (CORP-DIALOG-1)", () => {
  it("renders with dialog semantics, title and close control", () => {
    render(dialogMarkup(true, vi.fn()));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");

    const title = screen.getByText("Eliminar registro");
    expect(dialog).toHaveAttribute("aria-labelledby", title.id);

    expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeInTheDocument();
  });
});

describe("Dialog (CORP-DIALOG-2)", () => {
  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(dialogMarkup(true, onClose));

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("Dialog (CORP-DIALOG-3)", () => {
  it("moves focus to the first focusable on open and restores it on close", () => {
    const onClose = vi.fn();
    const { rerender } = render(dialogMarkup(false, onClose));

    const trigger = screen.getByRole("button", { name: "Abrir" });
    trigger.focus();
    expect(document.activeElement).toBe(trigger);

    rerender(dialogMarkup(true, onClose));
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Cerrar" }),
    );

    rerender(dialogMarkup(false, onClose));
    expect(document.activeElement).toBe(trigger);
  });

  it("traps Tab focus within the dialog, wrapping at both ends", () => {
    render(dialogMarkup(true, vi.fn()));

    const closeBtn = screen.getByRole("button", { name: "Cerrar" });
    const cancelBtn = screen.getByRole("button", { name: "Cancelar" });

    // Tab from the last focusable wraps to the first.
    fireEvent.keyDown(cancelBtn, { key: "Tab" });
    expect(document.activeElement).toBe(closeBtn);

    // Shift+Tab from the first wraps to the last.
    fireEvent.keyDown(closeBtn, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(cancelBtn);
  });
});