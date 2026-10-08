import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { AgentChat } from "./AgentChat";

describe("AssistantWorkspace", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
    window.history.replaceState({}, "", "/");
  });

  it("renders the three workspace regions with the existing chat in the center", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ threads: [], projects: [] }), { status: 200 }),
    );

    render(<AgentChat role="admin" />);

    expect(screen.queryByRole("navigation", { name: "Controles del espacio de trabajo" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear hilo" })).not.toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Proyectos" })).toBeInTheDocument();
    const thread = screen.getByRole("region", { name: "Área del hilo" });
    expect(within(thread).getByRole("heading", { name: "Asistente Lumat" })).toBeInTheDocument();
    expect(await within(thread).findByRole("heading", { name: "Comienza una conversación" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Contexto del hilo" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contexto" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Actividad" })).toBeInTheDocument();
  });

  it("loads real projects, filters by name, and expands project navigation and agent state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
        { id: 2, slug: "archivo", name: "Archivo", purpose: "Registro", status: "archived", created_at: null, updated_at: null },
      ] }), { status: 200 });
      if (url.includes("/threads?")) return new Response(JSON.stringify({ threads: [{ id: 42, title: "Nuevo hilo", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" />);

    const project = await screen.findByText("Operaciones");
    expect(project).toBeInTheDocument();
    expect(screen.getByText("Archivo")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar proyecto" }), { target: { value: "arch" } });
    await waitFor(() => expect(screen.queryByText("Operaciones")).not.toBeInTheDocument());
    expect(screen.getByText("Archivo")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar proyecto" }), { target: { value: "operaciones" } });
    await waitFor(() => expect(screen.getByText("Operaciones")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Operaciones").closest("button")!);
    expect(screen.getByRole("link", { name: "Contexto y archivos" })).toHaveAttribute("href", "/panel/app/projects/operaciones");
    expect(screen.getByRole("link", { name: "Historial de hilos" })).toHaveAttribute("href", "/panel/app/chat?proyecto=operaciones");
    expect(screen.getByRole("heading", { name: "Agentes del proyecto" })).toBeInTheDocument();
    expect(screen.getByText("La gestión de agentes por proyecto todavía no está disponible.")).toBeInTheDocument();
    expect(screen.getByLabelText("Cantidad no disponible")).toHaveTextContent("—");
    expect(screen.getByRole("button", { name: "Agregar agente" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Contraer Operaciones" }));
    expect(screen.queryByRole("link", { name: "Contexto y archivos" })).not.toBeInTheDocument();
  });

  it("shows a retryable error instead of fabricated project rows", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ detail: "failure" }), { status: 500 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar los proyectos");
    expect(screen.queryByText("Operaciones")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });

  it("creates a project through the API and refreshes the project list", async () => {
    const project = { id: 3, slug: "nuevo-proyecto", name: "Nuevo Proyecto", purpose: "Organizar trabajo", status: "active", created_at: null, updated_at: null };
    let projectRequests = 0;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/projects" && init?.method === "POST") {
        expect(JSON.parse(String(init.body))).toEqual({ slug: "nuevo-proyecto", name: "Nuevo Proyecto", purpose: "Organizar trabajo" });
        return new Response(JSON.stringify({ project }), { status: 201 });
      }
      if (url.includes("/panel/api/projects")) {
        projectRequests += 1;
        return new Response(JSON.stringify({ projects: projectRequests > 1 ? [project] : [] }), { status: 200 });
      }
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);

    fireEvent.click(await screen.findByRole("button", { name: "Crear proyecto" }));
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Nuevo Proyecto" } });
    expect(screen.getByLabelText("Slug")).toHaveValue("nuevo-proyecto");
    fireEvent.change(screen.getByLabelText("Propósito"), { target: { value: "Organizar trabajo" } });
    fireEvent.click(within(screen.getByRole("dialog", { name: "Crear proyecto" })).getByRole("button", { name: "Crear proyecto" }));

    expect((await screen.findAllByText("Nuevo Proyecto")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("dialog", { name: "Crear proyecto" })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalled();
  });

  it("keeps the project dialog open and reports API failures honestly", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/projects" && init?.method === "POST") return new Response(JSON.stringify({ detail: "failure" }), { status: 500 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);

    fireEvent.click(await screen.findByRole("button", { name: "Crear proyecto" }));
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Proyecto" } });
    fireEvent.change(screen.getByLabelText("Slug"), { target: { value: "proyecto" } });
    fireEvent.change(screen.getByLabelText("Propósito"), { target: { value: "Propósito" } });
    fireEvent.click(within(screen.getByRole("dialog", { name: "Crear proyecto" })).getByRole("button", { name: "Crear proyecto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos crear el proyecto");
    expect(screen.getByRole("dialog", { name: "Crear proyecto" })).toBeInTheDocument();
  });

  it("toggles both panes from the thread header at narrow widths", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 640 });

    render(<AgentChat role="admin" />);
    const projectsToggle = screen.getByRole("button", { name: "Mostrar u ocultar proyectos" });
    const contextToggle = screen.getByRole("button", { name: "Mostrar u ocultar el panel de contexto" });
    expect(projectsToggle).toHaveAttribute("aria-expanded", "false");
    expect(projectsToggle).toHaveAttribute("aria-controls", "assistant-workspace-projects");
    expect(contextToggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(projectsToggle);
    expect(projectsToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("complementary", { name: "Proyectos" })).toBeVisible();
    fireEvent.click(contextToggle);
    expect(contextToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("complementary", { name: "Contexto del hilo" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Cerrar paneles" })).toBeInTheDocument();
  });

  it("lists recent threads as navigable tabs and exposes the real create action", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/chat/threads" && init?.method === "POST") return new Response(JSON.stringify({
        thread: { id: 42, proyecto: "operaciones", status: "open" }, messages: [],
      }), { status: 201 });
      if (url.includes("/panel/api/chat/threads?")) return new Response(JSON.stringify({ threads: [
        { id: 11, title: "Agenda semanal", created_at: null, updated_at: null, run_status: null, approval_status: null },
        { id: 12, title: "Revisión KB", created_at: null, updated_at: null, run_status: null, approval_status: null },
      ] }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
      ] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    const onThreadOpened = vi.fn();

    render(<AgentChat role="admin" onThreadOpened={onThreadOpened} />);

    const tab = await screen.findByRole("button", { name: "Revisión KB" });
    fireEvent.click(screen.getByRole("button", { name: "Crear nuevo hilo" }));
    await waitFor(() => expect(onThreadOpened).toHaveBeenCalledWith(42));
    fireEvent.click(tab);
    expect(window.location.search).toBe("?proyecto=operaciones&thread_id=12");
    expect(screen.getByRole("button", { name: "Crear nuevo hilo" })).toBeInTheDocument();
  });

  it("shows the active thread title and real project name without a competing page title", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones&thread_id=7");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
      ] }), { status: 200 });
      if (url.includes("/panel/api/chat/threads?")) return new Response(JSON.stringify({ threads: [
        { id: 7, title: "Agenda semanal", created_at: null, updated_at: null, run_status: null, approval_status: null },
      ] }), { status: 200 });
      if (url.endsWith("/threads/7")) return new Response(JSON.stringify({
        thread: { id: 7, proyecto: "operaciones", status: "open", assistant_state: { events: [{ run_id: "run-7", evidence: [{ tool: "search_kb", status: "completed", detail: "Se encontraron documentos." }] }] } },
        messages: [], attachments: [{ id: 3, thread_id: 7, filename: "manual.pdf", kind: "document", content_type: "application/pdf", size: 100 }],
      }), { status: 200 });
      if (url.includes("/assistant/capabilities")) return new Response(JSON.stringify({ tools: [{ name: "search_kb", description: "Search", read_only: true, write: false }], personas: [], prompts: [], kb_available: true, memory_available: false }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" onThreadOpened={() => undefined} />);

    expect(await screen.findByRole("heading", { name: "Agenda semanal", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Asistente Lumat", level: 1 })).not.toBeInTheDocument();
    expect(screen.getByText("Proyecto: Operaciones")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Acciones del hilo" })).toBeInTheDocument();
    expect(screen.getByText("Gestión")).toBeInTheDocument();
    expect(screen.getAllByText("manual.pdf")).toHaveLength(3);
    expect(screen.getByRole("tab", { name: "Actividad" })).toBeInTheDocument();
  });
});
