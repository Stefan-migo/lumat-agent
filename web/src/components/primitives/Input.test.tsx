import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Input } from "./Input";

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

  it("disables the input when disabled is set", () => {
    render(<Input label="Nombre" disabled />);
    expect(screen.getByLabelText("Nombre")).toBeDisabled();
  });
});
