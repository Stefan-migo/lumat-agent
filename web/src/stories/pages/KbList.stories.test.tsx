import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { docs } from "./_shared/mockData/kb";
import { kbStatusLabel } from "./_shared/toneMaps";
import { KbList } from "../../components/pages/KbList";
import { KbListView, KbListEmpty } from "./KbList.stories";

describe("KbList page", () => {
  it("renders the Spanish page title and upload surface", () => {
    render(<KbListView />);
    expect(screen.getByRole("heading", { name: "Base de conocimientos" })).toBeInTheDocument();
    const addCard = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    expect(within(addCard).getByLabelText(/título/i)).toBeInTheDocument();
    expect(within(addCard).getByLabelText(/archivo/i)).toBeInTheDocument();
    expect(within(addCard).getByRole("button", { name: "Agregar" })).toBeInTheDocument();
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
    const addCard = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    expect(within(addCard).getByRole("option", { name: "Cliente y Lumat" })).toBeInTheDocument();
    expect(within(addCard).getByRole("option", { name: "Interno (solo Lumat)" })).toBeInTheDocument();
  });

  it("keeps provider/model advanced keys out of ordinary table rows", () => {
    render(<KbListView />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    expect(within(row).queryByText(`${docs[0].provider} / ${docs[0].model}`)).toBeNull();
  });

  it("renders processing and error state banners", () => {
    const { rerender } = render(<KbListView state="processing" />);
    expect(screen.getByRole("status")).toHaveTextContent("Procesando documento");
    rerender(<KbListView state="error" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos procesar el documento");
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
    const addCard = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    expect(within(addCard).getByLabelText("Audiencia")).toHaveValue("internal");
    await user.selectOptions(within(addCard).getByLabelText("Audiencia"), "customer");
    await user.type(within(addCard).getByLabelText("Título"), "Guide");
    await user.upload(within(addCard).getByLabelText(/archivo/i), new File(["# Content"], "guide.md", { type: "text/markdown" }));
    await user.click(within(addCard).getByRole("button", { name: "Agregar" }));
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
});
