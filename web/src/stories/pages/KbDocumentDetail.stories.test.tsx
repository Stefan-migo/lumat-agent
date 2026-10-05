import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import userEvent from "@testing-library/user-event";
import { KbDocumentDetailStory, Ready } from "./KbDocumentDetail.stories";

describe("KbDocumentDetail page story", () => {
  it("shows the redesigned header, unified content and versions tab, and summary cards", async () => {
    const user = userEvent.setup();
    render(<KbDocumentDetailStory {...Ready.args} />);

    expect(screen.getByRole("button", { name: "Editar contenido" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contenido y versiones" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Contenido" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Versiones" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Información del documento" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detalles técnicos" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Audiencia" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Disponibilidad" })).toBeInTheDocument();
    expect(screen.getByLabelText("Audiencia del documento")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar audiencia" })).toBeDisabled();
    expect(screen.getByLabelText("Proveedor")).toBeDisabled();
    expect(screen.getByLabelText("Modelo")).toBeDisabled();
    expect(screen.getByLabelText("Costo")).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: "Contenido y versiones" }));
    expect(await screen.findByLabelText("Contenido")).toBeInTheDocument();
    expect(screen.getByLabelText("Restaurar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Restaurar" })).toBeInTheDocument();
  });
});
