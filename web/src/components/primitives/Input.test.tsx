import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Input } from "./Input";
import { UserRound } from "lucide-react";

// T7.2 — Input (PDW-CMP-1). Label association (htmlFor+id), size via the
// observable data-bx-size contract, error/aria wiring, and disabled guard.
describe("Input (T7.2)", () => {
  it("associates the label with the input so getByLabelText resolves it", () => {
    render(<Input label="Nombre" />);
    const input = screen.getByLabelText("Nombre");
    expect(input.tagName).toBe("INPUT");
    expect(input).toHaveAttribute("data-bx-size", "md"); // default size
  });

  it("applies the sm size via the data-bx-size contract", () => {
    render(<Input label="Nombre" size="sm" />);
    expect(screen.getByLabelText("Nombre")).toHaveAttribute(
      "data-bx-size",
      "sm",
    );
  });

  it("updates the input value on typing via the onChange contract", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Input label="Usuario" value="" onChange={onChange} />);
    await user.type(screen.getByLabelText("Usuario"), "ana");
    expect(onChange).toHaveBeenCalled();
  });

  it("renders the error message and links it via aria-describedby + marks aria-invalid", () => {
    render(<Input label="Email" error="Formato de correo inválido" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    const describedBy = input.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    const message = screen.getByText("Formato de correo inválido");
    expect(message).toBeInTheDocument();
    expect(message.id).toBe(describedBy);
  });

  it("renders a leading icon, reveals passwords accessibly, and does not submit", async () => {
    const user = userEvent.setup();
    render(<form><Input label="Password" type="password" icon={UserRound} revealable /></form>);
    const input = screen.getByLabelText("Password");
    const toggle = screen.getByRole("button", { name: "Mostrar contraseña" });
    expect(document.querySelector(".field__adornment--leading svg")).toBeInTheDocument();
    expect(toggle).toHaveAttribute("type", "button");
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    await user.click(toggle);
    expect(input).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Ocultar contraseña" })).toHaveAttribute("aria-pressed", "true");
  });

  it("renders helper text unless an error replaces it", () => {
    const { rerender } = render(<Input label="Email" helper="Used for account notices" />);
    expect(screen.getByText("Used for account notices")).toHaveClass("field__helper");
    rerender(<Input label="Email" helper="Used for account notices" error="Invalid email" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid email");
    expect(screen.queryByText("Used for account notices")).not.toBeInTheDocument();
  });

  it("disables the input when disabled is set", () => {
    render(<Input label="Nombre" disabled />);
    expect(screen.getByLabelText("Nombre")).toBeDisabled();
  });

  it("disabled pairing keeps the visible label with the muted control — never color alone (CST-PRIM-4)", () => {
    render(<Input label="Nombre" disabled />);
    expect(screen.getByLabelText("Nombre")).toBeDisabled();
    // The label stays readable text (muted via .field--disabled), not dropped.
    expect(screen.getByText("Nombre")).toBeInTheDocument();
  });

  it("uses a non-white surface and measured boundary role with visible focus", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.field__control\s*\{[^}]*border:\s*1px solid var\(--border-strong\)[^}]*background:\s*var\(--surface\)/s);
    expect(css).toMatch(/\.field__control:focus\s*\{[^}]*outline:\s*var\(--focus-ring-width\) solid var\(--focus-ring\)/s);
    expect(css).toMatch(/\.field__control:disabled\s*\{[^}]*background:\s*var\(--surface-subtle\)/s);
  });
});
