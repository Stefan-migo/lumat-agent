import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "../domain/AppShell";
import { parsePanelPath, pathForRoute } from "../domain/panelRoutes";
import { KbDocumentDetail } from "./KbDocumentDetail";
import { docs } from "../../stories/pages/_shared/mockData/kb";
import type { KbDocument, User } from "../../types";

const admin: User = { username: "ana", role: "admin" };
const document = { ...docs[0], content: "Contenido del documento." } satisfies KbDocument;

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

  it("renders the detail for a document route with the shared back control", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(String(input), "http://localhost").pathname;
      if (path === "/panel/api/notifications") return new Response(JSON.stringify({ notifications: [] }), { status: 200 });
      if (path === `/panel/api/kb/${document.id}`) return new Response(JSON.stringify(document), { status: 200 });
      return new Response(JSON.stringify({ docs: [] }), { status: 200 });
    });

    render(<AppShell user={admin} />);

    expect(await screen.findByRole("heading", { name: document.title })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver a documentos" })).toBeInTheDocument();
  });

  it("renders labelled identity facts in a rail and operations in the main region", () => {
    render(<KbDocumentDetail data={document} state="ready" />);

    const surface = screen.getByRole("heading", { name: document.title }).closest("main") as HTMLElement;
    const rail = surface.querySelector(".client-ficha__rail") as HTMLElement;
    expect(surface.querySelector(".client-ficha__rail")).toBeInTheDocument();
    expect(surface.querySelector(".client-ficha__main")).toBeInTheDocument();
    expect(within(rail).getByText("Título")).toBeInTheDocument();
    expect(within(rail).getByText(document.title)).toBeInTheDocument();
    for (const label of ["Formato", "Versión activa", "Cantidad de versiones", "Estado", "Audiencia", "Proveedor", "Modelo", "Costo", "Creado"]) {
      expect(within(rail).getByText(label)).toBeInTheDocument();
    }
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
    await user.selectOptions(screen.getByLabelText("Restaurar"), "1");
    await user.click(screen.getByRole("button", { name: "Restaurar" }));
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    await user.selectOptions(screen.getByLabelText("Audiencia"), "internal");
    await user.click(screen.getByRole("button", { name: "Cambiar audiencia" }));
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes(`/kb/${document.id}/restore`))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes(`/kb/${document.id}/visibility`))).toBe(true);
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
