import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "../domain/AppShell";
import { parsePanelPath, pathForRoute } from "../domain/panelRoutes";
import { KbDocumentDetail } from "./KbDocumentDetail";
import type { KbDocument, User } from "../../types";

const admin: User = { username: "ana", role: "admin" };
const document = {
  id: 1,
  project_id: null,
  title: "Manual de atencion al cliente",
  format: "pdf",
  version: 3,
  active_version: 2,
  active: true,
  visibility: "customer",
  provider: "OpenRouter",
  model: "deepseek-chat",
  cost_meta: 0.000412,
  created_at: "2026-07-10T14:02:00-04:00",
  content: "Contenido del documento.",
} satisfies KbDocument;

beforeEach(() => {
  window.history.replaceState({}, "", "/panel/app/kb/1");
});

afterEach(() => {
  window.history.replaceState({}, "", "/panel/app/");
  vi.restoreAllMocks();
});

describe("KB document detail route", () => {
  it("builds and parses a KB document route", () => {
    expect(pathForRoute({ view: "kb", kbDocId: document.id })).toBe(`/panel/app/kb/${document.id}`);
    expect(parsePanelPath(`/panel/app/kb/${document.id}`)).toEqual({ view: "kb", kbDocId: document.id });
  });

  it("renders the detail route with edit action while keeping the KB list reachable", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input), "http://localhost").pathname;
      if (path === "/panel/api/notifications") return new Response(JSON.stringify({ notifications: [] }), { status: 200 });
      if (path === `/panel/api/kb/${document.id}`) return new Response(JSON.stringify(document), { status: 200 });
      return new Response(JSON.stringify({ docs: [] }), { status: 200 });
    });

    render(<AppShell user={admin} />);

    expect(await screen.findByRole("heading", { name: document.title })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar contenido" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Base de Conocimientos" })).toBeInTheDocument();
  });

  it("renders document and technical facts in the reference summary columns", () => {
    render(<KbDocumentDetail data={document} state="ready" />);

    const surface = screen.getByRole("heading", { name: document.title }).closest("main") as HTMLElement;
    const layout = surface.querySelector(".kb-document__layout") as HTMLElement;
    const left = within(layout).getByRole("region", { name: "Información y detalles técnicos" });
    expect(within(left).getByRole("heading", { name: "Información del documento" })).toBeInTheDocument();
    expect(within(left).getByText("Título")).toBeInTheDocument();
    expect(within(left).getByText(document.title)).toBeInTheDocument();
    for (const label of ["Formato", "Versión activa", "Cantidad de versiones", "Proveedor", "Modelo", "Costo", "Creado"]) {
      expect(within(left).getByText(label)).toBeInTheDocument();
    }
    expect(within(left).getByLabelText("Proveedor")).toHaveValue(document.provider);
    expect(within(left).getByLabelText("Modelo")).toHaveValue(document.model);
  });

  it("renders the reference two-column summary with audience, availability, and technical fields", () => {
    render(<KbDocumentDetail data={document} state="ready" />);

    const layout = screen.getByRole("region", { name: "Resumen del documento" });
    const left = within(layout).getByRole("region", { name: "Información y detalles técnicos" });
    const right = within(layout).getByRole("region", { name: "Audiencia y disponibilidad" });
    const info = within(left).getByRole("heading", { name: "Información del documento" }).closest("section") as HTMLElement;
    expect(within(info).getByText("Versión activa")).toBeInTheDocument();
    expect(within(info).getByText("v2")).toBeInTheDocument();
    expect(within(left).getByRole("group", { name: "Detalles técnicos" })).toBeInTheDocument();
    expect(within(left).getByLabelText("Proveedor")).toBeDisabled();
    expect(within(left).getByLabelText("Modelo")).toBeDisabled();
    expect(within(left).getByLabelText("Costo")).toBeDisabled();

    expect(within(right).getByRole("heading", { name: "Audiencia" })).toBeInTheDocument();
    expect(within(right).getByText("Define quién puede utilizar este documento.")).toBeInTheDocument();
    expect(within(right).getByLabelText("Audiencia del documento")).toHaveValue("customer");
    expect(within(right).getByText("Los documentos internos no se usan para responder a clientes.")).toBeInTheDocument();
    expect(within(right).getByRole("button", { name: "Guardar audiencia" })).toBeDisabled();
    expect(within(right).getByRole("heading", { name: "Disponibilidad" })).toBeInTheDocument();
    expect(within(right).getByText("Activo")).toBeInTheDocument();
    expect(within(right).getByRole("button", { name: "Deshabilitar" })).toBeInTheDocument();
  });

  it("renders the redesigned header and the unified content and versions tab", async () => {
    const user = userEvent.setup();
    render(<KbDocumentDetail data={document} state="ready" />);

    expect(screen.getByText(`#${document.id} · PDF · Creado el 10 jul 2026`)).toBeInTheDocument();
    expect(screen.getAllByText("Activo")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Editar contenido" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contenido y versiones" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Contenido" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Versiones" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Información del documento" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detalles técnicos" })).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(screen.getByText("En uso")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Editar contenido" }));
    expect(screen.getByRole("tab", { name: "Contenido y versiones" })).toHaveAttribute("data-state", "active");
    expect(await screen.findByLabelText("Contenido")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Versiones" })).toBeInTheDocument();
    expect(screen.getByLabelText("Restaurar")).toBeInTheDocument();
  });

  it("previews editor text as markdown and can return to editing", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ...document, content: "# Texto guardado\n\n- Primer punto" }), { status: 200 }));
    render(<KbDocumentDetail data={document} state="ready" />);

    await user.click(screen.getByRole("tab", { name: "Contenido y versiones" }));
    const editor = await screen.findByLabelText("Contenido");
    expect(editor).toHaveValue("# Texto guardado\n\n- Primer punto");
    await user.click(screen.getByRole("button", { name: "Vista previa" }));
    expect(screen.getByRole("heading", { name: "Texto guardado" })).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Primer punto");
    await user.click(screen.getByRole("button", { name: "Editar" }));
    expect(screen.getByLabelText("Contenido")).toBeInTheDocument();
  });

  it("enables a disabled document and refreshes its availability", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input).endsWith("/enable") && init?.method === "POST") {
        return new Response(JSON.stringify({ ok: true, doc: { ...document, active: true } }), { status: 200 });
      }
      return new Response(JSON.stringify({ ...document, active: true }), { status: 200 });
    });
    render(<KbDocumentDetail data={{ ...document, active: false }} state="ready" />);

    expect(screen.getByText("El documento está deshabilitado.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Habilitar" }));

    expect(fetchMock.mock.calls.some(([input, init]) => String(input).endsWith(`/kb/${document.id}/enable`) && init?.method === "POST")).toBe(true);
    expect(await screen.findByText("El documento está habilitado.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deshabilitar" })).toBeInTheDocument();
    fetchMock.mockRestore();
  });

  it("keeps disable confirmation page-owned and names the document", async () => {
    const user = userEvent.setup();
    render(<KbDocumentDetail data={document} state="ready" />);

    await user.click(screen.getByRole("button", { name: "Deshabilitar" }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Confirma la desactivación");
    expect(alert).toHaveTextContent(document.title);
    expect(alert).toHaveTextContent(/el agente dejará de responder/i);
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeInTheDocument();
  });

  it("keeps only the latest confirmation open when workflows overlap", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...document, active: true }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...document, active: false }), { status: 200 }));
    render(<KbDocumentDetail data={document} state="ready" />);

    await user.click(screen.getByRole("tab", { name: "Contenido y versiones" }));
    await user.selectOptions(screen.getByLabelText("Restaurar"), "1");
    await user.click(screen.getByRole("button", { name: "Restaurar" }));
    await user.click(screen.getByRole("tab", { name: "Resumen" }));
    await user.click(screen.getByRole("button", { name: "Deshabilitar" }));

    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Confirmar" })).toHaveLength(1);
    expect(screen.getByRole("alert")).toHaveTextContent("Confirma la desactivación");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith(`/kb/${document.id}/disable`))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith(`/kb/${document.id}/restore`))).toBe(false);
    fetchMock.mockRestore();
  });

  it("renders the detail fetch states", () => {
    const { rerender } = render(<KbDocumentDetail documentId={document.id} data={null} state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando documento");
    rerender(<KbDocumentDetail documentId={document.id} data={null} state="denied" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No tienes permiso para ver este documento");
    rerender(<KbDocumentDetail documentId={document.id} data={null} state="error" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No pudimos cargar el documento");
  });

  it("edits content as a new version from the detail", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") return new Response(JSON.stringify({ ok: true, doc: document }), { status: 200 });
      return new Response(JSON.stringify({ ...document, content: "Contenido existente" }), { status: 200 });
    });
    render(<KbDocumentDetail data={document} state="ready" />);
    await user.click(screen.getByText("Editar contenido"));
    expect(await screen.findByDisplayValue("Contenido existente")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /guardar/i }));
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith(`/kb/${document.id}/edit`))).toBe(true);
    fetchMock.mockRestore();
  });

  it("restores a selected version and changes audience from the detail", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ ...document, content: "Contenido" }), { status: 200 }));
    render(<KbDocumentDetail data={document} state="ready" />);
    await user.click(screen.getByRole("tab", { name: "Contenido y versiones" }));
    await user.selectOptions(screen.getByLabelText("Restaurar"), "1");
    await user.click(screen.getByRole("button", { name: "Restaurar" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/reabrirá como Interno \(solo Lumat\)/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/dejará de usarlo para responder a clientes/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/marques como Cliente y Lumat/i);
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    await user.click(screen.getByRole("tab", { name: "Resumen" }));
    await user.selectOptions(screen.getByLabelText("Audiencia del documento"), "internal");
    await user.click(screen.getByRole("button", { name: "Guardar audiencia" }));
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes(`/kb/${document.id}/restore`))).toBe(true);
    const visibilityCall = fetchMock.mock.calls.find(([input]) => String(input).includes(`/kb/${document.id}/visibility`));
    expect(visibilityCall).toBeDefined();
    expect(JSON.parse(visibilityCall?.[1]?.body as string)).toEqual({ visibility: "internal" });
    fetchMock.mockRestore();
  });

  it.each([400, 422])("maps %i validation failures to safe actionable feedback", async (status) => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") return new Response(JSON.stringify({ detail: "database secret" }), { status });
      return new Response(JSON.stringify({ ...document, content: "Contenido existente" }), { status: 200 });
    });
    render(<KbDocumentDetail data={document} state="ready" />);
    await user.click(screen.getByText("Editar contenido"));
    await screen.findByDisplayValue("Contenido existente");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Revisa los campos e inténtalo nuevamente.");
    expect(screen.getByRole("alert")).not.toHaveTextContent("database secret");
    fetchMock.mockRestore();
  });

  it("keeps mutation feedback safe and disables controls while saving", async () => {
    const user = userEvent.setup();
    let resolve!: (response: Response) => void;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise((next) => { resolve = next; }));
    render(<KbDocumentDetail data={document} state="ready" />);
    await user.click(screen.getByRole("button", { name: "Deshabilitar" }));
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(screen.getByRole("button", { name: "Deshabilitar" })).toBeDisabled();
    resolve(new Response(JSON.stringify({ detail: "admin role required" }), { status: 403 }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para modificar la base de conocimientos");
    expect(screen.getByRole("alert")).not.toHaveTextContent("admin role required");
    fetchMock.mockRestore();
  });
});
