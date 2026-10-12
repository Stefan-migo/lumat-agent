import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { InternalChatThreadSummary } from "../../types";
import { parsePanelPath, pathForRoute } from "../domain/panelRoutes";
import { AgentChat } from "./AgentChat";
import { groupThreadsByDate } from "./threadDateGroups";

describe("groupThreadsByDate", () => {
  it("groups by last activity, uses creation as a fallback, and sorts newest first", () => {
    const thread = (id: number, updated_at: string | null, created_at: string | null = null): InternalChatThreadSummary => ({ id, title: `Thread ${id}`, proyecto: "ops", updated_at, created_at, run_status: null, approval_status: null });
    const groups = groupThreadsByDate([
      thread(1, "2026-10-12T12:00:00-03:00"), thread(2, "2026-10-11T12:00:00-03:00"),
      thread(3, "2026-10-05T12:00:00-03:00"), thread(4, null, "2026-10-12T09:00:00-03:00"),
      thread(5, "2026-10-12T08:00:00-03:00"),
    ], new Date("2026-10-12T15:00:00Z"));
    expect(groups.map(({ label, threads }) => [label, threads.map(({ id }) => id)])).toEqual([["Hoy", [1, 4, 5]], ["Ayer", [2]], ["5 oct", [3]]]);
  });
});

