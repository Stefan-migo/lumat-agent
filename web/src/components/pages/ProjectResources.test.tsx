import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProjectResources } from "./ProjectResources";

const projectFile = { id: 1, project_id: 7, filename: "manual.pdf", content_type: "application/pdf", size: 2048, sha256: "x", status: "ready", created_at: "2026-07-10T14:02:00-04:00" };
const projectDoc = { id: 1, project_id: 7, title: "Manual", format: "pdf", version: 1, active_version: 1, active: true, visibility: "internal", provider: null, model: null, cost_meta: null, created_at: "2026-07-10T14:02:00-04:00" };
const globalDoc = { ...projectDoc, id: 2, project_id: null, title: "Global" };
const response = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("ProjectResources", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders project files and only project-scoped knowledge for admins", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [projectFile] }))
      .mockResolvedValueOnce(response({ docs: [projectDoc, globalDoc] }));
    render(<ProjectResources projectSlug="ops" projectId={7} role="admin" />);

    expect(await screen.findByText("manual.pdf")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    expect(await screen.findByText("Manual")).toBeInTheDocument();
    expect(screen.queryByText("Global")).not.toBeInTheDocument();
  });

  it("downloads a file using its filename", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [projectFile] }));
    const createObjectURL = vi.fn(() => "blob:test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const createElement = vi.spyOn(document, "createElement");
    fetchMock.mockResolvedValueOnce(new Response(new Blob(["pdf"]), { status: 200 }));
    render(<ProjectResources projectSlug="ops" projectId={7} role="operador" />);

    fireEvent.click(await screen.findByRole("button", { name: "Descargar manual.pdf" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/files/1/download", expect.anything()));
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    const anchor = createElement.mock.results.find((result) => result.type === "return" && result.value instanceof HTMLAnchorElement)?.value as HTMLAnchorElement;
    expect(anchor.download).toBe("manual.pdf");
  });

  it("does not fetch knowledge for non-admins", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(response({ files: [] }));
    render(<ProjectResources projectSlug="ops" projectId={7} role="operador" />);
    expect(await screen.findByText("Solo los administradores pueden ver los documentos indexados de un proyecto.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalledWith("/panel/api/kb", expect.anything());
  });

  it("shows the honest empty state when no project files exist", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(response({ files: [] }));
    render(<ProjectResources projectSlug="ops" projectId={7} role="operador" />);
    expect(await screen.findByText("Sin archivos")).toBeInTheDocument();
  });

  it("uploads a project file and refreshes the list", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ files: [] }))
      .mockResolvedValueOnce(response({ file: projectFile }))
      .mockResolvedValueOnce(response({ files: [projectFile] }));
    render(<ProjectResources projectSlug="ops" projectId={7} role="operador" />);

    const input = await screen.findByLabelText("Archivo del proyecto");
    fireEvent.change(input, { target: { files: [new File(["pdf"], "manual.pdf", { type: "application/pdf" })] } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/projects/ops/files", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByText("Archivo subido correctamente.")).toBeInTheDocument();
    expect(await screen.findByText("manual.pdf")).toBeInTheDocument();
  });
});
