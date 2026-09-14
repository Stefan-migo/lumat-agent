import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Dialog } from "./Dialog";

const dialogPrototype = HTMLDialogElement.prototype;
const nativeShowModal = dialogPrototype.showModal;
const nativeClose = dialogPrototype.close;

beforeAll(() => {
  if (typeof nativeShowModal !== "function") {
    Object.defineProperty(dialogPrototype, "showModal", {
      configurable: true,
      value() { this.setAttribute("open", ""); },
    });
  }
  if (typeof nativeClose !== "function") {
    Object.defineProperty(dialogPrototype, "close", {
      configurable: true,
      value() { this.removeAttribute("open"); },
    });
  }
});

afterAll(() => {
  if (typeof nativeShowModal !== "function") delete (dialogPrototype as { showModal?: unknown }).showModal;
  if (typeof nativeClose !== "function") delete (dialogPrototype as { close?: unknown }).close;
});

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

describe("Dialog (CST-PRIM-7, CORP-DIALOG-1)", () => {
  it("renders a native modal with an accessible name and close control", () => {
    render(dialogMarkup(true, vi.fn()));

    const dialog = screen.getByRole("dialog");
    expect(dialog.tagName).toBe("DIALOG");
    expect(dialog).toHaveAttribute("open");
    expect(dialog).toHaveAttribute("aria-modal", "true");

    const title = screen.getByText("Eliminar registro");
    expect(dialog).toHaveAttribute("aria-labelledby", title.id);

    expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeInTheDocument();
  });
  it("calls onClose for the native close event", () => {
    const onClose = vi.fn();
    render(dialogMarkup(true, onClose));
    const dialog = screen.getByRole("dialog");

    fireEvent(dialog, new Event("close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose for the native cancel event", () => {
    const onCancel = vi.fn();
    render(dialogMarkup(true, onCancel));
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("keeps the DOM lifecycle controlled by the open prop", () => {
    const onClose = vi.fn();
    const { rerender } = render(dialogMarkup(false, onClose));
    const dialog = screen.getByRole("dialog", { hidden: true });
    expect(dialog).not.toHaveAttribute("open");

    rerender(dialogMarkup(true, onClose));
    expect(dialog).toHaveAttribute("open");

    rerender(dialogMarkup(false, onClose));
    expect(dialog).not.toHaveAttribute("open");
  });
});
