import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { Dialog } from "./Dialog";
import { KeyRound } from "lucide-react";

const dialogPrototype = HTMLDialogElement.prototype;
const nativeShowModal = dialogPrototype.showModal;
const nativeClose = dialogPrototype.close;
const primitives = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");

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
    const close = screen.getByRole("button", { name: "Cerrar" });
    expect(close.querySelector("svg")).toHaveClass("icon", "icon--md");
    expect(close).not.toHaveTextContent("✕");
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeInTheDocument();
  });
  it("uses a non-white dialog surface, distinct radius, and overlay shadow token", () => {
    const dialog = primitives.match(/\.dialog\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(dialog).toMatch(/background:\s*var\(--surface\)/);
    expect(dialog).toMatch(/border-radius:\s*var\(--radius-xl\)/);
    expect(dialog).toMatch(/box-shadow:\s*var\(--shadow-3\)/);
  });
  it("renders optional header icon and description without changing the title label", () => {
    render(<Dialog open onClose={vi.fn()} title="Reset password" icon={KeyRound} description="Choose a new password">Body</Dialog>);
    const dialog = screen.getByRole("dialog");
    const title = screen.getByRole("heading", { name: "Reset password" });
    expect(dialog).toHaveAttribute("aria-labelledby", title.id);
    expect(screen.getByText("Choose a new password")).toHaveClass("dialog__description");
    expect(document.querySelector(".dialog__icon svg")).toBeInTheDocument();
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
    const prevented = fireEvent(
      screen.getByRole("dialog"),
      new Event("cancel", { cancelable: true }),
    );
    expect(prevented).toBe(false);
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

  it("anchors mobile dialogs as animated, scrollable bottom sheets", () => {
    const mobileRules = primitives.split('@media (max-width: 40rem)').find((rules) => rules.includes('dialog-sheet-enter')) ?? '';
    const sheet = mobileRules.match(/\.dialog\s*\{([^}]*)\}/)?.[1] ?? "";
    const header = mobileRules.match(/\.dialog__header\s*\{([^}]*)\}/)?.[1] ?? "";
    const body = mobileRules.match(/\.dialog__body\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(sheet).toMatch(/position:\s*fixed/);
    expect(sheet).toMatch(/inset:\s*auto 0 0/);
    expect(sheet).toMatch(/width:\s*100vw/);
    expect(sheet).toMatch(/border-radius:\s*var\(--radius-xl\) var\(--radius-xl\) 0 0/);
    expect(sheet).toMatch(/animation:/);
    expect(header).toMatch(/flex:\s*0 0 auto/);
    expect(body).toMatch(/min-height:\s*0/);
    expect(body).toMatch(/overflow-y:\s*auto/);
  });

  it("renders the new-visit dialog fullscreen with sticky actions on mobile", () => {
    const mobileRules = primitives.split('@media (max-width: 40rem)').find((rules) => rules.includes('dialog-sheet-enter')) ?? '';
    const createDialog = mobileRules.match(/\.dialog:has\(\.agenda-create-form\)\s*\{([^}]*)\}/)?.[1] ?? "";
    const actions = mobileRules.match(/\.agenda-create-form__actions\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(createDialog).toMatch(/inset:\s*0/);
    expect(createDialog).toMatch(/height:\s*100dvh/);
    expect(createDialog).toMatch(/max-height:\s*100dvh/);
    expect(createDialog).toMatch(/border-radius:\s*0/);
    expect(actions).toMatch(/position:\s*sticky/);
    expect(actions).toMatch(/bottom:\s*0/);
  });

  it("widens the desktop create dialog and lets schedule fields shrink", () => {
    const createDialog = primitives.match(/@media \(min-width: 40\.0625rem\)\s*\{\s*\.dialog:has\(\.agenda-create-form\)\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(createDialog).toMatch(/width:\s*min\(44rem,\s*calc\(100vw\s*-\s*var\(--space-5\)\)\)/);
    expect(primitives).toMatch(/\.agenda-create-form__row\s*>\s*\*\s*\{[^}]*min-width:\s*0/);
    expect(primitives).toMatch(/\.agenda-create-form__row\s+\.field__control-wrap\s*\{[^}]*min-width:\s*0/);
  });

  it("keeps closed dialogs hidden on mobile despite the sheet layout", () => {
    const mobileRules = primitives.split('@media (max-width: 40rem)').find((rules) => rules.includes('dialog-sheet-enter')) ?? '';
    const closed = mobileRules.match(/\.dialog:not\(\[open\]\)\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(closed).toMatch(/display:\s*none/);
  });
});
