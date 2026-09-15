import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AgentChat, COMMAND_CENTER_BREAKPOINTS, commandCenterTier } from "./AgentChat";

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
  afterEach(() => vi.restoreAllMocks());

  it("opens empty without creating a thread", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ threads: [] }));

    render(<AgentChat />);

    expect(
      await screen.findByRole("heading", { name: "Comienza una conversación" }),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.anything(),
    );
  });

  it("creates only when Nuevo chat is explicitly pressed", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input) =>
        String(input).includes("?limit=20")
          ? jsonResponse({ threads: [] })
          : jsonResponse({ thread: makeThread(), messages: [] }, 201),
    );

    render(<AgentChat />);
    fireEvent.click(await screen.findByRole("button", { name: "Nuevo chat" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/panel/api/chat/threads",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(await screen.findByRole("textbox", { name: /mensaje/i })).toBeEnabled();
  });

  it("loads an owned deep link without creating a thread", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ thread: makeThread(9), messages: [] }));

    render(<AgentChat threadId={9} />);

    await screen.findByRole("heading", { name: "¿En qué podemos ayudarte?" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/chat/threads/9",
      expect.anything(),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads",
      expect.anything(),
    );
  });

  it("renders history with Spanish grouping and no raw status", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).includes("?limit=20")
        ? jsonResponse({
            threads: [
              {
                id: 1,
                title: "Consulta",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ],
          })
        : jsonResponse({ threads: [] }),
    );

    render(<AgentChat />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial" }));

    expect((await screen.findAllByText("Hoy")).length).toBeGreaterThan(0);
    expect(screen.queryByText("open")).not.toBeInTheDocument();
  });

  it("renames a thread through a prefilled dialog and cancels without a call", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.includes("?limit=20")) {
        return jsonResponse({
          threads: [{ id: 1, title: "Consulta", created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
        });
      }
      return jsonResponse({ threads: [] });
    });

    render(<AgentChat />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial" }));
    fireEvent.click(await screen.findByRole("button", { name: /renombrar consulta/i }));
    expect(screen.getByLabelText(/nuevo nombre/i)).toHaveValue("Consulta");
    fireEvent.click(screen.getAllByRole("button", { name: "Cancelar" })[0]);
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/panel/api/chat/threads/1",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("confirms deletion in a named dialog instead of using a browser confirm", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      String(input).includes("?limit=20")
        ? jsonResponse({
            threads: [{ id: 1, title: "Consulta", created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
          })
        : jsonResponse({ threads: [] }),
    );

    render(<AgentChat />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial" }));
    fireEvent.click(await screen.findByRole("button", { name: /eliminar consulta/i }));
    expect(screen.getByText(/Eliminar la conversación “Consulta”/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar consulta/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar conversación" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/panel/api/chat/threads/1",
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
  });

  it("keeps Contexto closed until requested and translates connection state", async () => {
    render(<AgentChat />);

    expect(
      screen.queryByRole("complementary", { name: "Contexto" }),
    ).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Contexto" }));

    expect(screen.getByRole("complementary", { name: "Contexto" })).toHaveTextContent(
      "Conexión",
    );
    expect(screen.getByRole("complementary", { name: "Contexto" })).not.toHaveTextContent(
      "disconnected",
    );
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
    expect(composer).toHaveValue("Hola");
    expect(composer).not.toBeDisabled();
  });

  it("renders approval and evidence inside the producing message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        thread: {
          ...makeThread(),
          active_run_id: "run",
          current_plan: { tool: "agenda", status: "pending" },
          assistant_state: {
            approval: { token: "token", status: "pending" },
            events: [{ evidence: [{ tool: "agenda", status: "completed", detail: "Creado" }] }],
          },
        },
        messages: [
          { id: 1, author: "agent", content: "Necesito aprobación", status: "processed" },
        ],
      }),
    );

    render(<AgentChat threadId={4} />);
    const message = await screen.findByRole("article", { name: "Mensaje de agente" });

    expect(message).toContainElement(screen.getByRole("button", { name: "Aprobar" }));
    expect(message.querySelector("details")).toBeTruthy();
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

  it("does not call a disconnected stream successful and exposes recovery state", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
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
  });

  it("keeps persisted history authoritative when a transient stream is present", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
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
            { id: 1, author: "agent", content: "Plan pendiente", status: "processed" },
          ],
        }),
      )
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

  it("submits the approval verb for a persisted pending plan", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({
        thread: {
          ...makeThread(),
          active_run_id: "run-approve",
          current_plan: { tool: "agenda", status: "pending" },
          assistant_state: { approval: { token: "secret", status: "pending" } },
        },
        messages: [{ id: 1, author: "agent", content: "Confirma la agenda", status: "processed" }],
      }))
      .mockResolvedValueOnce(jsonResponse({
        status: "consumed",
        message: { id: 2, author: "agent", content: "Aprobado", status: "processed" },
      }))
      .mockResolvedValueOnce(sseResponse([]));

    render(<AgentChat threadId={4} />);
    fireEvent.click(await screen.findByRole("button", { name: "Aprobar" }));

    await waitFor(() => expect(fetchMock).toHaveBeenNthCalledWith(
      2,
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
          { id: 1, author: "agent", content: "Plan recuperado", status: "processed" },
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
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          attachment: { id: 9, thread_id: 4, filename: "photo.png", kind: "image", size: 3 },
        }, 201),
      );

    render(<AgentChat threadId={4} />);
    await screen.findByRole("textbox", { name: /mensaje/i });
    fireEvent.change(screen.getByLabelText(/adjuntar/i), {
      target: { files: [new File(["png"], "photo.png", { type: "image/png" })] },
    });

    expect(await screen.findByText("photo.png")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/panel/api/chat/threads/4/attachments",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows the active Cortex indicator and closes through the planning endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse({
          thread: {
            ...makeThread(),
            assistant_state: {
              cortex_session: {
                slug: "budget-4",
                topic: "Budget",
                status: "active",
                handoff: { status: "none", sdb_phase: null },
              },
            },
          },
          messages: [],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          session: {},
          report: { contenido: "Report" },
          handoff: { status: "pending", sdb_phase: "SPEC" },
        }),
      );

    render(<AgentChat threadId={4} />);
    expect(await screen.findByText(/Planificación activa/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /cerrar planificación/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        "/panel/api/planning/sessions/budget-4/close",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.getByText(/plan aprobado/i)).toBeInTheDocument();
  });

  it("treats exact planning commands as lifecycle controls and free text as chat", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
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
        2,
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
        3,
        "/panel/api/chat/threads/4/messages",
        expect.anything(),
      ),
    );
  });

  it("keeps a failed submitted message visible and actionable", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ thread: makeThread(), messages: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          message: { id: 3, author: "admin", content: "Retry me", status: "failed", error: "temporary" },
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
    expect(composer).toHaveValue("Retry me");
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
});
