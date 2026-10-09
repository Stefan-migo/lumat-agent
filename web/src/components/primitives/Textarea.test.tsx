import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Textarea } from "./Textarea";

// T7.4 — Textarea (PDW-CMP-1). Label association, controlled onChange,
// error/aria wiring, disabled guard. Resize/hour is token-driven via CSS.
describe("Textarea (T7.4)", () => {
  it("associates the label and renders a textarea element", () => {
    render(<Textarea label="Resumen" />);
    const textarea = screen.getByLabelText("Resumen");
    expect(textarea.tagName).toBe("TEXTAREA");
  });

  it("updates the value on typing via the onChange contract", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Textarea label="Resumen" value="" onChange={onChange} />);
    await user.type(screen.getByLabelText("Resumen"), "hola");
    expect(onChange).toHaveBeenCalled();
  });

  it("renders the error and links aria-describedby + marks aria-invalid", () => {
    render(<Textarea label="Resumen" error="Campo obligatorio" />);
    const textarea = screen.getByLabelText("Resumen");
    expect(textarea).toHaveAttribute("aria-invalid", "true");
    const describedBy = textarea.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    const message = screen.getByText("Campo obligatorio");
    expect(message).toBeInTheDocument();
    expect(message.id).toBe(describedBy);
  });

  it("disables the textarea when disabled is set", () => {
    render(<Textarea label="Resumen" disabled />);
    expect(screen.getByLabelText("Resumen")).toBeDisabled();
  });

  it("keeps a light surface boundary and keyboard focus indicator", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.field__control\s*\{[^}]*border:\s*1px solid var\(--border\)[^}]*background:\s*var\(--surface\)/s);
    expect(css).toMatch(/\.field__control:focus-visible\s*\{[^}]*outline:\s*var\(--focus-ring-width\) solid var\(--focus-ring\)/s);
  });
});
