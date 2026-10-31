import { readdirSync, readFileSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { docs } from "./_shared/mockData/kb";
import { kbStatusLabel } from "./_shared/toneMaps";
import { KbList } from "../../components/pages/KbList";
import { ToastProvider } from "../../components/primitives/Toast";
import type { ReactElement } from "react";

/** Upload results are toasts, so these renders need the provider. */
const renderKb = (ui: ReactElement) => render(<ToastProvider>{ui}</ToastProvider>);
import { KbListView, KbListEmpty } from "./KbList.stories";

const sourceRoot = resolve(process.cwd(), "src");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    if (path.includes(".test.")) return [];
    return [path].filter((file) => [".ts", ".tsx"].includes(extname(file)));
  });
}

describe("KbList page", () => {
  it("renders the Spanish page title and upload surface", () => {
    render(<KbListView />);
    expect(screen.getByRole("heading", { name: "Base de conocimientos" })).toBeInTheDocument();
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    expect(within(addRegion).getByLabelText(/título/i)).toBeInTheDocument();
    expect(within(addRegion).getByLabelText("Archivo (PDF / MD / TXT / CSV)")).toBeInTheDocument();
    expect(within(addRegion).getByRole("button", { name: "Agregar" })).toBeInTheDocument();
  });

  it("renders document rows with approved headers, statuses, audience and cost", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const first = docs[0];
    const row = within(table).getByRole("link", { name: new RegExp(first.title) }).closest("tr") as HTMLElement;
    for (const header of ["Documento", "Versión", "Estado", "Audiencia", "Costo"]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(within(row).getByText(`#${first.id} · ${first.format.toUpperCase()}`)).toBeInTheDocument();
    expect(within(row).getByText(`v${first.active_version} · Activa`)).toBeInTheDocument();
    expect(within(row).getByText(kbStatusLabel(first.active ? "activo" : "deshabilitado"))).toBeInTheDocument();
    expect(within(row).getByText("$0.000412")).toBeInTheDocument();
    expect(within(row).getByText("Cliente · Cliente y Lumat")).toBeInTheDocument();
  });

  it("places the populated document table on the shared data surface", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    expect(table.closest(".card")).toHaveClass("kb-list__documents");
  });

  it("keeps every KB stylesheet class referenced by a component or story", () => {
    const stylesheet = readFileSync(resolve(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    const declaredClasses = [...stylesheet.matchAll(/\.((?:kb)[a-z0-9_-]*)\b/g)].map((match) => match[1]);
    const source = sourceFiles(sourceRoot).map((file) => readFileSync(file, "utf8")).join("\n");
    const unreferenced = [...new Set(declaredClasses)].filter((className) => !new RegExp(`(?:^|[^a-z0-9_-])${className}(?:$|[^a-z0-9_-])`).test(source));

    expect(unreferenced, `Unreferenced KB classes: ${unreferenced.join(", ")}`).toEqual([]);
  });

  it("does not expose a workflow state prop that production does not provide", () => {
    const source = readFileSync(resolve(process.cwd(), "src/components/pages/KbList.tsx"), "utf8");
    expect(source).not.toMatch(/state\?: KbListState/);
  });

  it("makes documents and retrieval primary and keeps only upload in the secondary column", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const uploadHeading = screen.getByRole("heading", { name: "Agregar documento" });
    expect(table.compareDocumentPosition(uploadHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(table.closest(".kb-list__layout")).toHaveClass("kb-list__layout");
    expect(uploadHeading.closest(".kb-list__secondary")).toBeInTheDocument();
    const primary = table.closest(".kb-list__primary") as HTMLElement;
    const retrieval = screen.getByRole("heading", { name: "Probar recuperación" });
    expect(retrieval.closest(".kb-list__primary")).toBe(primary);
    expect(table.compareDocumentPosition(retrieval) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("region", { name: "Herramienta de recuperación" }).closest(".kb-list__secondary")).toBeNull();
  });

  it("renders an approved Spanish status label per document (triangulation across activo/deshabilitado)", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const inactive = docs.find((doc) => !doc.active)!;
    const inactiveRow = within(table).getByRole("link", { name: new RegExp(inactive.title) }).closest("tr") as HTMLElement;
    const inactiveBadge = within(inactiveRow)
      .getAllByText(kbStatusLabel("deshabilitado"))
      .find((element) => element.getAttribute("data-tone") === "neutral");
    expect(inactiveBadge, "the inactive badge should render the approved label").toBeDefined();
    expect(within(inactiveRow).getByText("Interno · Solo Lumat")).toBeInTheDocument();

    const active = docs.find((doc) => doc.active)!;
    const activeRow = within(table).getByRole("link", { name: new RegExp(active.title) }).closest("tr") as HTMLElement;
    const activeBadge = within(activeRow)
      .getAllByText(kbStatusLabel("activo"))
      .find((element) => element.getAttribute("data-tone") === "success");
    expect(activeBadge, "the active badge should render the approved label").toBeDefined();
  });

  it("links each document title to its detail without inline operation controls", async () => {
    const onOpenDocument = vi.fn();
    const user = userEvent.setup();
    renderKb(<KbList data={{ docs }} onOpenDocument={onOpenDocument} />);
    const row = within(screen.getByRole("table")).getByRole("link", { name: new RegExp(docs[0].title) }).closest("tr") as HTMLElement;
    const link = within(row).getByRole("link", { name: new RegExp(docs[0].title) });
    expect(link).toHaveClass("kb-list__identity");
    expect(within(row).queryByRole("button", { name: "Deshabilitar" })).toBeNull();
    expect(within(row).queryByRole("button", { name: "Restaurar" })).toBeNull();
    await user.click(link);
    expect(onOpenDocument).toHaveBeenCalledWith(docs[0].id);
  });

  it("declares who reads a customer document on every remaining audience surface", () => {
    renderKb(<KbList data={{ docs }} />);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    expect(within(addRegion).getByRole("option", { name: "Cliente y Lumat" })).toBeInTheDocument();
    expect(within(addRegion).getByRole("option", { name: "Interno (solo Lumat)" })).toBeInTheDocument();
  });

  it("keeps provider/model advanced keys out of ordinary table rows", () => {
    render(<KbListView />);
    const row = within(screen.getByRole("table")).getByRole("link", { name: new RegExp(docs[0].title) }).closest("tr") as HTMLElement;
    expect(within(row).queryByText(`${docs[0].provider} / ${docs[0].model}`)).toBeNull();
  });

  it("renders the fetch error state from the page data source", async () => {
    render(<KbListView state="error" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar la base de conocimientos");
  });

  it("renders the page loading banner from its own data source", async () => {
    renderKb(<KbList fetchDocuments={() => new Promise(() => undefined)} />);
    expect(await screen.findByRole("status")).toHaveTextContent("Cargando base de conocimientos");
    expect(screen.getByText("Documentos de la base de conocimientos")).toBeInTheDocument();
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
    await screen.findByRole("table");
    return screen.getByRole("heading", { name: "Probar recuperación" }).closest(".card") as HTMLElement;
  }

  it("wires search values to backend request parameters", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ results: [] }), { status: 200 }));
    renderKb(<KbList />);
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
      const view = renderKb(<KbList />);
      const searchCard = await openSearch();
      await user.click(within(searchCard).getByRole("button", { name: "Buscar" }));
      await assertion(searchCard);
      view.unmount();
    };

    await runSearch(new Response(JSON.stringify({ results }), { status: 200 }), async (searchCard) => {
      expect(await within(searchCard).findByText("1 resultados ordenados por similitud.")).toBeInTheDocument();
      expect(within(searchCard).getByText("Respuesta")).toBeInTheDocument();
      expect(within(searchCard).getByText(docs[0].title)).toBeInTheDocument();
      expect(within(searchCard).getByText("v3")).toBeInTheDocument();
      expect(within(searchCard).getByText("Fragmento 1")).toBeInTheDocument();
      expect(within(searchCard).getByText("Similitud 0.900")).toBeInTheDocument();
      expect(within(searchCard).queryByRole("table")).toBeNull();
      expect(within(searchCard).getByText("Respuesta").closest(".kb-search__result-content")).not.toHaveStyle({ maxWidth: "32rem" });
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
    const loadingView = renderKb(<KbList />);
    const loadingCard = await openSearch();
    await user.click(within(loadingCard).getByRole("button", { name: "Buscar" }));
    expect(await within(loadingCard).findByRole("status")).toHaveTextContent("Buscando en la base de conocimientos");
    resolveSearch(new Response(JSON.stringify({ results: [] }), { status: 200 }));
    loadingView.unmount();
    fetchMock.mockRestore();
  });

  it("shows the initial retrieval empty state and hides advanced values until disclosed", async () => {
    renderKb(<KbList data={{ docs }} />);
    const card = screen.getByRole("heading", { name: "Probar recuperación" }).closest(".card") as HTMLElement;
    expect(within(card).getByText("Los resultados aparecerán aquí después de buscar.")).toBeInTheDocument();
    expect(within(card).getByText("Opciones avanzadas").closest("details")).not.toHaveAttribute("open");
    await userEvent.setup().click(within(card).getByText("Opciones avanzadas"));
    expect(within(card).getByLabelText("Máximo de resultados")).toBeInTheDocument();
  });
});

