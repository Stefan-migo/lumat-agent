import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ProjectAgents } from "./ProjectAgents";

describe("project agents", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows the roster with role chips and an empty latest-run state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      agents: [{ key: "orchestrator", name: "Orquestador", role: "Asistente del proyecto", description: "Responde consultas.", read_only: false }, { key: "verifier", name: "Verificador", role: "Verificación independiente", description: "Contrasta evidencia.", read_only: true }],
      latest_run: null,
    }), { status: 200 }));
    render(<ProjectAgents projectSlug="ops" />);

    expect(await screen.findByText("Roles disponibles para trabajar con el contexto del proyecto.")).toBeInTheDocument();
    expect(screen.getByText("Orquestador")).toBeInTheDocument();
    expect(screen.getByText("Asistente del proyecto")).toBeInTheDocument();
    expect(screen.getByText("Verificación independiente")).toBeInTheDocument();
    expect(screen.getByText("Sin ejecuciones registradas")).toBeInTheDocument();
  });

  it("reports request errors and retries", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "failed" }), { status: 500 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ agents: [], latest_run: null }), { status: 200 }));
    render(<ProjectAgents projectSlug="ops" />);

    fireEvent.click(await screen.findByRole("button", { name: "Reintentar" }));

    expect(await screen.findByText("Sin ejecuciones registradas")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("labels the recorded latest run as a state, not a live feed", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      agents: [], latest_run: { status: "completed", tool: "kb.search", at: "2026-10-09T12:00:00Z" },
    }), { status: 200 }));
    render(<ProjectAgents projectSlug="ops" />);

    expect(await screen.findByText("Estado registrado de la ejecución más reciente.")).toBeInTheDocument();
    expect(screen.getByText("Completada")).toBeInTheDocument();
    expect(screen.getByText(/kb\.search/)).toBeInTheDocument();
    expect(document.querySelector("time")?.getAttribute("datetime")).toBe("2026-10-09T12:00:00Z");
  });

  it("falls back to the raw status when the recorded value is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      agents: [], latest_run: { status: "weird", tool: null, at: null },
    }), { status: 200 }));
    render(<ProjectAgents projectSlug="ops" />);

    expect(await screen.findByText("weird")).toBeInTheDocument();
  });
});
