import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProjectSkills } from "./ProjectSkills";

const response = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("ProjectSkills", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows read-only global and editable project skills and persists project updates", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ skills: [{ name: "catalog", description: "Global entry", scope: "global" }] }))
      .mockResolvedValueOnce(response({ project: {} }));
    render(<ProjectSkills projectSlug="ops" projectId={4} role="operador" skills={[{ name: "local", description: "Project entry", body: "Local body" }]} />);

    expect(await screen.findByText("Global entry")).toBeInTheDocument();
    expect(screen.getByText("Local body")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText("Descripción de habilidad"), { target: { value: "Updated" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar habilidad" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/config", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ skills: [{ name: "local", description: "Updated", body: "Local body" }] }) })));
  });

  it("shows honest empty states", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ skills: [] }));
    render(<ProjectSkills projectSlug="ops" projectId={4} skills={[]} />);
    expect(await screen.findByText("Catálogo global vacío")).toBeInTheDocument();
    expect(screen.getByText("Sin habilidades de proyecto")).toBeInTheDocument();
  });
});
