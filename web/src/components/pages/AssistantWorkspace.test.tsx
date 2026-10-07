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

    expect(screen.getByRole("complementary", { name: "Proyectos" })).toBeInTheDocument();
    const thread = screen.getByRole("region", { name: "Área del hilo" });
    expect(within(thread).getByRole("heading", { name: "Asistente Lumat" })).toBeInTheDocument();
    expect(await within(thread).findByRole("heading", { name: "Comienza una conversación" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Contexto del hilo" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Agentes" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contexto" })).toBeInTheDocument();
  });

  it("loads real projects, filters by name, and expands project navigation and agent state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
        { id: 2, slug: "archivo", name: "Archivo", purpose: "Registro", status: "archived", created_at: null, updated_at: null },
      ] }), { status: 200 });
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });

    render(<AgentChat role="admin" />);

    const project = await screen.findByText("Operaciones");
    expect(within(project.closest("button")!).getByText("Activo")).toBeInTheDocument();
    expect(screen.getByText("Archivo")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar proyectos" }), { target: { value: "arch" } });
    await waitFor(() => expect(screen.queryByText("Operaciones")).not.toBeInTheDocument());
    expect(screen.getByText("Archivo")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar proyectos" }), { target: { value: "operaciones" } });
    await waitFor(() => expect(screen.getByText("Operaciones")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Operaciones").closest("button")!);
    expect(screen.getByRole("link", { name: "Contexto y archivos" })).toHaveAttribute("href", "/panel/app/projects/operaciones");
    expect(screen.getByRole("link", { name: "Historial de hilos" })).toHaveAttribute("href", "/panel/app/chat?proyecto=operaciones");
    expect(screen.getByRole("heading", { name: "Agentes del proyecto" })).toBeInTheDocument();
    expect(screen.getByText("La gestión de agentes por proyecto todavía no está disponible.")).toBeInTheDocument();
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

  it("keeps pane toggles usable at narrow widths and creates a thread for the selected project", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/panel/api/projects")) return new Response(JSON.stringify({ projects: [
        { id: 1, slug: "operaciones", name: "Operaciones", purpose: "Gestión", status: "active", created_at: null, updated_at: null },
      ] }), { status: 200 });
      if (url === "/panel/api/chat/threads" && init?.method === "POST") {
        return new Response(JSON.stringify({ thread: { id: 42, proyecto: "operaciones", status: "open" }, messages: [] }), { status: 201 });
      }
      if (url.includes("/threads")) return new Response(JSON.stringify({ threads: [] }), { status: 200 });
      return new Response(JSON.stringify({}), { status: 200 });
    });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 640 });
    const dispatchEvent = vi.spyOn(window, "dispatchEvent").mockImplementation(() => true);

    render(<AgentChat role="admin" />);
    const projectsToggle = screen.getByRole("button", { name: "Mostrar u ocultar proyectos" });
    expect(projectsToggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(projectsToggle);
    expect(projectsToggle).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByText("Operaciones")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Operaciones").closest("button")!);
    fireEvent.click(screen.getByRole("button", { name: "Crear hilo" }));

    await waitFor(() => expect(window.location.search).toBe("?proyecto=operaciones&thread_id=42"));
    expect(dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "popstate" }));
    expect(globalThis.fetch).toHaveBeenCalledWith("/panel/api/chat/threads", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ proyecto: "operaciones" }),
    }));
  });
});
