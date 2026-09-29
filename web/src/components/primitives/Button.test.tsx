import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Button } from "./Button";

// T7.1 — Button (PDW-CMP-1). Behavioral tests: tag selection (button vs anchor),
// click handling, disabled guard, and className passthrough contract.
describe("Button (T7.1)", () => {
  it("renders a <button> by default with the given children as its accessible name", () => {
    render(<Button>Guardar</Button>);
    const btn = screen.getByRole("button", { name: "Guardar" });
    expect(btn.tagName).toBe("BUTTON");
    expect(btn).toBeEnabled();
  });

  it("renders an anchor when href is provided, with the same children and href", () => {
    render(<Button href="/panel/export/clients.csv">Exportar</Button>);
    const link = screen.getByRole("link", { name: "Exportar" });
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "/panel/export/clients.csv");
  });

  it("fires onClick on click, but not when disabled", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    const { unmount } = render(<Button onClick={onClick}>Aceptar</Button>);
    await user.click(screen.getByRole("button", { name: "Aceptar" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    unmount();

    render(
      <Button onClick={onClick} disabled>
        Bloqueado
      </Button>,
    );
    await user.click(screen.getByRole("button", { name: "Bloqueado" }));
    expect(onClick).toHaveBeenCalledTimes(1); // unchanged — disabled never fires
    expect(screen.getByRole("button", { name: "Bloqueado" })).toBeDisabled();
  });

  it("passes a custom className through to the rendered element", () => {
    const { container } = render(
      <Button className="my-custom-button">Algo</Button>,
    );
    const custom = container.querySelector(".my-custom-button");
    expect(custom).not.toBeNull();
    expect(custom).toHaveTextContent("Algo");
  });

  it("renders all variants as enabled buttons (visual difference is token-only, PDW-TKN-2)", () => {
    render(<Button variant="primary">Guardar</Button>);
    render(<Button variant="secondary">Cancelar</Button>);
    render(<Button variant="tertiary">Operations</Button>);
    render(<Button variant="danger">Eliminar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Operations" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toHaveClass("btn--danger");
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeEnabled();
  });

  it("defines the danger variant through the existing danger token", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.btn--danger\s*\{[^}]*var\(--danger\)/s);
  });

  it("preserves native disabled behavior for the danger variant", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button variant="danger" onClick={onClick} disabled>Eliminar</Button>);

    const button = screen.getByRole("button", { name: "Eliminar" });
    expect(button).toHaveClass("btn--danger");
    expect(button).toBeDisabled();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Button — slice-1 catalog audit (CST-PRIM-1/4)", () => {
  it("keeps the primitive source hex-free — every value resolves through tokens (CST-PRIM-1)", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    const hex = css.match(/#[0-9a-fA-F]{3,6}\b/);
    expect(hex).toBeNull();
  });

  it("disabled pairing retains the visible label alongside the disabled semantic — never color alone (CST-PRIM-4)", () => {
    render(<Button disabled>Guardar</Button>);
    const btn = screen.getByRole("button", { name: "Guardar" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent("Guardar");
  });

  it("anchor disabled pairing exposes aria-disabled alongside the visible label (CST-PRIM-4)", () => {
    render(
      <Button href="/panel/export/clients.csv" disabled>
        Exportar
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Exportar" });
    expect(link).toHaveAttribute("aria-disabled", "true");
    expect(link).toHaveTextContent("Exportar");
  });
});
