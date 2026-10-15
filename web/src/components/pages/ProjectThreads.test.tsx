import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProjectThreads } from "./ProjectThreads";
import { ToastProvider } from "../primitives/Toast";

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

const thread = (overrides: Partial<Record<string, unknown>> = {}) => ({
  id: 1,
  title: "Hilo",
  proyecto: "ops",
  created_at: null,
  updated_at: "2026-10-14T14:35:00-03:00",
  run_status: null,
  approval_status: null,
  preview: "Consulta registrada",
  ...overrides,
});

const renderThreads = (props: Partial<Parameters<typeof ProjectThreads>[0]> = {}) =>
  render(<ToastProvider><ProjectThreads projectSlug="ops" projectName="TestProject" {...props} /></ToastProvider>);

describe("ProjectThreads", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lists the project threads with title, preview and per-row actions", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({
      threads: [thread({ id: 5, title: "Revisión de herramientas", preview: "Consulta de las herramientas disponibles." })],
    }));

    renderThreads();

    expect(await screen.findByText("Revisión de herramientas")).toBeInTheDocument();
    expect(screen.getByText("Consulta de las herramientas disponibles.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hilos del proyecto (1)" })).toBeInTheDocument();
    expect(screen.getByText("Conversaciones asociadas a TestProject.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Abrir hilo/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Acciones de Revisión de herramientas" })).toBeInTheDocument();
  });

  it("opens a thread through the callback", async () => {
    const user = userEvent.setup();
    const onOpenThread = vi.fn();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ threads: [thread({ id: 7, title: "Plan de mejoras" })] }));

    renderThreads({ onOpenThread });

    await user.click(await screen.findByRole("button", { name: /Abrir hilo/ }));
    expect(onOpenThread).toHaveBeenCalledWith(7, "ops");
  });

  it("creates a new thread and opens it", async () => {
    const user = userEvent.setup();
    const onOpenThread = vi.fn();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ threads: [thread()] }));
    fetchMock.mockResolvedValueOnce(response({ threads: [thread({ id: 9 })] }));
    fetchMock.mockImplementation(async (input, init) => {
      if (String(input).includes("/panel/api/chat/threads") && init?.method === "POST") return response({ thread: { id: 42 }, messages: [] }, 201);
      return response({ threads: [thread({ id: 9 })] });
    });

    renderThreads({ onOpenThread });

    await user.click(await screen.findByRole("button", { name: "Nuevo hilo" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads", expect.objectContaining({ method: "POST", body: JSON.stringify({ proyecto: "ops" }) })));
    expect(onOpenThread).toHaveBeenCalledWith(42, "ops");
  });

  it("shows the real empty state and opens the assistant history", async () => {
    const user = userEvent.setup();
    const onOpenHistory = vi.fn();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ threads: [] }));

    renderThreads({ onOpenHistory });

    expect(await screen.findByText("Aún no hay hilos en este proyecto")).toBeInTheDocument();
    expect(screen.getByText("Por ahora, consulta tus conversaciones desde el historial del asistente.")).toBeInTheDocument();
    expect(screen.getByText("El historial del asistente reúne las conversaciones de todos tus proyectos.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Abrir historial/ }));
    expect(onOpenHistory).toHaveBeenCalledWith("ops");
  });

  it("shows the unavailable state when the list is denied", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "forbidden" }), { status: 403 }));

    renderThreads();

    expect(await screen.findByText("Los hilos de este proyecto aún no están disponibles")).toBeInTheDocument();
    expect(screen.getByText("No disponible")).toBeInTheDocument();
  });

  it("renames a thread through the row menu", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ threads: [thread({ id: 5, title: "Viejo" })] }));
    fetchMock.mockImplementation(async (input, init) => {
      if (String(input).includes("/panel/api/chat/threads/5") && init?.method === "PATCH") return response({ thread: thread({ id: 5, title: "Nuevo" }) });
      return response({ threads: [thread({ id: 5, title: "Viejo" })] });
    });

    renderThreads();
    await user.click(await screen.findByRole("button", { name: "Acciones de Viejo" }));
    await user.click(screen.getByRole("menuitem", { name: "Renombrar" }));

    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Nombre del hilo"), { target: { value: "Nuevo" } });
    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads/5", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ title: "Nuevo" }) })));
  });

  it("deletes a thread after confirming in the dialog", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(response({ threads: [thread({ id: 5, title: "Descartable" })] }));
    fetchMock.mockImplementation(async (input, init) => {
      if (String(input).includes("/panel/api/chat/threads/5") && init?.method === "DELETE") return response({ ok: true });
      return response({ threads: [thread({ id: 5, title: "Descartable" })] });
    });

    renderThreads();
    await user.click(await screen.findByRole("button", { name: "Acciones de Descartable" }));
    await user.click(screen.getByRole("menuitem", { name: "Eliminar hilo" }));

    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Eliminar hilo" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads/5", expect.objectContaining({ method: "DELETE" })));
    expect(await screen.findByText("Hilo eliminado.")).toBeInTheDocument();
  });

  it("filters the list by the search query", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response({
      threads: [thread({ id: 1, title: "Revisión de herramientas" }), thread({ id: 2, title: "Plan de mejoras" })],
    }));

    renderThreads();
    await screen.findByText("Plan de mejoras");

    await user.type(screen.getByLabelText("Buscar hilo"), "sin-coincidencia");

    expect(await screen.findByText("No encontramos hilos. Prueba con otro nombre.", {}, { timeout: 2000 })).toBeInTheDocument();
  });
});
