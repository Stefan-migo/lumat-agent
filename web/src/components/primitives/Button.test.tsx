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

  it("forwards aria-pressed to the rendered button", () => {
    render(<Button aria-pressed>Monday</Button>);
    expect(screen.getByRole("button", { name: "Monday" })).toHaveAttribute("aria-pressed", "true");
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

  it("uses the dark semantic pair for primary actions and a light-boundary surface secondary", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.btn--primary\s*\{[^}]*background:\s*var\(--chrome-950\)[^}]*color:\s*var\(--text-on-dark\)/s);
    expect(css).toMatch(/\.btn--primary:hover\s*\{[^}]*background:\s*var\(--chrome-900\)/s);
    expect(css).toMatch(/\.btn--secondary\s*\{[^}]*background:\s*var\(--surface\)[^}]*border-color:\s*var\(--border\)/s);
  });

  it("uses the tokenized control-label weight for every button variant", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.btn\s*\{[^}]*font-weight:\s*var\(--weight-semibold\)/s);
  });

  it("keeps visible keyboard focus on action controls", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.btn:focus-visible[\s\S]*?outline:\s*var\(--focus-ring-width\) solid var\(--focus-ring\)/);
  });

  it("keeps danger action boundaries on the approved surface and uses danger as reinforcement", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.btn--danger\s*\{[^}]*background:\s*var\(--surface\)[^}]*color:\s*var\(--danger\)[^}]*border-color:\s*var\(--border\)/s);
    expect(css).toMatch(/\.btn--danger:hover\s*\{[^}]*background:\s*var\(--surface\)[^}]*border-color:\s*var\(--danger\)/s);
  });

  it("resolves every variant token reference against the token source — no phantom custom property", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    const tokens = readFileSync(join(process.cwd(), "src/tokens/tokens.css"), "utf8");
    // A custom property counts as declared when it is defined in the token source
    // or scoped locally inside this stylesheet (e.g. `.dashboard__card { --bent-accent: … }`).
    const declared = new Set(
      [...(css + tokens).matchAll(/(--[a-z0-9-]+)\s*:/gi)].map((match) => match[1]),
    );

    const variantRules = css.match(/\.btn--[a-z-]+(?:\s*:[a-z-]+)?\s*\{[^}]*\}/gs) ?? [];
    expect(variantRules.length).toBeGreaterThanOrEqual(4);

    const referenced = [
      ...new Set(
        variantRules.flatMap((rule) =>
          [...rule.matchAll(/var\((--[a-z0-9-]+)/gi)].map((match) => match[1]),
        ),
      ),
    ];
    expect(referenced.length).toBeGreaterThan(0);
    // A `var()` with no declared custom property is invalid at computed-value time,
    // so the declaration silently drops — the variant loses the style and still looks green.
    expect(referenced.filter((token) => !declared.has(token))).toEqual([]);
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
