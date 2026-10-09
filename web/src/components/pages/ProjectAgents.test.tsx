import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ProjectAgents } from "./ProjectAgents";

describe("project agents", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows the roster and an empty latest-run state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      agents: [{ key: "orchestrator", name: "Orquestador", role: "Asistente del proyecto", description: "Responde consultas.", read_only: false }, { key: "verifier", name: "Verificador", role: "Verificación independiente", description: "Contrasta evidencia.", read_only: true }],
      latest_run: null,
    }), { status: 200 }));
    render(<ProjectAgents projectSlug="ops" />);

    expect(await screen.findByText("Orquestador")).toBeInTheDocument();
    expect(screen.getByText("Verificación independiente")).toBeInTheDocument();
    expect(screen.getByText("Solo lectura")).toBeInTheDocument();
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

  it("shows the persisted latest-run status without implying a live feed", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      agents: [], latest_run: { status: "running", tool: null, at: "2026-10-09T12:00:00Z" },
    }), { status: 200 }));
    render(<ProjectAgents projectSlug="ops" />);

    expect(await screen.findByText(/Estado: running/)).toBeInTheDocument();
  });
});
