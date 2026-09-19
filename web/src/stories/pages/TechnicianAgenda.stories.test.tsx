import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { TechnicianSurfaceView } from "./TechnicianAgenda.stories";
import * as storyModule from "./TechnicianAgenda.stories";
import { agendaData, agendaLong, agendaNow } from "./_shared/mockData/technicianAgenda";

describe("TechnicianAgenda page story", () => {
  it("publishes every documented state", () => {
    for (const name of ["Default", "LongRoster", "NoCustomerData", "Empty", "Loading", "Error"]) {
      expect(storyModule[name as keyof typeof storyModule], name).toBeDefined();
    }
  });

  it("renders one page heading, the shell brand and the session control", () => {
    render(<TechnicianSurfaceView />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByAltText("Lumat")).toBeInTheDocument();
    expect(screen.getByText("tec-agenda")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
  });

  it("reads as a schedule: today marked, past separated, the slot leading each card", () => {
    render(<TechnicianSurfaceView />);

    const upcoming = screen.getByRole("region", { name: "Próximas visitas" });
    expect(within(upcoming).getByRole("heading", { name: "Hoy" })).toBeInTheDocument();
    expect(within(upcoming).getByRole("heading", { name: "Mañana" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Visitas anteriores" })).getByText("Cliente Demo H3")).toBeInTheDocument();
    expect(screen.getByText("3 visitas · 1 cancelada · Actualizado", { exact: false })).toBeInTheDocument();

    const card = screen.getByText("Revisión de calefont").closest("article");
    expect(card?.firstElementChild).toHaveClass("technician-agenda__slot");
    expect(within(card as HTMLElement).getByText("15:00")).toBeInTheDocument();
  });

  it("keeps every fallback string on the card when the customer data is absent", () => {
    render(<TechnicianSurfaceView data={agendaData.map((row) => ({ ...row, customer: { name: null, address: null, comuna: null, phone: null }, case_summary: null }))} />);

    expect(screen.getAllByText("Cliente sin nombre").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Dirección no registrada").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Comuna no registrada").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Teléfono no registrado").length).toBeGreaterThan(0);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("groups a twelve-visit roster without losing a day or a card", () => {
    render(<TechnicianSurfaceView data={agendaLong} />);

    expect(screen.getByText("9 visitas · 3 canceladas · Actualizado", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Mantención programada número 12")).toBeInTheDocument();
    // Twelve consecutive days from the fixed clock: today is day one.
    expect(screen.getByRole("heading", { name: "Hoy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mañana" })).toBeInTheDocument();
  });

  it("renders the empty, loading and error states through the frame", () => {
    const { rerender } = render(<TechnicianSurfaceView data={[]} state="empty" />);
    expect(screen.getByText("No hay visitas asignadas")).toBeInTheDocument();

    rerender(<TechnicianSurfaceView data={null} state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando agenda");

    rerender(<TechnicianSurfaceView data={null} state="error" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos cargar la agenda");
    expect(screen.getByRole("button", { name: "Reintentar" })).toHaveClass("btn");
  });

  it("pins the story clock so the day labels cannot drift with the run date", () => {
    expect(agendaNow.toISOString()).toBe("2026-09-19T15:00:00.000Z");
  });
});
