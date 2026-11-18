import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PanelSessions } from "./PanelSessions";

const sessions = [
  {
    id: 11,
    user_agent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Version/17.0 Mobile/15E148 Safari/604.1",
    created_at: "2026-01-01T00:00:00Z",
    last_used_at: "2026-01-02T00:00:00Z",
    current: true,
  },
  {
    id: 12,
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
    created_at: "2026-01-01T00:00:00Z",
    last_used_at: "2026-01-03T00:00:00Z",
    current: false,
  },
];

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("PanelSessions", () => {
  it("renders the caller's devices and marks only the current one", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ sessions }));
    render(<PanelSessions />);

    expect(await screen.findByText("iPhone · Safari")).toBeInTheDocument();
    expect(screen.getByText("Windows · Chrome")).toBeInTheDocument();
    expect(screen.getAllByText("Este dispositivo")).toHaveLength(1);
    expect(screen.getByText("Cada dispositivo que abrió el panel conserva el acceso hasta que lo revoques.")).toBeInTheDocument();
  });

  it("shows the empty state when there are no remembered devices", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ sessions: [] }));
    render(<PanelSessions />);
    expect(await screen.findByText("No hay dispositivos recordados")).toBeInTheDocument();
  });

  it("shows an error state when the list cannot be loaded", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ detail: "fallo" }, 500));
    render(<PanelSessions />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar los dispositivos");
  });

  it("requires confirmation, revokes a device, and refetches the list", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") return response({ ok: true });
      return response({ sessions });
    });
    const user = userEvent.setup();
    render(<PanelSessions />);

    const row = await screen.findByText("iPhone · Safari");
    const rowElement = row.closest("tr")!;
    await user.click(within(rowElement).getByRole("button", { name: "Revocar" }));
    expect(screen.getByRole("dialog", { name: "Revocar dispositivo" })).toHaveTextContent("iPhone · Safari");
    expect(screen.getByRole("dialog")).toHaveTextContent("tendrás que ingresar tus credenciales de nuevo en este dispositivo.");
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmar revocación" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(3));
    expect(fetchSpy.mock.calls[1][0]).toBe("/panel/api/sessions/11/revoke");
    expect(fetchSpy.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "POST" }));
    expect(fetchSpy.mock.calls[2][0]).toBe("/panel/api/sessions");
  });

  it("requires confirmation before closing the other sessions", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") return response({ ok: true });
      return response({ sessions });
    });
    const user = userEvent.setup();
    render(<PanelSessions />);

    await user.click(await screen.findByRole("button", { name: "Cerrar las demás sesiones" }));
    expect(screen.getByRole("dialog", { name: "Cerrar las demás sesiones" })).toHaveTextContent("Se cerrarán todas las sesiones excepto este dispositivo.");
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cerrar sesiones" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(3));
    expect(fetchSpy.mock.calls[1][0]).toBe("/panel/api/sessions/revoke-all");
    expect(fetchSpy.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "POST" }));
    expect(fetchSpy.mock.calls[2][0]).toBe("/panel/api/sessions");
  });
});
