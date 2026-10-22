import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SettingsVersionHistory } from "./SettingsVersionHistory";

const versions = {
  versions: [
    { version: 1, created_at: "2026-10-22T10:00:00Z", actor: "adm", content: { orchestrator: "Eres Max." } },
    { version: 2, created_at: "2026-10-22T11:00:00Z", actor: "adm", content: { orchestrator: "Eres Max, edición dos." } },
  ],
};

function mockFetch(handler: (url: string, init?: RequestInit) => Response) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) =>
    Promise.resolve(handler(String(input), init)),
  );
}

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });

describe("SettingsVersionHistory", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads the history only when the owner asks for it", async () => {
    const user = userEvent.setup();
    const fetchSpy = mockFetch(() => json(versions));
    render(<SettingsVersionHistory scope="persona" onRestored={() => {}} />);

    expect(fetchSpy).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Ver historial" }));

    expect(await screen.findByText("Versión 2")).toBeInTheDocument();
    expect(screen.getByText("Versión 1")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/versions/persona", expect.anything());
  });

  it("says so when nothing was ever saved", async () => {
    const user = userEvent.setup();
    mockFetch(() => json({ versions: [] }));
    render(<SettingsVersionHistory scope="emergency" onRestored={() => {}} />);

    await user.click(screen.getByRole("button", { name: "Ver historial" }));

    expect(await screen.findByText("Todavía no hay versiones guardadas: se usa el texto original.")).toBeInTheDocument();
  });

  it("shows the diff of one version against the previous state", async () => {
    const user = userEvent.setup();
    const fetchSpy = mockFetch((url) =>
      url.includes("/diff?") ? json({ diff: { orchestrator: "-Eres Max.\\n+Eres Max, edición dos." } }) : json(versions),
    );
    render(<SettingsVersionHistory scope="persona" onRestored={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Ver historial" }));
    await screen.findByText("Versión 2");

    const buttons = screen.getAllByRole("button", { name: "Ver cambios" });
    await user.click(buttons[0]);

    expect(await screen.findByText(/Eres Max, edición dos\./)).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/versions/persona/diff?from=1&to=2", expect.anything());
  });

  it("restores a version and tells the parent to reload", async () => {
    const user = userEvent.setup();
    const onRestored = vi.fn();
    const fetchSpy = mockFetch((_url, init) => (init?.method === "POST" ? json({ ok: true }) : json(versions)));
    render(<SettingsVersionHistory scope="persona" onRestored={onRestored} />);
    await user.click(screen.getByRole("button", { name: "Ver historial" }));
    await screen.findByText("Versión 2");

    await user.click(screen.getAllByRole("button", { name: "Restaurar" })[1]);

    await waitFor(() => expect(onRestored).toHaveBeenCalled());
    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/versions/persona/restore", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ version: 1 }),
    }));
  });

  it("restores the shipped default through version zero", async () => {
    const user = userEvent.setup();
    const fetchSpy = mockFetch((_url, init) => (init?.method === "POST" ? json({ ok: true }) : json(versions)));
    render(<SettingsVersionHistory scope="emergency" onRestored={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Ver historial" }));

    await user.click(screen.getByRole("button", { name: "Restaurar original" }));

    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/versions/emergency/restore", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ version: 0 }),
    }));
  });

  it("reports a history that cannot be loaded", async () => {
    const user = userEvent.setup();
    mockFetch(() => new Response(JSON.stringify({ detail: "boom" }), { status: 500, headers: { "Content-Type": "application/json" } }));
    render(<SettingsVersionHistory scope="persona" onRestored={() => {}} />);

    await user.click(screen.getByRole("button", { name: "Ver historial" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar el historial.");
  });
});