describe("KbList mobile upload story", () => {
  it("opens the add-document dialog from the full-width entry action", async () => {
    renderKb(<KbList data={{ docs }} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Agregar documento" }));
    expect(screen.getByRole("dialog", { name: "Agregar documento" })).toBeInTheDocument();
  });

  it("accepts a dropped file through the accessible dropzone", async () => {
    renderKb(<KbList data={{ docs }} />);
    const card = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    const zone = within(card).getByText("Arrastra un archivo aquí o selecciónalo desde tu equipo").closest("[role='button']") as HTMLElement;
    const file = new File(["content"], "guide.md", { type: "text/markdown" });
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(within(card).getByText("guide.md")).toBeInTheDocument();
    expect(within(card).getByLabelText("Archivo (PDF / MD / TXT / CSV)")).toHaveAttribute("type", "file");
  });
});

describe("KbList API page", () => {
  it("renders the admin document list from GET /panel/api/kb", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ docs }), { status: 200 }));
    renderKb(<KbList />);
    const table = await screen.findByRole("table");
    expect(within(table).getByRole("link", { name: new RegExp(docs[0].title) })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/kb", expect.objectContaining({ credentials: "include" }));
    fetchMock.mockRestore();
  });

  it("renders permission denied when an operador receives 403", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Admin role required" }), { status: 403 }));
    renderKb(<KbList />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    fetchMock.mockRestore();
  });

  it("uploads a document as FormData and refreshes", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }));
    renderKb(<KbList />);
    await screen.findByRole("table");
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    expect(within(addRegion).getByLabelText("Audiencia")).toHaveValue("internal");
    await user.selectOptions(within(addRegion).getByLabelText("Audiencia"), "customer");
    await user.type(within(addRegion).getByLabelText("Título"), "Guide");
    await user.upload(within(addRegion).getByLabelText("Archivo (PDF / MD / TXT / CSV)"), new File(["# Content"], "guide.md", { type: "text/markdown" }));
    await user.click(within(addRegion).getByRole("button", { name: "Agregar" }));
    const request = fetchMock.mock.calls[1][1] as RequestInit;
    expect(request.method).toBe("POST");
    expect(request.body).toBeInstanceOf(FormData);
    expect((request.body as FormData).get("title")).toBe("Guide");
    expect((request.body as FormData).get("file")).toBeInstanceOf(File);
    expect((request.body as FormData).get("visibility")).toBe("customer");
    expect((request.headers as Record<string, string> | undefined)?.["Content-Type"]).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(await screen.findByText("Documento agregado", { selector: ".toast__message" })).toBeInTheDocument();
    fetchMock.mockRestore();
  });

  it("derives the extension only from a real filename suffix", () => {
    const source = readFileSync(resolve(process.cwd(), "src/components/pages/KbList.tsx"), "utf8");
    expect(source).toMatch(/const dot = file\.name\.lastIndexOf\("\."\);/);
    expect(source).toMatch(/const extension = dot > 0 \? file\.name\.slice\(dot\)\.toLowerCase\(\) : "";/);
  });

  it("shows the supported formats and size limit before upload", async () => {
    const user = userEvent.setup();
    renderKb(<KbList data={{ docs }} />);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    const fileInput = within(addRegion).getByLabelText("Archivo (PDF / MD / TXT / CSV)");
    expect(fileInput).toHaveAttribute("accept", ".pdf,.md,.txt,.csv");
    expect(within(addRegion).getByText(/máximo 5 mb/i)).toBeInTheDocument();
    await user.type(within(addRegion).getByLabelText("Título"), "Guide");
    fireEvent.change(fileInput, { target: { files: [new File(["content"], "guide.exe", { type: "application/octet-stream" })] } });
    await user.click(within(addRegion).getByRole("button", { name: "Agregar" }));
    expect(await screen.findByText(/Formato no compatible/, { selector: ".toast__message" })).toBeInTheDocument();
  });

  it("keeps processing feedback at the upload locus and offers upload retry after failure", async () => {
    const user = userEvent.setup();
    let resolveUpload!: (response: Response) => void;
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Response(JSON.stringify({ detail: "upload failed" }), { status: 500 }));
    renderKb(<KbList data={{ docs }} />);
    const addRegion = screen.getByRole("heading", { name: "Agregar documento" }).closest("section") as HTMLElement;
    await user.type(within(addRegion).getByLabelText("Título"), "Guide");
    await user.upload(within(addRegion).getByLabelText("Archivo (PDF / MD / TXT / CSV)"), new File(["content"], "guide.md", { type: "text/markdown" }));
    await user.click(within(addRegion).getByRole("button", { name: "Agregar" }));
    expect(await screen.findByText("No pudimos procesar el documento", { selector: ".toast__message" })).toBeInTheDocument();
    expect(within(addRegion).getByRole("button", { name: "Reintentar carga" })).toBeInTheDocument();

    fetchMock.mockReturnValueOnce(new Promise((resolve) => { resolveUpload = resolve; }));
    await user.click(within(addRegion).getByRole("button", { name: "Reintentar carga" }));
    expect(within(addRegion).getByRole("status")).toHaveTextContent("Procesando documento");
    resolveUpload(new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 }));
    fetchMock.mockRestore();
  });
});
