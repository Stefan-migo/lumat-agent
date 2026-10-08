import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MessagePreview } from "./MessagePreview";

describe("MessagePreview", () => {
  it("shows the assistant avatar, message, and optional caption", () => {
    render(<MessagePreview message="Hola, ¿en qué te ayudo?" note="Menú de categorías automático" />);
    expect(screen.getByText("Hola, ¿en qué te ayudo?")).toBeInTheDocument();
    expect(screen.getByText("L")).toBeInTheDocument();
    expect(screen.getByText("Menú de categorías automático")).toBeInTheDocument();
  });

  it("supports a custom author and omits the caption when absent", () => {
    render(<MessagePreview message="Mensaje" name="Asistente" />);
    expect(screen.getByLabelText("Mensaje de Asistente")).toBeInTheDocument();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("uses an optional brand image without changing the default letter avatar", () => {
    render(<MessagePreview message="Hola" avatarSrc="/panel/app/brand/lumat-mark.png" />);
    expect(screen.getByRole("img", { name: "Lumat" })).toHaveAttribute("src", "/panel/app/brand/lumat-mark.png");
  });
});
