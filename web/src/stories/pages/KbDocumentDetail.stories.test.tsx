import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KbDocumentDetailStory, Ready } from "./KbDocumentDetail.stories";

describe("KbDocumentDetail page story", () => {
  it("shows the redesigned header, tabs, and document summary cards", () => {
    render(<KbDocumentDetailStory {...Ready.args} />);

    expect(screen.getByRole("button", { name: "Editar contenido" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contenido" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Versiones" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Información del documento" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detalles técnicos" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Versión activa" })).toBeInTheDocument();
  });
});