describe("AssistantWorkspace", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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
    expect(screen.getByRole("heading", { name: "Asistente Lumat", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Proyectos", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agentes", level: 3 })).toBeInTheDocument();
    const thread = screen.getByRole("region", { name: "Área del hilo" });
    expect(within(thread).queryByRole("heading", { name: "Asistente Lumat" })).not.toBeInTheDocument();
    expect(await within(thread).findByRole("heading", { name: /Buenos días|Buenas tardes|Buenas noches/ })).toBeInTheDocument();
    expect(within(thread).queryByRole("navigation", { name: "Hilos abiertos" })).not.toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Contexto del hilo" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contexto" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Actividad" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detalle del hilo" })).toBeInTheDocument();
    expect(screen.getByText("Sin título")).toBeInTheDocument();
    for (const title of ["Proyecto", "Recursos del proyecto", "Capacidades del asistente", "Archivos del hilo", "Artefactos del hilo", "Fuentes del hilo"]) {
      expect(screen.getByRole("button", { name: new RegExp(title) })).toHaveAttribute("aria-controls");
    }
    expect(screen.getByRole("button", { name: "Proyecto" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Los adjuntos y resultados pertenecen a este hilo.")).toBeInTheDocument();
    const resourcesToggle = screen.getByRole("button", { name: /Recursos del proyecto/ });
    fireEvent.click(resourcesToggle);
    expect(resourcesToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Selección de recursos aún no disponible.")).toBeVisible();
    fireEvent.click(resourcesToggle);
    expect(resourcesToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Selección de recursos aún no disponible.")).not.toBeVisible();
  });

  it("loads real projects, filters by name, and expands project navigation and agent state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/agents")) return new Response(JSON.stringify({ agents: [], latest_run: null }), { status: 200 });
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
    expect(screen.getByRole("button", { name: "Contexto y archivos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Historial de hilos" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar agente" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Contraer Operaciones" }));
    expect(screen.queryByRole("link", { name: "Contexto y archivos" })).not.toBeInTheDocument();
  });

  it("opens project context as a tab and closes it without changing thread tab behavior", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/panel/api/projects/operaciones")) return new Response(JSON.stringify({ project: { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", config: { instructions: "Instrucciones del proyecto", skills: [] }, created_at: null, updated_at: null } }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [{ id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.includes("/planning/sessions")) return new Response(JSON.stringify({ sessions: [] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      if (url.includes("/project-files")) return new Response(JSON.stringify({ files: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);
    fireEvent.click(await screen.findByRole("button", { name: "Expandir Operaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Contexto y archivos" }));
    expect(window.location.search).toBe("?context=operaciones");
    expect(await screen.findByRole("button", { name: "Configuración · Operaciones" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Instrucciones del proyecto" })).toBeInTheDocument();
    const projectPage = screen.getByRole("main");
    for (const label of ["Contexto", "Hilos", "Agentes", "Skills"]) expect(within(projectPage).getByRole("tab", { name: label })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Acciones de Configuración · Operaciones" })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Acciones de Configuración · Operaciones" }));
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Cerrar pestaña" }));
    expect(window.location.search).toBe("");
    expect(screen.queryByRole("heading", { name: "Archivos y conocimiento" })).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /Buenos días|Buenas tardes|Buenas noches/ })).toBeInTheDocument();
  });

  it("shows a retryable error instead of fabricated project rows", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/active-runs")) return new Response(JSON.stringify({ active_runs: [] }), { status: 200 });
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
      if (url.endsWith("/agents")) return new Response(JSON.stringify({ agents: [], latest_run: null }), { status: 200 });
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

    await userEvent.setup().click(screen.getByRole("button", { name: "Acciones de proyectos" }));
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Nuevo proyecto" }));
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
      if (url.endsWith("/active-runs")) return new Response(JSON.stringify({ active_runs: [] }), { status: 200 });
      if (url === "/panel/api/projects" && init?.method === "POST") return new Response(JSON.stringify({ detail: "failure" }), { status: 500 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Acciones de proyectos" }));
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Nuevo proyecto" }));
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Proyecto" } });
    fireEvent.change(screen.getByLabelText("Slug"), { target: { value: "proyecto" } });
    fireEvent.change(screen.getByLabelText("Propósito"), { target: { value: "Propósito" } });
    fireEvent.click(within(screen.getByRole("dialog", { name: "Crear proyecto" })).getByRole("button", { name: "Crear proyecto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos crear el proyecto");
    expect(screen.getByRole("dialog", { name: "Crear proyecto" })).toBeInTheDocument();
  });

  it("toggles each pane from its own header and keeps collapsed rails reopenable", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 640 });

    render(<AgentChat role="admin" />);
    const projectsToggle = screen.getByRole("button", { name: "Expandir panel de proyectos" });
    const contextToggle = screen.getByRole("button", { name: "Abrir panel del hilo" });
    const contextHeader = screen.getByRole("heading", { name: "Detalle del hilo" }).closest("header")!;
    expect(within(contextHeader).getAllByRole("button")).toHaveLength(1);
    expect(contextToggle.querySelector("svg")).toHaveClass("lucide-panel-right");
    expect(projectsToggle).toHaveAttribute("aria-expanded", "false");
    expect(projectsToggle).toHaveAttribute("aria-controls", "assistant-workspace-projects");
    expect(contextToggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(projectsToggle);
    const collapseProjects = screen.getByRole("button", { name: "Contraer panel de proyectos" });
    expect(collapseProjects).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("complementary", { name: "Proyectos" })).toBeVisible();
    fireEvent.click(contextToggle);
    const closeContext = screen.getByRole("button", { name: "Cerrar panel del hilo" });
    expect(closeContext.querySelector("svg")).toHaveClass("lucide-panel-right");
    expect(closeContext).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("complementary", { name: "Contexto del hilo" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Cerrar paneles" })).toBeInTheDocument();
    fireEvent.click(collapseProjects);
    expect(screen.getByRole("button", { name: "Expandir panel de proyectos" })).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(closeContext);
    expect(screen.getByRole("button", { name: "Abrir panel del hilo" })).toHaveAttribute("aria-expanded", "false");
    expect(within(screen.getByRole("region", { name: "Área del hilo" })).queryByRole("button", { name: /panel de/ })).not.toBeInTheDocument();
  });

  it("limits default chat controls to admin and operator and supports default thread creation/history", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/chat/threads" && init?.method === "POST") return new Response(JSON.stringify({ thread: { id: 71, proyecto: "default", status: "open" }, messages: [] }), { status: 201 });
      if (url.includes("proyecto=default")) return new Response(JSON.stringify({ threads: [{ id: 72, title: "Consulta general", proyecto: "default", created_at: null, updated_at: null, run_status: null, approval_status: null }] }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    const { unmount } = render(<AgentChat role="admin" onThreadOpened={(id) => window.history.replaceState({}, "", `/panel/app/chat?thread_id=${id}`)} />);
    expect(await screen.findByRole("button", { name: "Nueva conversación" })).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("complementary", { name: "Proyectos" })).getByRole("button", { name: "Historial" }));
    fireEvent.click(await screen.findByRole("button", { name: "Consulta general" }));
    expect(window.location.search).toContain("thread_id=72");
    fireEvent.click(screen.getByRole("button", { name: "Nueva conversación" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads", expect.objectContaining({ method: "POST" })));
    expect(window.location.search).toContain("thread_id=71");

    unmount();
    const operator = render(<AgentChat role="operador" />);
    expect(await screen.findByRole("button", { name: "Nueva conversación" })).toBeInTheDocument();
    expect(within(screen.getByRole("complementary", { name: "Proyectos" })).getByRole("button", { name: "Historial" })).toBeInTheDocument();
    operator.unmount();
    render(<AgentChat role="tecnico" />);
    expect(screen.queryByRole("button", { name: "Nueva conversación" })).not.toBeInTheDocument();
    expect(within(screen.getByRole("complementary", { name: "Proyectos" })).queryByRole("button", { name: "Historial" })).not.toBeInTheDocument();
  });

  it("filters inline project history without rendering a static agent roster", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/planning/sessions")) return new Response(JSON.stringify({ sessions: [] }), { status: 200 });
      if (url.includes("proyecto=operaciones")) return new Response(JSON.stringify({ threads: [
        { id: 81, title: "Agenda semanal", proyecto: "operaciones", created_at: null, updated_at: null, run_status: null, approval_status: null },
        { id: 82, title: "Revisar inventario", proyecto: "operaciones", created_at: null, updated_at: null, run_status: null, approval_status: null },
      ] }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [{ id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);

    fireEvent.click(await screen.findByRole("button", { name: "Expandir Operaciones" }));
    fireEvent.click(screen.getByRole("button", { name: "Historial de hilos" }));
    expect(await screen.findByRole("button", { name: "Agenda semanal" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar hilos de Operaciones" }), { target: { value: "inventario" } });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Agenda semanal" })).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Revisar inventario" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revisar inventario" }));
    expect(window.location.search).toContain("proyecto=operaciones");
    expect(window.location.search).toContain("thread_id=82");
  });

  it("opens the full project history as a tab and renders date groups", async () => {
    expect(pathForRoute({ view: "chat", historyProjectSlug: "operaciones" })).toBe("/panel/app/chat?history=operaciones");
    expect(parsePanelPath("/panel/app/chat?history=operaciones")).toEqual({ view: "chat", historyProjectSlug: "operaciones" });
    expect(parsePanelPath("/panel/app/chat?thread_id=8&context=ops&planning=plan&history=other")).toEqual({ view: "chat", threadId: 8 });
    expect(parsePanelPath("/panel/app/chat?context=ops&planning=plan&history=other")).toEqual({ view: "chat", contextProjectSlug: "ops" });
    expect(parsePanelPath("/panel/app/chat?planning=plan&history=other")).toEqual({ view: "chat", planningSlug: "plan" });
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones");
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    const isoDate = (date: Date) => date.toISOString();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [{ id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.includes("/planning/sessions")) return new Response(JSON.stringify({ sessions: [] }), { status: 200 });
      if (url.includes("limit=100")) return new Response(JSON.stringify({ threads: [
        { id: 91, title: "Hilo de hoy", proyecto: "operaciones", created_at: isoDate(today), updated_at: isoDate(today), run_status: null, approval_status: null },
        { id: 92, title: "Hilo de ayer", proyecto: "operaciones", created_at: isoDate(yesterday), updated_at: isoDate(yesterday), run_status: null, approval_status: null },
        { id: 93, title: "Hilo anterior", proyecto: "operaciones", created_at: isoDate(lastWeek), updated_at: isoDate(lastWeek), run_status: null, approval_status: null },
      ] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);

    await screen.findByRole("button", { name: "Contraer Operaciones" });
    fireEvent.click(screen.getByRole("button", { name: "Historial de hilos" }));
    const allThreads = await screen.findByRole("link", { name: "Ver todos los hilos →" });
    fireEvent.click(allThreads);

    expect(window.location.search).toBe("?history=operaciones");
    expect(await screen.findByRole("button", { name: "Historial · Operaciones" })).toBeInTheDocument();
    const fullHistory = screen.getByRole("region", { name: "Historial de Operaciones" });
    expect(await within(fullHistory).findByRole("heading", { name: "Hoy" })).toBeInTheDocument();
    expect(within(fullHistory).getByRole("heading", { name: "Ayer" })).toBeInTheDocument();
    expect(within(fullHistory).getByRole("button", { name: "Hilo anterior" })).toBeInTheDocument();
    fireEvent.click(within(fullHistory).getByRole("button", { name: "Hilo de ayer" }));
    expect(window.location.search).toContain("thread_id=92");
  });

  it("re-homes project management, project chat, and project planning sessions", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/planning/sessions")) return new Response(JSON.stringify({ sessions: [{ slug: "plan-a", proyecto: "operaciones", topic: "Plan", status: "active", thread_id: 3, opened_at: null, closed_at: null, report_key: null }] }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [{ id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({ active_runs: [] }), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Acciones de proyectos" }));
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Administrar proyectos" }));
    expect(window.location.pathname).toBe("/panel/app/projects");

    fireEvent.click(await screen.findByRole("button", { name: "Expandir Operaciones" }));
    expect(await screen.findByRole("link", { name: "Sesiones de planificación" })).toHaveAttribute("href", "/panel/app/planning-sessions?proyecto=operaciones");
    fireEvent.click(screen.getByRole("button", { name: "Iniciar chat en Operaciones" }));
    expect(window.location.search).toContain("proyecto=operaciones");
  });

  it("renders open tabs with idle status and enriches matching runs with their stage", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones&thread_id=91");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/active-runs")) return new Response(JSON.stringify({ active_runs: [
        { thread_id: 91, title: "Plan", proyecto: "operaciones", agent: "orchestrator", stage: "planning", run_id: "run-91", updated_at: null },
        { thread_id: 92, title: "Consulta", proyecto: "default", agent: "orchestrator", stage: "streaming", run_id: "run-92", updated_at: null },
      ] }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [{ id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    render(<AgentChat role="admin" />);
    expect(await screen.findByText("Operaciones", { selector: ".assistant-workspace__agents li p" })).toBeInTheDocument();
    expect(screen.getByText("Planificando")).toBeInTheDocument();
    expect(screen.queryByText("Conversación rápida")).not.toBeInTheDocument();
    expect(screen.getAllByText("Orquestador")).toHaveLength(1);
  });

  it("shows an honest empty state when no tab is open regardless of run-list results", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/active-runs")) return new Response(JSON.stringify({ active_runs: [] }), { status: 200 });
      if (String(input).includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({ projects: [] }), { status: 200 });
    });
    const { unmount } = render(<AgentChat role="admin" />);
    expect(await screen.findByText("No hay agentes activos")).toBeInTheDocument();
    unmount();
    fetchMock.mockImplementation(async (input) => String(input).endsWith("/active-runs")
      ? new Response(JSON.stringify({ detail: "failure" }), { status: 500 })
      : new Response(JSON.stringify({ threads: [], projects: [] }), { status: 200 }));
    render(<AgentChat role="admin" />);
    expect(await screen.findByText("No hay agentes activos")).toBeInTheDocument();
  });

  it("opens selected history threads as tabs and exposes the real create action", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
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

    const projectsSidebar = screen.getByRole("complementary", { name: "Proyectos" });
    expect(within(projectsSidebar).getByRole("button", { name: "Historial" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revisión KB" })).not.toBeInTheDocument();
    fireEvent.click(within(projectsSidebar).getByRole("button", { name: "Historial" }));
    fireEvent.click(await screen.findByRole("button", { name: "Agenda semanal" }));
    const historyThread = await screen.findByRole("button", { name: "Revisión KB" });
    fireEvent.click(historyThread);
    const workspace = screen.getByRole("region", { name: "Área del hilo" });
    const tab = await within(workspace).findByRole("button", { name: "Revisión KB" });
    fireEvent.click(screen.getByRole("button", { name: "Crear nuevo hilo" }));
    await waitFor(() => expect(onThreadOpened).toHaveBeenCalledWith(42));
    fireEvent.click(tab);
    expect(window.location.search).toBe("?proyecto=default&thread_id=12");
    expect(screen.getByRole("button", { name: "Crear nuevo hilo" })).toBeInTheDocument();
    expect(within(workspace).getByRole("button", { name: "Acciones de Revisión KB" })).toBeInTheDocument();
    expect(within(workspace).getByRole("button", { name: "Acciones de Agenda semanal" })).toBeInTheDocument();
    expect(within(workspace).queryByRole("button", { name: "Acciones del hilo" })).not.toBeInTheDocument();
    await userEvent.setup().click(within(workspace).getByRole("button", { name: "Acciones de Revisión KB" }));
    const renameItem = await screen.findByRole("menuitem", { name: "Renombrar" });
    const closeItem = screen.getByRole("menuitem", { name: "Cerrar pestaña" });
    const deleteItem = screen.getByRole("menuitem", { name: "Eliminar hilo" });
    expect(renameItem.querySelector("svg")).not.toBeNull();
    expect(closeItem.querySelector("svg")).not.toBeNull();
    expect(deleteItem.querySelector("svg")).not.toBeNull();
    await userEvent.setup().click(renameItem);
    expect(screen.getByRole("dialog", { name: "Renombrar hilo" })).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre del hilo")).toHaveValue("Revisión KB");
    fireEvent.click(within(screen.getByRole("dialog", { name: "Renombrar hilo" })).getByRole("button", { name: "Cerrar" }));
    await userEvent.setup().click(within(workspace).getByRole("button", { name: "Acciones de Revisión KB" }));
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Eliminar hilo" }));
    expect(screen.getByRole("dialog", { name: "Eliminar hilo" })).toHaveTextContent("Revisión KB");
    fireEvent.click(within(screen.getByRole("dialog", { name: "Eliminar hilo" })).getByRole("button", { name: "Cerrar" }));
    await userEvent.setup().click(within(workspace).getByRole("button", { name: "Acciones de Revisión KB" }));
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Cerrar pestaña" }));
    expect(window.location.search).toBe("?proyecto=default&thread_id=11");
    expect(within(workspace).queryByRole("button", { name: "Revisión KB" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input, init]) => String(input).includes("/threads/12") && init?.method === "DELETE")).toBe(false);
  });

  it("shows the active thread title in the tab bar without redundant header chrome", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?thread_id=7");
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

    expect(await screen.findByRole("button", { name: "Agenda semanal" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Asistente Lumat", level: 1 })).not.toBeInTheDocument();
    expect(screen.queryByText("Proyecto: Operaciones")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Acciones de Agenda semanal" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Acciones del hilo" })).not.toBeInTheDocument();
    expect(screen.getByText("Gestión")).toBeInTheDocument();
    expect(screen.getAllByText("manual.pdf").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByRole("tab", { name: "Actividad" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detalle del hilo" }).parentElement).toHaveTextContent("Agenda semanal");
  });

  it("uses the loaded thread project in the context panel, independently of sidebar expansion", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones&thread_id=7");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
        { id: 2, slug: "archivo", name: "Archivo", purpose: "Registro", status: "archived", created_at: null, updated_at: null },
      ] }), { status: 200 });
      if (url.includes("/panel/api/chat/threads?")) return new Response(JSON.stringify({ threads: [{ id: 7, title: "Agenda semanal", created_at: null, updated_at: null }] }), { status: 200 });
      if (url.endsWith("/threads/7")) return new Response(JSON.stringify({ thread: { id: 7, proyecto: "archivo", status: "open" }, messages: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" onThreadOpened={() => undefined} />);

    expect(await screen.findByText("Registro")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expandir Archivo" }));
    expect(screen.getByText("Registro")).toBeVisible();
    expect(screen.queryByText("Gestión")).not.toBeInTheDocument();
  });

  it("renames an open tab even when its thread is absent from loaded lists", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?thread_id=404");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/active-runs")) return new Response(JSON.stringify({ active_runs: [] }), { status: 200 });
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url === "/panel/api/chat/threads?limit=20") return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      if (url.endsWith("/threads/404") && init?.method === "PATCH") return new Response(JSON.stringify({ thread: { id: 404, title: "Hilo renombrado" } }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" />);
    const workspace = screen.getByRole("region", { name: "Área del hilo" });
    const actions = await within(workspace).findByRole("button", { name: "Acciones de hilo" });
    await userEvent.setup().click(actions);
    await userEvent.setup().click(await screen.findByRole("menuitem", { name: "Renombrar" }));
    expect(screen.getByRole("dialog", { name: "Renombrar hilo" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Nombre del hilo"), { target: { value: "Hilo renombrado" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar nombre" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads/404", expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ title: "Hilo renombrado" }),
    })));
    expect(await within(workspace).findByRole("button", { name: "Hilo renombrado" })).toBeInTheDocument();
  });

  it("lists and downloads thread artifacts, and shows an honest empty state when none exist", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones&thread_id=7");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
      ] }), { status: 200 });
      if (url.includes("/panel/api/chat/threads?")) return new Response(JSON.stringify({ threads: [
        { id: 7, title: "Agenda semanal", created_at: null, updated_at: null, run_status: null, approval_status: null },
      ] }), { status: 200 });
      if (url.endsWith("/threads/7")) return new Response(JSON.stringify({
        thread: { id: 7, proyecto: "operaciones", status: "open" },
        messages: [],
        artifacts: [{ id: 5, thread_id: 7, filename: "reporte.csv", content_type: "text/csv", size: 1200, created_at: null }],
      }), { status: 200 });
      if (url.includes("/assistant/capabilities")) return new Response(JSON.stringify({ tools: [], personas: [], prompts: [], kb_available: true, memory_available: false }), { status: 200 });
      if (url.endsWith("/artifacts/5/download")) return new Response(new Blob(["data"], { type: "text/csv" }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    vi.stubGlobal("URL", Object.assign(class extends URL {}, {
      createObjectURL: vi.fn(() => "blob:test-artifact"),
      revokeObjectURL: vi.fn(),
    }));
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" onThreadOpened={() => undefined} />);

    await userEvent.setup().click(screen.getByRole("button", { name: /Artefactos del hilo/ }));
    expect(await screen.findByText("reporte.csv")).toBeInTheDocument();
    fireEvent.click(document.querySelector<HTMLButtonElement>(".assistant-workspace__file-list button")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads/7/artifacts/5/download", expect.anything()));
  });

  it("shows the honest empty state when a thread has no artifacts", async () => {
    window.history.replaceState({}, "", "/panel/app/chat?proyecto=operaciones&thread_id=8");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
      if (url.includes("/panel/api/chat/threads?")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      if (url.endsWith("/threads/8")) return new Response(JSON.stringify({ thread: { id: 8, proyecto: "operaciones", status: "open" }, messages: [] }), { status: 200 });
      if (url.includes("/assistant/capabilities")) return new Response(JSON.stringify({ tools: [], personas: [], prompts: [], kb_available: true, memory_available: false }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" onThreadOpened={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: /Artefactos del hilo/ }));
    expect(await screen.findByText("Los archivos que el asistente genere aparecerán aquí.")).toBeInTheDocument();
  });
});
