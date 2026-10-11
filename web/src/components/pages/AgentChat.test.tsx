import { StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { AgentChat as AgentChatView, COMMAND_CENTER_BREAKPOINTS, commandCenterTier, type AgentChatProps } from "./AgentChat";

vi.mock("../../api", async (importOriginal) => ({
  ...await importOriginal<typeof import("../../api")>(),
  listActiveRuns: vi.fn().mockResolvedValue({ active_runs: [] }),
}));

function AgentChat(props: Omit<AgentChatProps, "role"> & { role?: AgentChatProps["role"] }) {
  const role = Object.hasOwn(props, "role") ? props.role : "admin";
  return <AgentChatView {...props} role={role as AgentChatProps["role"]} />;
}

const makeThread = (id = 4) => ({
  id,
  status: "open",
  assistant_state: {},
  messages: [],
});

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

const sseResponse = (events: unknown[]) => {
  const body = events
    .map((event) => `data: ${JSON.stringify(event)}\n\n`)
    .join("");
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
};

describe("command center tier metadata", () => {
  it("marks the compact boundary below CC-compactMax", () => {
    expect(commandCenterTier(COMMAND_CENTER_BREAKPOINTS.compactMax - 1)).toBe(
      "compact",
    );
    expect(commandCenterTier(COMMAND_CENTER_BREAKPOINTS.compactMax)).toBe(
      "tablet",
    );
  });

  it("marks the desktop boundary at CC-desktopMin", () => {
    expect(commandCenterTier(COMMAND_CENTER_BREAKPOINTS.desktopMin - 1)).toBe(
      "tablet",
    );
    expect(commandCenterTier(COMMAND_CENTER_BREAKPOINTS.desktopMin)).toBe(
      "desktop",
    );
  });

  it("keeps the reference breakpoints stable", () => {
    expect(COMMAND_CENTER_BREAKPOINTS).toEqual({
      compactMax: 640,
      desktopMin: 1024,
    });
  });
});

describe("AgentChat", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
  });

  const policy = (overrides: Partial<{ available: string[]; opt_in_enabled: string[]; inherited: boolean }> = {}) => ({
    available: ["tool.one", "tool.two"],
    opt_in_enabled: ["tool.one"],
    inherited: true,
    ...overrides,
  });
  const toolToggle = (name: string) => document.querySelector<HTMLInputElement>(`input[aria-label="${name}"]`);

  it("fetches and renders the thread tool policy", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).endsWith("/tool-policy")
        ? jsonResponse(policy())
        : jsonResponse({ thread: makeThread(), messages: [] }),
    );
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    await waitFor(() => expect(toolToggle("tool.one")).not.toBeNull());
    const dialog = screen.getByRole("dialog", { name: "Agregar al hilo" });
    expect(dialog.querySelector("h2")).toHaveClass("visually-hidden");
    expect(document.querySelectorAll(".assistant-chat__tool-row:not(.assistant-chat__tool-master) small")).toHaveLength(0);
    expect(document.querySelector(".assistant-chat__tool-row:not(.assistant-chat__tool-master) svg")).toBeInTheDocument();
    expect(toolToggle("tool.one")).toBeChecked();
    expect(toolToggle("tool.two")).not.toBeChecked();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads/4/tool-policy", expect.anything());
  });

  it("sends the full opt-in selection when toggling a tool", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input).endsWith("/tool-policy")) {
        return init?.method === "PUT" ? jsonResponse(policy({ opt_in_enabled: ["tool.one", "tool.two"] })) : jsonResponse(policy());
      }
      return jsonResponse({ thread: makeThread(), messages: [] });
    });
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    await waitFor(() => expect(toolToggle("tool.two")).not.toBeNull());
    fireEvent.click(toolToggle("tool.two")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/tool-policy",
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ opt_in_enabled: ["tool.one", "tool.two"] }) }),
    ));
    await waitFor(() => expect(toolToggle("tool.two")).toBeChecked());
    expect(document.querySelector(".assistant-chat__tools-summary")).toHaveTextContent(/Herramientas\s+2/);
  });

  it("enables all available optional tools from the master switch", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input).endsWith("/tool-policy")) {
        return init?.method === "PUT" ? jsonResponse(policy({ opt_in_enabled: ["tool.one", "tool.two"] })) : jsonResponse(policy());
      }
      return jsonResponse({ thread: makeThread(), messages: [] });
    });
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    const masterToggle = await screen.findByRole("checkbox", { name: "Todas las herramientas" });
    expect(masterToggle).not.toBeChecked();
    fireEvent.click(masterToggle);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/tool-policy",
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ opt_in_enabled: ["tool.one", "tool.two"] }) }),
    ));
  });

  it("resets the thread policy to the project selection", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input).endsWith("/tool-policy")) {
        return init?.method === "DELETE" ? jsonResponse(policy({ inherited: true, opt_in_enabled: [] })) : jsonResponse(policy({ inherited: false }));
      }
      return jsonResponse({ thread: makeThread(), messages: [] });
    });
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    await waitFor(() => expect(document.querySelector(".assistant-chat__tool-chips button")).not.toBeNull());
    expect(screen.getByRole("button", { name: "Usar la selección del proyecto" })).toBeInTheDocument();
    fireEvent.click(document.querySelector(".assistant-chat__tool-chips button")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/tool-policy",
      expect.objectContaining({ method: "DELETE" }),
    ));
    await waitFor(() => expect(document.querySelector(".assistant-chat__tool-chips button")).toBeNull());
  });

  it("locks policy controls while a persisted run is active", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).endsWith("/tool-policy") ? jsonResponse(policy({ inherited: false })) : jsonResponse({
        thread: makeThread(),
        messages: [{ id: 1, author: "admin", content: "Working", status: "processing" }],
      }),
    );
    render(<AgentChat threadId={4} />);
    await screen.findByRole("button", { name: "Planificar" });
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    await waitFor(() => expect(toolToggle("tool.one")).not.toBeNull());
    expect(toolToggle("tool.one")).toBeDisabled();
  });

  it("shows stop only for an active run and sends its current run id", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/tool-policy")) return jsonResponse(policy());
      if (String(input).endsWith("/stop")) return jsonResponse({ status: "stopping", run_id: "run-live" });
      return jsonResponse({
        thread: { ...makeThread(), active_run_id: "run-live" },
        messages: [{ id: 1, author: "admin", content: "Working", status: "processing", assistant_metadata: { run_id: "run-live" } }],
      });
    });
    render(<AgentChat threadId={4} />);
    const stop = await screen.findByRole("button", { name: /detener ejecución/i });
    expect(stop).toBeEnabled();
    fireEvent.click(stop);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/stop",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ run_id: "run-live" }) }),
    ));
    expect(await screen.findByRole("button", { name: "Deteniendo…" })).toBeInTheDocument();
    expect(screen.queryByText("Cancelado")).not.toBeInTheDocument();
  });

  it("does not show stop when no run is active", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).endsWith("/tool-policy") ? jsonResponse(policy()) : jsonResponse({ thread: makeThread(), messages: [] }),
    );
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    expect(screen.queryByRole("button", { name: /detener ejecución/i })).not.toBeInTheDocument();
  });

  it("renders the reference composer actions and thread-context triggers", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => String(input).endsWith("/tool-policy")
      ? jsonResponse(policy())
      : jsonResponse({ thread: { ...makeThread(), proyecto: "default" }, messages: [] }));
    render(<AgentChat threadId={4} />);

    expect(await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" })).toBeInTheDocument();
    expect(screen.getByText("Consulta, planifica o trabaja en tus proyectos con el asistente Lumat.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "+" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Planificar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "General" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archivos 0" })).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector(".assistant-chat__tools-summary > span")).toHaveTextContent("1"));
    expect(document.querySelector(".assistant-chat__tools-summary .badge")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archivos 0" }).querySelector(".badge")).not.toBeInTheDocument();
    expect(document.querySelector(".assistant-chat__active-chips")).toBeNull();
    expect(screen.queryByRole("button", { name: /Herramientas/ })).not.toBeInTheDocument();
    expect(document.querySelector(".assistant-chat__composer-bottom-row")).toHaveClass("assistant-chat__composer-bottom-row--grouped");
  });

  it("hides the tray and applies compact active styling when messages exist", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: makeThread(),
      messages: [{ id: 1, author: "admin", content: "Hola", status: "processed" }],
    }));
    render(<AgentChat threadId={4} />);

    expect(await screen.findByText("Hola")).toBeInTheDocument();
    expect(document.querySelector(".assistant-chat__composer-stack")).toHaveClass(
      "assistant-chat__composer-stack--active",
    );
    expect(document.querySelector(".assistant-chat__composer-tray")).not.toBeInTheDocument();
  });

  it("keeps the tray rendered when the conversation has no messages", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ thread: makeThread(), messages: [] }));
    render(<AgentChat threadId={4} />);

    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    expect(document.querySelector(".assistant-chat__composer-tray")).toBeInTheDocument();
    expect(document.querySelector(".assistant-chat__composer-stack")).not.toHaveClass(
      "assistant-chat__composer-stack--active",
    );
  });

  it("shows project names without slugs and keeps selection functional", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/tool-policy")) return jsonResponse(policy());
      if (url === "/panel/api/projects") return jsonResponse({ projects: [{ id: 1, slug: "ops-private-slug", name: "Operations" }] });
      if (url === "/panel/api/chat/threads/4" && init?.method === "PATCH") return jsonResponse({ thread: { ...makeThread(), proyecto: "ops-private-slug" } });
      return jsonResponse({ thread: { ...makeThread(), proyecto: "default" }, messages: [] });
    });
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "General" }));
    const projectOption = await screen.findByRole("button", { name: "Operations" });
    expect(projectOption).not.toHaveTextContent("ops-private-slug");
    fireEvent.click(projectOption);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ proyecto: "ops-private-slug" }) }),
    ));
  });

  it("keeps the stop control off while only the tool policy is saving", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input).endsWith("/tool-policy")) {
        if (init?.method === "PUT") return new Promise<Response>(() => {});
        return jsonResponse(policy({ inherited: false }));
      }
      return jsonResponse({ thread: makeThread(), messages: [] });
    });
    render(<AgentChat threadId={4} />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    await waitFor(() => expect(toolToggle("tool.two")).not.toBeNull());
    fireEvent.click(toolToggle("tool.two")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/tool-policy",
      expect.objectContaining({ method: "PUT" }),
    ));
    expect(screen.queryByRole("button", { name: /detener ejecución/i })).not.toBeInTheDocument();
  });

  it("renders a persisted cancelled message distinctly", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).endsWith("/tool-policy") ? jsonResponse(policy()) : jsonResponse({
        thread: { ...makeThread(), assistant_state: { execution_status: "cancelled" } },
        messages: [{ id: 1, author: "admin", content: "Stopped", status: "cancelled" }],
      }),
    );
    render(<AgentChat threadId={4} />);
    expect(await screen.findByText("Cancelado")).toBeInTheDocument();
  });

  it("shows policy loading errors without inventing toggles", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).endsWith("/tool-policy") ? jsonResponse({ detail: "denied" }, 403) : jsonResponse({ thread: makeThread(), messages: [] }),
    );
    render(<AgentChat threadId={4} />);
    expect(await screen.findAllByRole("alert")).toEqual(expect.arrayContaining([expect.objectContaining({ textContent: "denied" })]));
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("shows an honest empty state when no opt-in tools are available", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).endsWith("/tool-policy") ? jsonResponse(policy({ available: [], opt_in_enabled: [] })) : jsonResponse({ thread: makeThread(), messages: [] }),
    );
    render(<AgentChat threadId={4} />);
    expect(await screen.findAllByText("No hay herramientas opcionales disponibles.")).not.toHaveLength(0);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("opens empty without creating a thread", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ threads: [] }));

    render(<AgentChat role={undefined} />);

    expect(
      await screen.findByRole("heading", { name: /Buenos días|Buenas tardes|Buenas noches/ }),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.anything(),
    );
  });

  it("requires a project selection before creating a new chat", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input) === "/panel/api/projects") return jsonResponse({ projects: [{ id: 1, slug: "ops", name: "Operations", purpose: "Run operations", status: "active" }] });
      if (String(input) === "/panel/api/chat/threads" && init?.method === "POST") return jsonResponse({ thread: { ...makeThread(), proyecto: "ops" }, messages: [] }, 201);
      return jsonResponse({ threads: [] });
    });

    render(<AgentChat role={undefined} />);
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar conversación" }));

    expect(await screen.findByRole("dialog", { name: /elegir proyecto/i })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith("/panel/api/chat/threads", expect.objectContaining({ method: "POST" }));
    fireEvent.click(screen.getByRole("button", { name: "Operations" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/panel/api/chat/threads",
        expect.objectContaining({ method: "POST", body: JSON.stringify({ proyecto: "ops" }) }),
      ),
    );
    expect(await screen.findByRole("textbox", { name: /mensaje/i })).toBeEnabled();
  });

  it("does not create a chat when the user has no projects", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => jsonResponse({ projects: [], threads: [] }));
    render(<AgentChat role={undefined} />);
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar conversación" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/proyecto primero/i);
    expect(fetchMock).not.toHaveBeenCalledWith("/panel/api/chat/threads", expect.objectContaining({ method: "POST" }));
  });

  it("creates a projectless chat for admins without opening the project picker", async () => {
    const onThreadOpened = vi.fn();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input) === "/panel/api/chat/threads" && init?.method === "POST") {
        return jsonResponse({ thread: makeThread(8), messages: [] }, 201);
      }
      return jsonResponse({ threads: [] });
    });

    render(<AgentChat role="admin" onThreadOpened={onThreadOpened} />);
    fireEvent.click(await screen.findByRole("button", { name: "Nueva conversación" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ proyecto: "default" }) }),
    ));
    expect(screen.queryByRole("dialog", { name: /elegir proyecto/i })).not.toBeInTheDocument();
    expect(screen.queryByText("default")).not.toBeInTheDocument();
    expect(onThreadOpened).toHaveBeenCalledWith(8);
  });

  it("keeps the project picker for technicians without a project", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input) === "/panel/api/projects"
        ? jsonResponse({ projects: [{ id: 1, slug: "ops", name: "Operations", purpose: "Run operations", status: "active" }] })
        : jsonResponse({ threads: [] }),
    );

    render(<AgentChat role="tecnico" />);
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar conversación" }));

    expect(await screen.findByRole("dialog", { name: /elegir proyecto/i })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ proyecto: "default" }) }),
    );
  });

  it("loads an owned deep link without creating a thread", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ thread: makeThread(9), messages: [] }));

    render(<AgentChat threadId={9} />);

    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/9",
      expect.anything(),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.anything(),
    );
  });

  it("keeps the existing thread deep link working from the URL", async () => {
    window.history.pushState({}, "", "/panel/app/chat?thread_id=9");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ thread: makeThread(9), messages: [] }));

    render(<AgentChat />);

    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/9",
      expect.anything(),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.anything(),
    );
  });

  it("creates a project-bound thread from the project deep link", async () => {
    window.history.pushState({}, "", "/panel/app/chat?proyecto=ops");
    const onThreadOpened = vi.fn((id: number) => {
      window.history.replaceState({}, "", `/panel/app/chat?thread_id=${id}`);
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input) === "/panel/api/chat/threads") {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({ proyecto: "ops" });
        return jsonResponse({ thread: { ...makeThread(7), proyecto: "ops" }, messages: [] }, 201);
      }
      return jsonResponse({ threads: [] });
    });

    render(<AgentChat onThreadOpened={onThreadOpened} />);

    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    expect(onThreadOpened).toHaveBeenCalledWith(7);
    expect(window.location.search).toBe("?thread_id=7");
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not create a second thread after following the created thread URL", async () => {
    window.history.pushState({}, "", "/panel/app/chat?proyecto=ops");
    let creates = 0;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input) === "/panel/api/chat/threads" && init?.method === "POST") {
        creates += 1;
        return jsonResponse({ thread: { ...makeThread(7), proyecto: "ops" }, messages: [] }, 201);
      }
      if (String(input) === "/panel/api/chat/threads/7") {
        return jsonResponse({ thread: { ...makeThread(7), proyecto: "ops" }, messages: [] });
      }
      return jsonResponse({ threads: [] });
    });

    const first = render(
      <AgentChat
        onThreadOpened={(id) => window.history.replaceState({}, "", `/panel/app/chat?thread_id=${id}`)}
      />,
    );
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    first.unmount();
    render(<AgentChat />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/panel/api/chat/threads/7", expect.anything()));
    expect(creates).toBe(1);
  });

  it("keeps the project binding when Nuevo chat is pressed from a project thread", async () => {
    window.history.pushState({}, "", "/panel/app/chat?thread_id=4");
    let createdPayload: unknown;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input) === "/panel/api/chat/threads" && init?.method === "POST") {
        createdPayload = JSON.parse(String(init.body));
        return jsonResponse({ thread: { ...makeThread(5), proyecto: "ops" }, messages: [] }, 201);
      }
      return jsonResponse({ thread: { ...makeThread(4), proyecto: "ops" }, messages: [] });
    });

    render(<AgentChat />);
    await screen.findByRole("heading", { name: "¿En qué trabajamos hoy?" });
    fireEvent.click(screen.getByRole("button", { name: "Crear nuevo hilo" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/panel/api/chat/threads",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(createdPayload).toEqual({ proyecto: "ops" });
  });

  it("removes the redundant inline context panel", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ threads: [] }));
    render(<AgentChat />);
    await screen.findByRole("heading", { name: /Buenos días|Buenas tardes|Buenas noches/ });
    expect(screen.queryByRole("button", { name: "Contexto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Contexto" })).not.toBeInTheDocument();
  });

  it("renders directional messages with exact timestamps and copy controls", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        thread: makeThread(),
        messages: [
          {
            id: 1,
            author: "agent",
            content: "Respuesta",
            status: "processed",
            created_at: "2026-09-15T12:00:00Z",
          },
          {
            id: 2,
            author: "admin",
            content: "Consulta",
            status: "processed",
            created_at: "2026-09-15T12:01:00Z",
          },
        ],
      }),
    );

    render(<AgentChat threadId={4} />);

    expect(await screen.findByText("Respuesta")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Copiar mensaje" })).toHaveLength(2);
    expect(screen.getAllByRole("time")).toHaveLength(2);
  });

  it("renders role-authored human messages as outbound and agent messages as inbound", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        thread: makeThread(),
        messages: [
          { id: 1, author: "tecnico", content: "Consulta técnica", status: "processed" },
          { id: 2, author: "agent", content: "Respuesta", status: "processed" },
        ],
      }),
    );

    render(<AgentChat role="tecnico" threadId={4} />);

    const human = await screen.findByLabelText("Mensaje de técnico");
    expect(human).toHaveClass("ai-agent-grammar__bubble-row--outbound");
    expect(within(human).getByText("Técnico")).toBeInTheDocument();
    expect(screen.getByLabelText("Mensaje de agente")).not.toHaveClass(
      "ai-agent-grammar__bubble-row--outbound",
    );
  });

  it("auto-grows the composer and keeps Shift+Enter as a newline", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ thread: makeThread(), messages: [] }),
    );
    render(<AgentChat threadId={4} />);

    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    Object.defineProperty(composer, "scrollHeight", {
      configurable: true,
      value: 96,
    });
    fireEvent.change(composer, { target: { value: "Hola" } });
    expect(composer).toHaveStyle({ height: "96px" });

    fireEvent.keyDown(composer, { key: "Enter", shiftKey: true });
    expect(composer).toHaveValue("Hola\n");
    expect(composer).not.toBeDisabled();
    expect(vi.mocked(globalThis.fetch)).toHaveBeenCalledTimes(2);
  });

  it("renders approval and evidence inside the producing message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        thread: {
          ...makeThread(),
          active_run_id: "run",
          current_plan: { tool: "skill.propose", arguments: { name: "calefont", description: "Guía del proyecto", body: "Usa solo evidencia local." }, status: "pending" },
          assistant_state: {
            approval: { token: "token", status: "pending" },
            events: [{ evidence: [{ tool: "agenda", status: "completed", detail: "Creado" }] }],
          },
        },
         messages: [
           { id: 1, author: "agent", content: "Necesito aprobación", status: "processed", assistant_metadata: { run_id: "run" } },
         ],
      }),
    );

    render(<AgentChat threadId={4} />);
    const message = await screen.findByRole("article", { name: "Mensaje de agente" });

    expect(message).toContainElement(screen.getByRole("button", { name: "Aprobar" }));
    expect(message.querySelector("details")).toBeTruthy();
    expect(message).toHaveTextContent("calefont");
    expect(message).toHaveTextContent("Guía del proyecto");
    expect(message).toHaveTextContent("Usa solo evidencia local.");
  });

  it("keeps processing until the SSE stream closes", async () => {
    let closeStream: () => void = () => undefined;
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            `data: ${JSON.stringify({
              type: "response",
              thread_id: 4,
              run_id: "run-4",
              sequence: 0,
              content: "Still streaming",
            })}\n\n`,
          ),
        );
        closeStream = () => controller.close();
      },
    });
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({
          message: {
            id: 2,
            author: "admin",
            content: "Hello",
            status: "processing",
            assistant_metadata: { run_id: "run-4" },
          },
        }, 201),
      )
      .mockResolvedValueOnce(
        new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      );

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("Still streaming")).toBeInTheDocument();
    expect(composer).toBeDisabled();
    closeStream();
    await waitFor(() => expect(composer).toBeEnabled());
  });

  it("keeps watching after a timeout until the persisted run settles", async () => {
    vi.useFakeTimers();
    try {
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              `data: ${JSON.stringify({
                type: "timeout",
                thread_id: 4,
                run_id: "run-timeout",
              })}\n\n`,
            ),
          );
          controller.close();
        },
      });
      const fetchMock = vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
        .mockResolvedValueOnce(jsonResponse(policy()))
        .mockResolvedValueOnce(jsonResponse({
          message: {
            id: 2,
            author: "admin",
            content: "Hello",
            status: "processing",
            assistant_metadata: { run_id: "run-timeout" },
          },
        }, 201))
        .mockResolvedValueOnce(new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }))
        .mockResolvedValueOnce(jsonResponse({
          thread: makeThread(),
          messages: [{
            id: 2,
            author: "admin",
            content: "Hello",
            status: "processing",
            assistant_metadata: { run_id: "run-timeout" },
          }],
        }))
        .mockResolvedValueOnce(jsonResponse({
          thread: makeThread(),
          messages: [{ id: 3, author: "agent", content: "Persisted answer", status: "processed", assistant_metadata: { run_id: "run-timeout" } }],
        }))
        .mockResolvedValueOnce(jsonResponse({
          thread: makeThread(),
          messages: [{ id: 3, author: "agent", content: "Persisted answer", status: "processed", assistant_metadata: { run_id: "run-timeout" } }],
        }));

      render(<AgentChat threadId={4} />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      const composer = screen.getByRole("textbox", { name: /mensaje/i });
      fireEvent.change(composer, { target: { value: "Hello" } });
      fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(fetchMock).toHaveBeenCalledTimes(4);
      expect(composer).toBeDisabled();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3_000);
        await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(3_000);
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(screen.getByText("Persisted answer")).toBeInTheDocument();
      expect(fetchMock).toHaveBeenCalledTimes(7);
      expect(screen.getAllByText("Persisted answer")).toHaveLength(1);
      expect(composer).toBeEnabled();
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not poll after a normally closed stream", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(jsonResponse({
        message: {
          id: 2,
          author: "admin",
          content: "Hello",
          status: "processing",
          assistant_metadata: { run_id: "run-normal" },
        },
      }, 201))
      .mockResolvedValueOnce(sseResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        thread: makeThread(),
        messages: [{ id: 3, author: "agent", content: "Normal answer", status: "processed" }],
      }));

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(screen.getByText("Normal answer")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(5);
    expect(composer).toBeEnabled();
  });

  it("keeps watching after a timeout under StrictMode", async () => {
    vi.useFakeTimers();
    try {
      let streamServed = false;
      let threadReadsAfterStream = 0;
      vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        const url = typeof input === "string" ? input : String((input as Request).url);
        const method = (init?.method ?? "GET").toUpperCase();
        if (url.includes("/stream")) {
          streamServed = true;
          return sseResponse([{ type: "timeout", thread_id: 4, run_id: "run-strict" }]);
        }
        if (method === "POST" && url.includes("/messages")) {
          return jsonResponse({
            message: {
              id: 2,
              author: "admin",
              content: "Hello",
              status: "processing",
              assistant_metadata: { run_id: "run-strict" },
            },
          }, 201);
        }
        if (streamServed) {
          threadReadsAfterStream += 1;
          if (threadReadsAfterStream === 1) {
            return jsonResponse({
              thread: makeThread(),
              messages: [{
                id: 2,
                author: "admin",
                content: "Hello",
                status: "processing",
                assistant_metadata: { run_id: "run-strict" },
              }],
            });
          }
          return jsonResponse({
            thread: makeThread(),
            messages: [{
              id: 3,
              author: "agent",
              content: "Persisted answer",
              status: "processed",
              assistant_metadata: { run_id: "run-strict" },
            }],
          });
        }
        return jsonResponse({ thread: makeThread(), messages: [] });
      });

      render(
        <StrictMode>
          <AgentChat threadId={4} />
        </StrictMode>,
      );
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      const composer = screen.getByRole("textbox", { name: /mensaje/i });
      fireEvent.change(composer, { target: { value: "Hello" } });
      fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3_000);
        await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(3_000);
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(screen.getByText("Persisted answer")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("switches a settled stream from literal text to markdown", async () => {
    let closeStream: () => void = () => undefined;
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            `data: ${JSON.stringify({
              type: "response",
              thread_id: 4,
              run_id: "run-markdown",
              sequence: 0,
              content: "**respuesta en curso**",
            })}\n\n`,
          ),
        );
        closeStream = () => controller.close();
      },
    });
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(jsonResponse({
        message: {
          id: 2,
          author: "admin",
          content: "Hello",
          status: "processing",
          assistant_metadata: { run_id: "run-markdown" },
        },
      }, 201))
      .mockResolvedValueOnce(new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }))
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()));

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("**respuesta en curso**")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("respuesta en curso").tagName).toBe("STRONG"), {
      timeout: 500,
    });
    closeStream();
    await waitFor(() => expect(composer).toBeEnabled());
  });

  it("renders new stream content while a previous markdown snapshot is stale", async () => {
    let pushEvent: (content: string) => void = () => undefined;
    let closeStream: () => void = () => undefined;
    const stream = new ReadableStream({
      start(controller) {
        pushEvent = (content) =>
          controller.enqueue(
            new TextEncoder().encode(
              `data: ${JSON.stringify({
                type: "response",
                thread_id: 4,
                run_id: "run-stale-markdown",
                sequence: 0,
                content,
              })}\n\n`,
            ),
          );
        pushEvent("**respuesta inicial**");
        closeStream = () => controller.close();
      },
    });
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(jsonResponse({
        message: {
          id: 2,
          author: "admin",
          content: "Hello",
          status: "processing",
          assistant_metadata: { run_id: "run-stale-markdown" },
        },
      }, 201))
      .mockResolvedValueOnce(new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }))
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()));

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(screen.getByText("respuesta inicial").tagName).toBe("STRONG"), {
      timeout: 500,
    });
    pushEvent("**respuesta inicial** y contenido nuevo");
    await waitFor(
      () => expect(screen.getByText("**respuesta inicial** y contenido nuevo")).toBeInTheDocument(),
      { timeout: 150 },
    );
    closeStream();
    await waitFor(() => expect(composer).toBeEnabled());
  });

  it("does not call a disconnected stream successful and exposes recovery state", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({
          message: {
            id: 2,
            author: "admin",
            content: "Hello",
            status: "processing",
            assistant_metadata: { run_id: "run-fail" },
          },
        }, 201),
      )
      .mockRejectedValueOnce(new Error("socket closed"));

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/stream del asistente falló/i);
    expect(screen.getByRole("status", { name: /recuperable/i })).toHaveTextContent(
      /recuperable/i,
    );
    expect(screen.queryByText("Cancelado")).not.toBeInTheDocument();
  });

  it("keeps persisted history authoritative when a transient stream is present", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({
          message: {
            id: 2,
            author: "admin",
            content: "Hello",
            status: "processing",
            assistant_metadata: { run_id: "run-persist" },
          },
        }, 201),
      )
      .mockResolvedValueOnce(
        sseResponse([
          {
            type: "response",
            thread_id: 4,
            run_id: "run-persist",
            sequence: 0,
            content: "Transient only",
          },
        ]),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          thread: makeThread(),
          messages: [{ id: 9, author: "agent", content: "Persisted answer", status: "processed" }],
        }),
      );

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("Persisted answer")).toBeInTheDocument();
    expect(screen.queryByText("Transient only")).not.toBeInTheDocument();
  });

  it("allows approving and rejecting a persisted pending plan after reload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse({
          thread: {
            ...makeThread(),
            active_run_id: "run-2",
            current_plan: {
              tool: "automation.create_rule",
              arguments: { name: "Notify" },
              status: "pending",
            },
            assistant_state: {
              stage: "approval_pending",
              approval: { token: "secret", status: "pending" },
            },
          },
          messages: [
           { id: 1, author: "agent", content: "Plan pendiente", status: "processed", assistant_metadata: { run_id: "run-2" } },
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({
          status: "rejected",
          message: { id: 3, author: "admin", content: "Write rule", status: "rejected" },
        }),
      );

    render(<AgentChat threadId={4} />);
    expect(await screen.findByText("automation.create_rule")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /rechazar/i }));

    await waitFor(() => expect(screen.getByText(/rechazado/i)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/panel/api/chat/threads/4/approval",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ run_id: "run-2", token: "secret", reject: true }),
      }),
    );
  });

  it("renders plan arguments as a readable list instead of raw JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({
        thread: {
          ...makeThread(),
          active_run_id: "run-args",
          current_plan: {
            tool: "service.create",
            arguments: { date: "tomorrow", notes: "Puerta azul" },
            status: "pending",
          },
          assistant_state: {
            stage: "approval_pending",
            approval: { token: "secret", status: "pending" },
          },
        },
        messages: [
          { id: 1, author: "agent", content: "Plan pendiente", status: "processed", assistant_metadata: { run_id: "run-args" } },
        ],
      }),
    );

    render(<AgentChat threadId={4} />);
    expect(await screen.findByText("service.create")).toBeInTheDocument();
    expect(screen.getByText("tomorrow")).toBeInTheDocument();
    expect(screen.getByText("Puerta azul")).toBeInTheDocument();
    expect(screen.queryByText(/\{"date":"tomorrow"/)).not.toBeInTheDocument();
  });

  it("submits the approval verb for a persisted pending plan", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/chat/threads/4" && !init?.method) return jsonResponse({
        thread: {
          ...makeThread(),
          active_run_id: "run-approve",
          current_plan: { tool: "agenda", status: "pending" },
          assistant_state: { approval: { token: "secret", status: "pending" } },
        },
        messages: [{ id: 1, author: "agent", content: "Confirma la agenda", status: "processed", assistant_metadata: { run_id: "run-approve" } }],
      });
      if (url === "/panel/api/chat/threads/4/tool-policy") return jsonResponse(policy());
      if (url === "/panel/api/chat/threads/4/approval" && init?.method === "POST") return jsonResponse({
        status: "consumed",
        message: { id: 2, author: "agent", content: "Aprobado", status: "processed" },
      });
      if (url.includes("/panel/api/chat/threads/4/stream")) return sseResponse([]);
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<AgentChat threadId={4} />);
    fireEvent.click(await screen.findByRole("button", { name: "Aprobar" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/approval",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ run_id: "run-approve", token: "secret", reject: false }),
      }),
    ));
  });

  it("recovers a persisted plan by thread id without creating a new thread", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        thread: {
          ...makeThread(),
          active_run_id: "run-3",
          current_plan: { tool: "automation.create_rule", arguments: { name: "Notify" }, status: "pending" },
          assistant_state: {
            stage: "approval_pending",
            recoverable: true,
            execution_status: "pending",
            approval: { token: "secret", status: "pending" },
            events: [],
          },
        },
        messages: [
           { id: 1, author: "agent", content: "Plan recuperado", status: "processed", assistant_metadata: { run_id: "run-3" } },
        ],
      }),
    );

    render(<AgentChat threadId={4} />);
    expect(await screen.findByText("automation.create_rule")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4",
      expect.anything(),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.anything(),
    );
    expect(screen.getByRole("button", { name: /aprobar/i })).toBeEnabled();
  });

  it("uploads an attachment from the composer and shows its filename", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/projects") return jsonResponse({ projects: [] });
      if (url === "/panel/api/chat/threads/4" && !init?.method) {
        return jsonResponse({ thread: makeThread(), messages: [] });
      }
      if (url === "/panel/api/chat/threads/4/tool-policy") return jsonResponse(policy());
      if (url === "/panel/api/chat/threads/4/attachments" && init?.method === "POST") {
        return jsonResponse({
          attachment: { id: 9, thread_id: 4, filename: "photo.png", kind: "image", size: 3 },
        }, 201);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<AgentChat threadId={4} />);
    await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(screen.getByLabelText(/adjuntar/i), {
      target: { files: [new File(["png"], "photo.png", { type: "image/png" })] },
    });

    expect(await screen.findAllByText("photo.png")).toHaveLength(3);
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/4/attachments",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows the active Cortex indicator and closes through the planning endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/panel/api/chat/threads/4" && !init?.method) return jsonResponse({
        thread: {
          ...makeThread(),
          assistant_state: {
            cortex_session: {
              slug: "budget-4",
              topic: "Budget",
              status: "active",
            },
          },
        },
        messages: [],
      });
      if (url === "/panel/api/chat/threads/4/tool-policy") return jsonResponse(policy());
      if (url === "/panel/api/planning/sessions/budget-4/close" && init?.method === "POST") return jsonResponse({
        session: {},
        report: { contenido: "Report" },
      });
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<AgentChat threadId={4} />);
    expect(await screen.findByText(/Planificación activa/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /cerrar planificación/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/panel/api/planning/sessions/budget-4/close",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.getByText(/Informe de planificación: Report/i)).toBeInTheDocument();
  });

  it("treats exact planning commands as lifecycle controls and free text as chat", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({ session: { slug: "budget-4" }, thread_id: 4 }, 201),
      )
      .mockResolvedValueOnce(
        jsonResponse({ message: { id: 2, author: "admin", content: "planning words", status: "processed" } }, 201),
      );

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "/planning budget" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenNthCalledWith(
        3,
        "/panel/api/planning/sessions",
        expect.objectContaining({
          body: JSON.stringify({ topic: "budget", thread_id: 4 }),
        }),
      ),
    );
    fireEvent.change(composer, { target: { value: "please discuss planning" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenNthCalledWith(
        4,
        "/panel/api/chat/threads/4/messages",
        expect.anything(),
      ),
    );
  });

  it("resubmits a failed message in place and preserves an unsent draft", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({
         message: { id: 3, author: "admin", content: "Retry me", status: "failed", error: "temporary" },
        }, 201),
       )
      .mockResolvedValueOnce(
        jsonResponse({
          message: { id: 4, author: "admin", content: "Retry me", status: "failed", error: "temporary" },
        }, 201),
      );

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Retry me" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect((await screen.findAllByRole("alert")).some((item) =>
      item.textContent?.includes("No se pudo procesar el mensaje"),
    )).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /reintentar/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/panel/api/chat/threads/4/messages",
      expect.objectContaining({ body: JSON.stringify({ content: "Retry me", attachment_ids: [] }) }),
    ));

    fireEvent.change(composer, { target: { value: "draft" } });
    fireEvent.click(screen.getAllByRole("button", { name: /reintentar/i })[0]);
    expect(composer).toHaveValue("draft");
  });

  it("keeps plan and evidence with the message that owns their run", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: {
        ...makeThread(),
        active_run_id: "run-two",
        current_plan: { tool: "new.tool", status: "pending" },
        assistant_state: {
          events: [
            { run_id: "run-one", evidence: [{ tool: "old.tool", status: "completed", detail: "Old evidence" }] },
            { run_id: "run-two", evidence: [{ tool: "new.tool", status: "completed", detail: "New evidence" }], plan: { tool: "new.tool", status: "pending" } },
          ],
          approval: { token: "token", status: "pending" },
        },
      },
      messages: [
        { id: 1, author: "admin", content: "Old request", status: "processed", assistant_metadata: { run_id: "run-one" } },
        { id: 2, author: "admin", content: "New request", status: "processed", assistant_metadata: { run_id: "run-two" } },
      ],
    }));

    render(<AgentChat threadId={4} />);
    const messages = await screen.findAllByRole("article");
    expect(messages).toHaveLength(2);
    expect(messages[0]).toContainElement(screen.getByText("Old evidence"));
    expect(messages[1]).toContainElement(screen.getByText("New evidence"));
    expect(messages[1]).toHaveTextContent("new.tool");
  });

  it("does not inherit earlier run artifacts when a later run has none", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: {
        ...makeThread(),
        active_run_id: "run-live",
        assistant_state: {
          events: [{
            run_id: "run-a",
            plan: { tool: "agenda.create", status: "completed" },
            evidence: [{ tool: "agenda.create", status: "completed", detail: "Cita creada" }],
          }],
        },
      },
      messages: [
        { id: 1, author: "agent", content: "Respuesta anterior", status: "processed", assistant_metadata: { run_id: "run-a" } },
        { id: 2, author: "agent", content: "Respuesta posterior", status: "processed", assistant_metadata: { run_id: "run-b" } },
      ],
    }));

    render(<AgentChat threadId={4} />);
    const messages = await screen.findAllByRole("article");
    const later = within(messages[1]);

    expect(messages[0]).toHaveTextContent("agenda.create");
    expect(messages[0]).toHaveTextContent("Cita creada");
    expect(messages[1]).not.toHaveTextContent("agenda.create");
    expect(messages[1]).not.toHaveTextContent("Cita creada");
    expect(later.queryByText("Plan de acción")).not.toBeInTheDocument();
    expect(later.queryByText(/Evidencia de herramientas/)).not.toBeInTheDocument();
  });

  it("keeps the authorized refusal text without escalation copy", async () => {
    const refusal = "No puedo realizar esa acción fuera del approved operational workflow.";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        thread: makeThread(),
        messages: [{ id: 5, author: "agent", content: refusal, status: "processed" }],
      }),
    );

    render(<AgentChat threadId={4} />);
    expect(await screen.findByText(refusal)).toBeInTheDocument();
    expect(screen.queryByText(/herramientas privilegiadas|escalamiento nuevo/i)).not.toBeInTheDocument();
  });

  it("renders an actionable permission error without internal thread content", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "No tienes permiso para ver el chat interno" }, 403),
    );

    render(<AgentChat threadId={4} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No tienes permiso para ver el chat interno",
    );
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByText("No hay mensajes todavía")).not.toBeInTheDocument();
  });

  it("renders a streamed plan, evidence, and final response in event order", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(jsonResponse(policy()))
      .mockResolvedValueOnce(
        jsonResponse({
          message: {
            id: 2,
            thread_id: 4,
            author: "admin",
            content: "Schedule it",
            status: "processing",
            assistant_metadata: { run_id: "run-1" },
          },
        }, 201),
      )
      .mockResolvedValueOnce(
        sseResponse([
          {
            type: "plan",
            thread_id: 4,
            run_id: "run-1",
            sequence: 0,
            plan: { tool: "appointments.create", arguments: { date: "tomorrow" }, status: "pending" },
          },
          { type: "status", thread_id: 4, run_id: "run-1", sequence: 1, status: "streaming" },
          { type: "tool", thread_id: 4, run_id: "run-1", sequence: 2, tool: "appointments.create", status: "completed" },
          {
            type: "evidence",
            thread_id: 4,
            run_id: "run-1",
            sequence: 3,
            evidence: [{ tool: "appointments.create", status: "completed", detail: "Appointment created" }],
          },
          { type: "response", thread_id: 4, run_id: "run-1", sequence: 4, content: "Done." },
        ]),
      );

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Schedule it" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect((await screen.findAllByText("appointments.create")).length).toBeGreaterThan(0);
    expect(screen.getByText("Appointment created")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Done.")).toBeInTheDocument());
    expect(screen.getByText("Completado")).toBeInTheDocument();
  });

  it("renders a run's artifacts once, on the agent reply, not on both messages", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: {
        ...makeThread(),
        active_run_id: "run-1",
        assistant_state: {
          events: [{
            run_id: "run-1",
            plan: { tool: "agenda.create", status: "completed" },
            evidence: [{ tool: "agenda.create", status: "completed", detail: "Cita creada" }],
          }],
        },
      },
      messages: [
        { id: 1, author: "admin", content: "Agenda una visita", status: "processed", assistant_metadata: { run_id: "run-1" } },
        { id: 2, author: "agent", content: "Listo", status: "processed", assistant_metadata: { run_id: "run-1" } },
      ],
    }));

    render(<AgentChat threadId={4} />);
    const messages = await screen.findAllByRole("article");

    expect(messages).toHaveLength(2);
    expect(messages[0]).not.toHaveTextContent("Cita creada");
    expect(messages[1]).toHaveTextContent("Cita creada");
    expect(screen.getAllByText(/Actividad del agente/)).toHaveLength(1);
  });

  it("renders no activity block for a plain answer with no tool work", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: {
        ...makeThread(),
        active_run_id: "run-1",
        assistant_state: {
          events: [{
            run_id: "run-1",
            plan: { tool: null, arguments: {}, summary: "hey chat estas disponible" },
          }],
        },
      },
      messages: [
        { id: 2, author: "agent", content: "Sí, estoy disponible.", status: "processed", assistant_metadata: { run_id: "run-1" } },
      ],
    }));

    render(<AgentChat threadId={4} />);
    const message = await screen.findByRole("article", { name: "Mensaje de agente" });

    expect(message).toHaveTextContent("Sí, estoy disponible.");
    expect(message).not.toHaveTextContent("Actividad del agente");
    expect(screen.queryByText("Plan de acción")).not.toBeInTheDocument();
  });

  it("shows a working indicator while the agent is thinking", async () => {
    let closeStream: () => void = () => undefined;
    const stream = new ReadableStream({
      start(controller) {
        closeStream = () => controller.close();
      },
    });
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          message: {
            id: 2,
            author: "admin",
            content: "Hola",
            status: "processing",
            assistant_metadata: { run_id: "run-4" },
          },
        }, 201),
      )
      .mockResolvedValueOnce(
        new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      );

    render(<AgentChat threadId={4} />);
    const composer = await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hola" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await screen.findByRole("article", { name: "El agente está trabajando" });
    expect(screen.getByText("Analizando tu solicitud…")).toBeInTheDocument();
    closeStream();
    await waitFor(() => expect(composer).toBeEnabled());
  });

  it("renders agent replies as markdown and leaves the operator text literal", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: makeThread(),
      messages: [
        { id: 1, author: "admin", content: "**esto** no debe formatearse", status: "processed" },
        { id: 2, author: "agent", content: "**esto sí** debe formatearse", status: "processed" },
      ],
    }));

    render(<AgentChat threadId={4} />);
    const admin = await screen.findByRole("article", { name: "Mensaje de administrador" });
    const agent = screen.getByRole("article", { name: "Mensaje de agente" });

    expect(within(agent).getByText("esto sí").tagName).toBe("STRONG");
    expect(within(agent).queryByText("*esto sí*")).not.toBeInTheDocument();
    expect(admin).toHaveTextContent("**esto** no debe formatearse");
    expect(within(admin).queryByText("esto")).not.toBeInTheDocument();
  });

  it("confirms a copy with a transient label", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      thread: makeThread(),
      messages: [{ id: 1, author: "agent", content: "Copia esto", status: "processed" }],
    }));

    render(<AgentChat threadId={4} />);
    fireEvent.click(await screen.findByRole("button", { name: "Copiar mensaje" }));

    expect(writeText).toHaveBeenCalledWith("Copia esto");
    expect(screen.getByText("Copiado")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Mensaje copiado al portapapeles" }),
    ).toBeInTheDocument();
  });
});
