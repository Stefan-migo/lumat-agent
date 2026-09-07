import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { docs } from "./_shared/mockData/kb";
import { kbStatusLabel } from "./_shared/toneMaps";
import { KbList } from "../../components/pages/KbList";
import { KbListView, KbListEmpty } from "./KbList.stories";

describe("KbList page story (T5.2 / S6 DS-UI-COPY/STATES/LABELS)", () => {
  it("renders the Spanish page title 'Base de conocimientos'", () => {
    render(<KbListView />);
    expect(screen.getByRole("heading", { name: "Base de conocimientos" })).toBeInTheDocument();
  });

  it("renders the add-document Card with approved Spanish labels (Agregar documento / Título / Archivo / Agregar)", () => {
    render(<KbListView />);
    const addCard = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    const withinCard = within(addCard);
    expect(withinCard.getByLabelText(/título/i)).toBeInTheDocument();
    expect(withinCard.getByLabelText(/archivo/i)).toBeInTheDocument();
    expect(withinCard.getByRole("button", { name: "Agregar" })).toBeInTheDocument();
  });

  it("renders the docs DataTable with approved Spanish headers (#, Título, Formato, Versión, Estado, Costo)", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const first = docs[0];

    // # column
    const idCell = within(table).getByText(`#${first.id}`);
    expect(idCell).toBeInTheDocument();
    const row = idCell.closest("tr") as HTMLElement;
    expect(row).not.toBeNull();

    // Título
    expect(within(table).getByText(first.title)).toBeInTheDocument();
    // Formato
    expect(within(row).getByText(first.format)).toBeInTheDocument();
    // Versión (version + active_version)
    expect(within(row).getByText(`${first.version} (activa: ${first.active_version})`)).toBeInTheDocument();
    // Estado via approved kbStatusLabel badge (never a raw 'active'/'inactive')
    const stateKey = first.active ? "activo" : "deshabilitado";
    const estadoLabel = kbStatusLabel(stateKey);
    expect(within(row).getByText(estadoLabel)).toBeInTheDocument();
    // Costo 6-decimal USD (formatted like '%.6f')
    expect(within(row).getByText("$0.000412")).toBeInTheDocument();
  });

  it("renders an approved Spanish status label per document (triangulation across activo/deshabilitado)", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    // Cover a different status than the first (e.g. an inactive doc → "Deshabilitado").
    // Disambiguate the status badge (data-tone) from the plain actions-cell note.
    const inactive = docs.find((d) => !d.active)!;
    const rowInactive = within(table).getByText(`#${inactive.id}`).closest("tr")!;
    const inactiveBadge = within(rowInactive)
      .getAllByText(kbStatusLabel("deshabilitado"))
      .find((el) => el.getAttribute("data-tone") === "neutral");
    expect(inactiveBadge, "the inactive badge should render the approved label").toBeDefined();
    const active = docs.find((d) => d.active)!;
    const rowActive = within(table).getByText(`#${active.id}`).closest("tr")!;
    const activeBadge = within(rowActive)
      .getAllByText(kbStatusLabel("activo"))
      .find((el) => el.getAttribute("data-tone") === "success");
    expect(activeBadge, "the active badge should render the approved label").toBeDefined();
  });

  it("keeps raw provider/model advanced keys OUT of the ordinary table row", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const row = within(table).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    // The raw "provider / model" pair must NOT appear among the ordinary table cells.
    expect(within(row).queryByText(`${docs[0].provider} / ${docs[0].model}`)).toBeNull();
    // Cost stays in the table (a normal column); provider/model lives in an advanced detail.
    expect(within(row).getByText("$0.000412")).toBeInTheDocument();
  });

  it("renders per-doc Edit accordion as a native <details> with Spanish action labels", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const row = within(table).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    const details = within(row).getByRole("group");
    expect(details.tagName).toBe("DETAILS");
    expect(within(details).getByText("Editar")).toBeInTheDocument();
    expect(within(details).getByRole("button", { name: /guardar/i })).toBeInTheDocument();
    expect(within(details).getByLabelText(/título/i)).toBeInTheDocument();
    expect(within(details).getByLabelText(/contenido/i)).toBeInTheDocument();
  });

  it("separates and explains the advanced provider/model detail in plain Spanish", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const providerRow = docs.find((d) => d.provider && d.model)!;
    const provider = providerRow.provider!;
    const model = providerRow.model!;
    const row = within(table).getByText(`#${providerRow.id}`).closest("tr") as HTMLElement;
    const details = within(row).getByRole("group");
    // The raw provider/model values now appear only inside the explained
    // advanced detail, each as its own labelled value (not in ordinary controls).
    expect(within(details).getByText(provider)).toBeInTheDocument();
    expect(within(details).getByText(model)).toBeInTheDocument();
    expect(within(details).getByText(/detalle técnico · proveedor y modelo/i)).toBeInTheDocument();
    expect(within(details).getByText(/no es necesario cambiarlos en el uso habitual/i)).toBeInTheDocument();
  });

  it("renders Disable button for active docs and Restore select for versioned rows (Spanish labels)", () => {
    render(<KbListView />);
    const table = screen.getByRole("table");
    const activeDoc = docs.find((d) => d.active)!;
    const activeRow = within(table).getByText(`#${activeDoc.id}`).closest("tr") as HTMLElement;
    expect(within(activeRow).getByRole("button", { name: "Deshabilitar" })).toBeInTheDocument();

    const versionedDoc = docs.find((d) => d.version > 1)!;
    const versionedRow = within(table).getByText(`#${versionedDoc.id}`).closest("tr") as HTMLElement;
    const restoreSelect = within(versionedRow).getByLabelText(`Restaurar doc ${versionedDoc.id}`);
    expect(restoreSelect.tagName).toBe("SELECT");
    expect(within(restoreSelect).getByRole("option", { name: "v1" })).toBeInTheDocument();
    expect(within(versionedRow).getByRole("button", { name: "Restaurar" })).toBeInTheDocument();
  });

  it("renders the disable-confirmation state naming the document and its agent-answer impact (DS-UI-STATES)", () => {
    render(<KbListView state="disable-confirmation" />);
    const activeDoc = docs.find((d) => d.active)!;
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText("Confirma la desactivación")).toBeInTheDocument();
    expect(within(alert).getByText(new RegExp(activeDoc.title))).toBeInTheDocument();
    expect(within(alert).getByText(/el agente dejará de responder/i)).toBeInTheDocument();
  });

  it("renders a processing state banner pairing status role with a visible label (DS-UI-STATES)", () => {
    render(<KbListView state="processing" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Procesando documento")).toBeInTheDocument();
  });

  it("renders an error state banner pairing alert role with a visible label (DS-UI-STATES)", () => {
    render(<KbListView state="error" />);
    const banner = screen.getByRole("alert");
    expect(within(banner).getByText("No pudimos procesar el documento")).toBeInTheDocument();
  });
});

