import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { docs } from "./_shared/mockData/kb";
import { kbStatusLabel } from "./_shared/toneMaps";
import { KbList } from "../../components/pages/KbList";
import { KbListView, KbListEmpty } from "./KbList.stories";

describe("KbList page", () => {
  it("renders the Spanish page title and upload surface", () => {
    render(<KbListView />);
    expect(screen.getByRole("heading", { name: "Base de conocimientos" })).toBeInTheDocument();
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    expect(within(addRegion).getByLabelText(/título/i)).toBeInTheDocument();
    expect(within(addRegion).getByLabelText(/archivo/i)).toBeInTheDocument();
    expect(within(addRegion).getByRole("button", { name: "Agregar" })).toBeInTheDocument();
  });

  it("renders document rows with approved headers, statuses, audience and cost", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const first = docs[0];
    const row = within(table).getByText(`#${first.id}`).closest("tr") as HTMLElement;
    for (const header of ["#", "Título", "Formato", "Versión", "Estado", "Audiencia", "Costo"]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(within(row).getByText(first.title)).toBeInTheDocument();
    expect(within(row).getByText(first.format)).toBeInTheDocument();
    expect(within(row).getByText(`${first.version} (activa: ${first.active_version})`)).toBeInTheDocument();
    expect(within(row).getByText(kbStatusLabel(first.active ? "activo" : "deshabilitado"))).toBeInTheDocument();
    expect(within(row).getByText("$0.000412")).toBeInTheDocument();
    expect(within(row).getByText("Cliente y Lumat")).toBeInTheDocument();
  });

  it("places the populated document table on the shared data surface", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    expect(table.closest(".data-region")).toBeInTheDocument();
  });

  it("does not keep KB-specific layout selectors for the shared upload structure", () => {
    const stylesheet = readFileSync(resolve(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(stylesheet).not.toMatch(/\.kb-upload__fields/);
  });

  it("does not expose a workflow state prop that production does not provide", () => {
    const source = readFileSync(resolve(process.cwd(), "src/components/pages/KbList.tsx"), "utf8");
    expect(source).not.toMatch(/state\?: KbListState/);
  });

  it("makes documents primary and keeps upload and retrieval as secondary regions", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const uploadHeading = screen.getByRole("heading", { name: "Agregar documento" });
    expect(table.compareDocumentPosition(uploadHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(uploadHeading.closest(".card")).toBeNull();
    expect(screen.getByRole("region", { name: "Herramienta de recuperación" })).toBeInTheDocument();
  });

  it("renders an approved Spanish status label per document (triangulation across activo/deshabilitado)", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const inactive = docs.find((doc) => !doc.active)!;
    const inactiveRow = within(table).getByText(`#${inactive.id}`).closest("tr") as HTMLElement;
    const inactiveBadge = within(inactiveRow)
      .getAllByText(kbStatusLabel("deshabilitado"))
      .find((element) => element.getAttribute("data-tone") === "neutral");
    expect(inactiveBadge, "the inactive badge should render the approved label").toBeDefined();
    expect(within(inactiveRow).getByText("Interno (solo Lumat)")).toBeInTheDocument();

    const active = docs.find((doc) => doc.active)!;
    const activeRow = within(table).getByText(`#${active.id}`).closest("tr") as HTMLElement;
    const activeBadge = within(activeRow)
      .getAllByText(kbStatusLabel("activo"))
      .find((element) => element.getAttribute("data-tone") === "success");
    expect(activeBadge, "the active badge should render the approved label").toBeDefined();
  });

  it("links each document title to its detail without inline operation controls", async () => {
    const onOpenDocument = vi.fn();
    const user = userEvent.setup();
    render(<KbList data={{ docs }} onOpenDocument={onOpenDocument} />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    const link = within(row).getByRole("link", { name: docs[0].title });
    expect(link).toHaveClass("table__link");
    expect(within(row).queryByRole("button", { name: "Deshabilitar" })).toBeNull();
    expect(within(row).queryByRole("button", { name: "Restaurar" })).toBeNull();
    await user.click(link);
    expect(onOpenDocument).toHaveBeenCalledWith(docs[0].id);
  });

  it("declares who reads a customer document on every remaining audience surface", () => {
    render(<KbList data={{ docs }} />);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    expect(within(addRegion).getByRole("option", { name: "Cliente y Lumat" })).toBeInTheDocument();
    expect(within(addRegion).getByRole("option", { name: "Interno (solo Lumat)" })).toBeInTheDocument();
  });

  it("keeps provider/model advanced keys out of ordinary table rows", () => {
    render(<KbListView />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    expect(within(row).queryByText(`${docs[0].provider} / ${docs[0].model}`)).toBeNull();
  });

  it("renders the fetch error state from the page data source", async () => {
    render(<KbListView state="error" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar la base de conocimientos");
  });
});

describe("KbList empty story", () => {
  it("renders the empty state with an operable upload action", () => {
    render(<KbListEmpty />);
    expect(screen.getByText("No hay documentos")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar" })).toBeEnabled();
  });
});

describe("KbList search panel", () => {
  async function openSearch() {
    await screen.findByText(docs[0].title);
    return screen.getByRole("heading", { name: "Probar recuperación" }).closest(".card") as HTMLElement;
  }

  it("wires search values to backend request parameters", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ results: [] }), { status: 200 }));
    render(<KbList />);
    const searchCard = await openSearch();
    await user.type(within(searchCard).getByLabelText("Consulta"), "portabilidad numerica");
    await user.clear(within(searchCard).getByLabelText("Máximo de resultados"));
    await user.type(within(searchCard).getByLabelText("Máximo de resultados"), "9");
    await user.clear(within(searchCard).getByLabelText("Similitud mínima"));
    await user.type(within(searchCard).getByLabelText("Similitud mínima"), "0.75");
    await user.click(within(searchCard).getByRole("button", { name: "Buscar" }));
    await screen.findByText("No encontramos resultados");
    const requestUrl = new URL(String(fetchMock.mock.calls[1][0]), "http://localhost");
    expect(requestUrl.pathname).toBe("/panel/api/kb/search");
    expect(requestUrl.searchParams.get("q")).toBe("portabilidad numerica");
    expect(requestUrl.searchParams.get("top_k")).toBe("9");
    expect(requestUrl.searchParams.get("min_sim")).toBe("0.75");
    fetchMock.mockRestore();
  });

  it("renders loading, ready, empty, generic error and denied search states", async () => {
    const user = userEvent.setup();
    const results = [{ document_id: 1, title: docs[0].title, version: 3, chunk_index: 0, content: "Respuesta", source_meta: null, similarity: 0.9 }];
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const runSearch = async (response: Response, assertion: (searchCard: HTMLElement) => Promise<void>) => {
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }));
      fetchMock.mockResolvedValueOnce(response);
      const view = render(<KbList />);
      const searchCard = await openSearch();
      await user.click(within(searchCard).getByRole("button", { name: "Buscar" }));
      await assertion(searchCard);
      view.unmount();
    };

    await runSearch(new Response(JSON.stringify({ results }), { status: 200 }), async (searchCard) => {
      expect(await within(searchCard).findByText("1 resultados ordenados por similitud.")).toBeInTheDocument();
      expect(within(searchCard).getByText("Respuesta")).toBeInTheDocument();
    });
    await runSearch(new Response(JSON.stringify({ results: [] }), { status: 200 }), async (searchCard) => {
      expect(await within(searchCard).findByText("No encontramos resultados")).toBeInTheDocument();
    });
    await runSearch(new Response(JSON.stringify({ detail: "search failed" }), { status: 500 }), async (searchCard) => {
      expect(await within(searchCard).findByRole("alert")).toHaveTextContent("No pudimos realizar la búsqueda");
    });
    await runSearch(new Response(JSON.stringify({ detail: "search forbidden" }), { status: 403 }), async (searchCard) => {
      expect(await within(searchCard).findByRole("alert")).toHaveTextContent("No tienes permiso para buscar en la base de conocimientos");
    });

    let resolveSearch!: (response: Response) => void;
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }));
    fetchMock.mockReturnValueOnce(new Promise((resolve) => { resolveSearch = resolve; }));
    const loadingView = render(<KbList />);
    const loadingCard = await openSearch();
    await user.click(within(loadingCard).getByRole("button", { name: "Buscar" }));
    expect(await within(loadingCard).findByRole("status")).toHaveTextContent("Buscando en la base de conocimientos");
    resolveSearch(new Response(JSON.stringify({ results: [] }), { status: 200 }));
    loadingView.unmount();
    fetchMock.mockRestore();
  });
});

