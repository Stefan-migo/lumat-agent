import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProjectSkills } from "./ProjectSkills";
import { ToastProvider } from "../primitives/Toast";

const response = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("ProjectSkills", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows read-only global and editable project skills and persists project updates", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ skills: [{ name: "catalog", description: "Global entry", scope: "global", body: "## Global body" }] }))
      .mockResolvedValueOnce(response({ project: {} }));
    render(<ProjectSkills projectSlug="ops" role="operador" skills={[{ name: "local", description: "Project entry", body: "Local body" }]} />);

    expect(await screen.findByText("Global entry")).toBeInTheDocument();
    expect(screen.getByText("Project entry")).toBeInTheDocument();
    expect(screen.getByText("Global")).toBeInTheDocument();
    expect(screen.getByText("Solo lectura")).toBeInTheDocument();
    expect(screen.getByText("Proyecto")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Acciones de local" }));
    await user.click(screen.getByRole("menuitem", { name: "Editar" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Descripción de habilidad"), { target: { value: "Updated" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar habilidad" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/config", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ skills: [{ name: "local", description: "Updated", body: "Local body" }] }) })));
  });

  it("adds a project skill from the card header through the dialog", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ skills: [] }))
      .mockResolvedValueOnce(response({ project: {} }));
    render(<ToastProvider><ProjectSkills projectSlug="ops" skills={[]} /></ToastProvider>);
    expect(await screen.findByText("Aún no hay habilidades en este proyecto")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Agregar habilidad" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Nombre de habilidad"), { target: { value: "resumen-operativo" } });
    fireEvent.change(within(dialog).getByLabelText("Descripción de habilidad"), { target: { value: "Resume" } });
    fireEvent.change(within(dialog).getByLabelText("Contenido de habilidad"), { target: { value: "Body" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Guardar habilidad" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/config", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ skills: [{ name: "resumen-operativo", description: "Resume", body: "Body" }] }) })));
    expect(await screen.findByText("Habilidad agregada.", { selector: ".toast__message" })).toBeInTheDocument();
  });

  it("expands a global skill into its read-only content", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ skills: [{ name: "catalog", description: "Global entry", scope: "global", body: "## Propósito\n\nOrganizar la memoria." }] }));
    render(<ProjectSkills projectSlug="ops" skills={[]} />);

    const row = await screen.findByRole("button", { name: /catalog/ });
    expect(row).toHaveAttribute("aria-expanded", "false");

    await user.click(row);

    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Contenido de la habilidad")).toBeInTheDocument();
    expect(screen.getByText("Vista de lectura")).toBeInTheDocument();
    expect(screen.getByText("Propósito")).toBeInTheDocument();
  });

  it("filters both lists by the search query", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ skills: [{ name: "catalog", description: "Global entry", scope: "global", body: null }] }));
    render(<ProjectSkills projectSlug="ops" skills={[{ name: "local", description: "Project entry", body: "" }]} />);

    await screen.findByText("Global entry");
    await user.type(screen.getByLabelText("Buscar habilidad"), "sin-coincidencia");

    expect((await screen.findAllByText("Sin coincidencias", {}, { timeout: 2000 })).length).toBe(2);
  });

  it("shows honest empty states", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ skills: [] }));
    render(<ProjectSkills projectSlug="ops" skills={[]} />);

    expect(await screen.findByText("Catálogo global vacío")).toBeInTheDocument();
    expect(screen.getByText("Aún no hay habilidades en este proyecto")).toBeInTheDocument();
  });
});
