import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProjectResources } from "./ProjectResources";

const projectFile = { id: 1, project_id: 7, filename: "manual.pdf", content_type: "application/pdf", size: 2048, sha256: "x", status: "ready", kb_document_id: 1, folder_id: null, created_at: "2026-07-10T14:02:00-04:00" };
const projectDoc = { id: 1, project_id: 7, title: "Manual", format: "pdf", version: 1, active_version: 1, active: true, visibility: "internal", provider: null, model: null, cost_meta: null, created_at: "2026-07-10T14:02:00-04:00" };
const globalDoc = { ...projectDoc, id: 2, project_id: null, title: "Global" };
const response = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });
const renderResources = (role?: "admin" | "operador") => render(<ProjectResources projectSlug="ops" projectId={7} projectName="TestProject" role={role} />);

describe("ProjectResources", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("marks a file as indexed and does not repeat its KB document in the knowledge list", async () => {
    const linkedDoc = { ...projectDoc, id: 1, title: "manual.pdf" };
    const directDoc = { ...projectDoc, id: 3, title: "Politica interna" };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [projectFile] }))
      .mockResolvedValueOnce(response({ folders: [] }))
      .mockResolvedValueOnce(response({ docs: [linkedDoc, directDoc, globalDoc] }));
    renderResources("admin");

    expect(await screen.findByText("manual.pdf")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    expect((await screen.findAllByText("En la KB")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Politica interna")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Global")).not.toBeInTheDocument();
  });

  it("downloads a file using its filename", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [projectFile] }))
      .mockResolvedValueOnce(response({ folders: [] }));
    const createObjectURL = vi.fn(() => "blob:test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const createElement = vi.spyOn(document, "createElement");
    fetchMock.mockResolvedValueOnce(new Response(new Blob(["pdf"]), { status: 200 }));
    renderResources("operador");

    fireEvent.click(await screen.findByRole("button", { name: "Descargar manual.pdf" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/files/1/download", expect.anything()));
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    const anchor = createElement.mock.results.find((result) => result.type === "return" && result.value instanceof HTMLAnchorElement)?.value as HTMLAnchorElement;
    expect(anchor.download).toBe("manual.pdf");
  });

  it("does not fetch knowledge for non-admins", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [] }))
      .mockResolvedValueOnce(response({ folders: [] }));
    renderResources("operador");
    expect(await screen.findByText("Solo los administradores pueden ver los documentos indexados de un proyecto.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).not.toHaveBeenCalledWith("/panel/api/kb", expect.anything());
  });

  it("shows the honest empty state when no project files or folders exist", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [] }))
      .mockResolvedValueOnce(response({ folders: [] }));
    renderResources("operador");
    expect(await screen.findByText("Aún no hay archivos")).toBeInTheDocument();
  });

  it("renders the project root, folders with counts, and the totals footer", async () => {
    const folderA = { id: 10, project_id: 7, parent_id: null, name: "Diseño", created_at: null };
    const folderB = { id: 11, project_id: 7, parent_id: null, name: "Operación", created_at: null };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({
        files: [
          { ...projectFile, id: 1, filename: "a.png", folder_id: 10 },
          { ...projectFile, id: 2, filename: "b.png", folder_id: 10 },
          { ...projectFile, id: 3, filename: "resumen.md", folder_id: 11 },
          { ...projectFile, id: 4, filename: "raiz.txt", folder_id: null },
        ],
      }))
      .mockResolvedValueOnce(response({ folders: [folderA, folderB] }));
    renderResources("operador");

    expect(await screen.findByText("TestProject")).toBeInTheDocument();
    expect(screen.getByText("Diseño")).toBeInTheDocument();
    expect(screen.getByText("(2)")).toBeInTheDocument();
    expect(screen.getByText("(1)")).toBeInTheDocument();
    expect(screen.getByText("4 archivos · 2 carpetas")).toBeInTheDocument();
    expect(screen.getByText("raiz.txt")).toBeInTheDocument();
  });

  it("uploads a project file into the selected folder and refreshes the list", async () => {
    const folder = { id: 10, project_id: 7, parent_id: null, name: "Diseño", created_at: null };
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [] }))
      .mockResolvedValueOnce(response({ folders: [folder] }))
      .mockResolvedValueOnce(response({ file: { ...projectFile, folder_id: 10 } }))
      .mockResolvedValueOnce(response({ files: [{ ...projectFile, folder_id: 10 }] }));
    renderResources("operador");

    fireEvent.click(await screen.findByRole("button", { name: "Diseño" }));
    const input = screen.getByLabelText("Archivo del proyecto");
    fireEvent.change(input, { target: { files: [new File(["pdf"], "manual.pdf", { type: "application/pdf" })] } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/files", expect.objectContaining({ method: "POST" })));
    const body = fetchMock.mock.calls.find((call) => call[1]?.method === "POST")?.[1]?.body as FormData;
    expect(body.get("folder_id")).toBe("10");
    expect(await screen.findByText("Archivo subido correctamente.")).toBeInTheDocument();
  });

  it("creates a folder from the project actions menu", async () => {
    const user = userEvent.setup();
    const created = { id: 20, project_id: 7, parent_id: null, name: "Reportes", created_at: null };
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [projectFile] }))
      .mockResolvedValueOnce(response({ folders: [] }))
      .mockResolvedValueOnce(response({ folder: created }))
      .mockResolvedValueOnce(response({ folders: [created] }));
    renderResources("operador");

    await user.click(await screen.findByRole("button", { name: "Acciones del proyecto" }));
    await user.click(screen.getByRole("menuitem", { name: "Nueva carpeta" }));
    await user.type(screen.getByLabelText("Nombre de la carpeta"), "Reportes");
    await user.click(screen.getByRole("button", { name: "Crear carpeta" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/folders", expect.objectContaining({ method: "POST", body: JSON.stringify({ name: "Reportes", parent_id: null }) })));
  });

  it("deletes a project file after confirming in the dialog", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [projectFile] }))
      .mockResolvedValueOnce(response({ folders: [] }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(response({ files: [] }))
      .mockResolvedValueOnce(response({ folders: [] }));
    renderResources("operador");

    await user.click(await screen.findByRole("button", { name: "Eliminar manual.pdf" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("¿Quieres eliminar este archivo del proyecto?")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Eliminar archivo" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/files/1", expect.objectContaining({ method: "DELETE" })));
    expect(await screen.findByText("Archivo eliminado.")).toBeInTheDocument();
  });
});