describe("KbList API page", () => {
  it("renders the admin document list from GET /panel/api/kb", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ docs }), { status: 200 }));
    render(<KbList />);
    expect(await screen.findByText(docs[0].title)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/kb", expect.objectContaining({ credentials: "include" }));
    fetchMock.mockRestore();
  });

  it("renders permission denied when an operador receives 403", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Admin role required" }), { status: 403 }));
    render(<KbList />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    fetchMock.mockRestore();
  });

  it("uploads a document as FormData and refreshes", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }));
    render(<KbList />);
    await screen.findByText(docs[0].title);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    expect(within(addRegion).getByLabelText("Audiencia")).toHaveValue("internal");
    await user.selectOptions(within(addRegion).getByLabelText("Audiencia"), "customer");
    await user.type(within(addRegion).getByLabelText("Título"), "Guide");
    await user.upload(within(addRegion).getByLabelText(/archivo/i), new File(["# Content"], "guide.md", { type: "text/markdown" }));
    await user.click(within(addRegion).getByRole("button", { name: "Agregar" }));
    const request = fetchMock.mock.calls[1][1] as RequestInit;
    expect(request.method).toBe("POST");
    expect(request.body).toBeInstanceOf(FormData);
    expect((request.body as FormData).get("title")).toBe("Guide");
    expect((request.body as FormData).get("file")).toBeInstanceOf(File);
    expect((request.body as FormData).get("visibility")).toBe("customer");
    expect((request.headers as Record<string, string> | undefined)?.["Content-Type"]).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    fetchMock.mockRestore();
  });

  it("shows the supported formats and size limit before upload", async () => {
    const user = userEvent.setup();
    render(<KbList data={{ docs }} />);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    const fileInput = within(addRegion).getByLabelText(/archivo/i);
    expect(fileInput).toHaveAttribute("accept", ".pdf,.md,.txt,.csv");
    expect(within(addRegion).getByText(/máximo 5 mb/i)).toBeInTheDocument();
    await user.type(within(addRegion).getByLabelText("Título"), "Guide");
    fireEvent.change(fileInput, { target: { files: [new File(["content"], "guide.exe", { type: "application/octet-stream" })] } });
    await user.click(within(addRegion).getByRole("button", { name: "Agregar" }));
    expect(await within(addRegion).findByRole("alert")).toHaveTextContent("Formato no compatible");
  });

  it("keeps processing feedback at the upload locus and offers upload retry after failure", async () => {
    const user = userEvent.setup();
    let resolveUpload!: (response: Response) => void;
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Response(JSON.stringify({ detail: "upload failed" }), { status: 500 }));
    render(<KbList data={{ docs }} />);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    await user.type(within(addRegion).getByLabelText("Título"), "Guide");
    await user.upload(within(addRegion).getByLabelText(/archivo/i), new File(["content"], "guide.md", { type: "text/markdown" }));
    await user.click(within(addRegion).getByRole("button", { name: "Agregar" }));
    expect(await within(addRegion).findByRole("alert")).toHaveTextContent("No pudimos procesar el documento");
    expect(within(addRegion).getByRole("button", { name: "Reintentar carga" })).toBeInTheDocument();

    fetchMock.mockReturnValueOnce(new Promise((resolve) => { resolveUpload = resolve; }));
    await user.click(within(addRegion).getByRole("button", { name: "Reintentar carga" }));
    expect(within(addRegion).getByRole("status")).toHaveTextContent("Procesando documento");
    resolveUpload(new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 }));
    fetchMock.mockRestore();
  });
});