describe("KbList Empty story", () => {
  it("renders the empty state with the approved Spanish message", () => {
    render(<KbListEmpty />);
    expect(screen.getByText("No hay documentos")).toBeInTheDocument();
  });
});

describe("KbList API page", () => {
  it("renders the admin document list from GET /panel/api/kb", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ docs }), { status: 200 }));

    render(<KbList />);
    await screen.findByText(docs[0].title);

    expect(await screen.findByText(docs[0].title)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/kb", expect.objectContaining({ credentials: "include" }));
    fetchMock.mockRestore();
  });

  it("renders permission denied when an operador receives 403 without crashing", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Admin role required" }), { status: 403 }),
    );

    render(<KbList />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    expect(screen.queryByText("No pudimos cargar la base de conocimientos")).toBeNull();
    fetchMock.mockRestore();
  });

  it("uploads a document as FormData without manually setting Content-Type, then refreshes", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ docs }), { status: 200 }));

    render(<KbList />);
    await screen.findByText(docs[0].title);
    const file = new File(["# Content"], "guide.md", { type: "text/markdown" });
    const addCard = screen.getByRole("heading", { name: "Agregar documento" }).closest(".card") as HTMLElement;
    await user.type(within(addCard).getByLabelText("Título"), "Guide");
    await user.upload(within(addCard).getByLabelText(/archivo/i), file);
    await user.click(within(addCard).getByRole("button", { name: "Agregar" }));

    const uploadRequest = fetchMock.mock.calls[1][1] as RequestInit;
    expect(uploadRequest.method).toBe("POST");
    expect(uploadRequest.body).toBeInstanceOf(FormData);
    expect((uploadRequest.body as FormData).get("title")).toBe("Guide");
    expect((uploadRequest.body as FormData).get("file")).toBeInstanceOf(File);
    expect((uploadRequest.headers as Record<string, string> | undefined)?.["Content-Type"]).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    fetchMock.mockRestore();
  });

  it("posts edit, disable, and restore JSON mutations and refreshes after each commit", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") return new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 });
      return new Response(JSON.stringify({ docs }), { status: 200 });
    });

    render(<KbList data={{ docs }} />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    await user.click(within(row).getByText("Editar"));
    await user.click(within(row).getByRole("button", { name: /guardar/i }));
    await user.click(within(row).getByRole("button", { name: "Deshabilitar" }));
    const restoreRow = within(screen.getByRole("table")).getByText(`#${docs.find((doc) => doc.version > 1)!.id}`).closest("tr") as HTMLElement;
    await user.click(within(restoreRow).getByRole("button", { name: "Restaurar" }));

    const mutationCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(mutationCalls).toHaveLength(3);
    expect((mutationCalls[0][1]?.body as string)).toContain('"content"');
    expect((mutationCalls[1][0] as string)).toContain(`/kb/${docs[0].id}/disable`);
    expect((mutationCalls[2][0] as string)).toContain(`/kb/${docs.find((doc) => doc.version > 1)!.id}/restore`);
    expect(fetchMock.mock.calls.filter(([, init]) => !init?.method || init.method === "GET")).toHaveLength(3);
    fetchMock.mockRestore();
  });

  it.each([400, 422])("maps %i validation failures to safe actionable feedback", async (status) => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "database secret" }), { status }));
    render(<KbList data={{ docs }} />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    await user.click(within(row).getByText("Editar"));
    await user.click(within(row).getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("heading", { name: /revisa los campos/i })).toBeInTheDocument();
    expect(screen.getByRole("alert")).not.toHaveTextContent("database secret");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fetchMock.mockRestore();
  });

  it("shows permission state for a mutation denied with 403", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "admin role required" }), { status: 403 }),
    );
    render(<KbList data={{ docs }} />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    await user.click(within(row).getByRole("button", { name: "Deshabilitar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para modificar la base de conocimientos");
    expect(screen.getByRole("alert")).not.toHaveTextContent("admin role required");
    fetchMock.mockRestore();
  });

  it("disables mutation controls while a commit is in flight", async () => {
    const user = userEvent.setup();
    let resolve!: (response: Response) => void;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise((next) => { resolve = next; }));
    render(<KbList data={{ docs }} />);
    const row = within(screen.getByRole("table")).getByText(`#${docs[0].id}`).closest("tr") as HTMLElement;
    const disable = within(row).getByRole("button", { name: "Deshabilitar" });
    await user.click(disable);
    expect(disable).toBeDisabled();
    resolve(new Response(JSON.stringify({ ok: true, doc: docs[0] }), { status: 200 }));
    fetchMock.mockRestore();
  });
});
