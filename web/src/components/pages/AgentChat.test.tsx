import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AgentChat } from "./AgentChat";

describe("AgentChat", () => {
  afterEach(() => vi.restoreAllMocks());

  const sseResponse = (events: unknown[]) => {
    const body = events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("");
    return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
  };

  it("loads persisted messages and submits a new message", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: { id: 4, status: "open" }, messages: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: { id: 2, author: "admin", content: "Answer", status: "processed" } }), { status: 201 }));
    render(<AgentChat />);
    expect(await screen.findByText("Chat interno vacío")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: /mensaje/i }), { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Answer")).toBeInTheDocument();
  });

  it("renders persisted agent and administrator messages as directional bubbles", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({
      thread: { id: 4, status: "open" },
      messages: [
        { id: 1, author: "agent", content: "Agent answer", status: "processed" },
        { id: 2, author: "admin", content: "Administrator note", status: "processed" },
      ],
    }), { status: 200 }));

    render(<AgentChat />);

    const agentBubble = await screen.findByRole("article", { name: "Mensaje de agente" });
    const adminBubble = screen.getByRole("article", { name: "Mensaje de administrador" });
    expect(agentBubble.querySelector(".ai-agent-grammar__bubble")).toHaveClass("ai-agent-grammar__bubble");
    expect(adminBubble.querySelector(".ai-agent-grammar__bubble")).toHaveClass("ai-agent-grammar__bubble--outbound");
    expect(agentBubble.querySelector(".avatar")).toHaveTextContent("AL");
    expect(adminBubble.querySelector(".avatar")).toHaveTextContent("A");
  });

  it("shows a labeled empty state and disables the composer while processing", async () => {
    let resolveSend: (response: Response) => void = () => undefined;
    const pendingSend = new Promise<Response>((resolve) => { resolveSend = resolve; });
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: { id: 4, status: "open" }, messages: [] }), { status: 200 }))
      .mockReturnValueOnce(pendingSend);

    render(<AgentChat />);
    expect(await screen.findByText("Chat interno vacío")).toBeInTheDocument();
    const composer = screen.getByRole("textbox", { name: /mensaje/i });
    fireEvent.change(composer, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(screen.getByText("Procesando respuesta")).toBeInTheDocument();
    expect(composer).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
    resolveSend(new Response(JSON.stringify({ message: { id: 2, author: "agent", content: "Answer", status: "processed" } }), { status: 201 }));
  });

  it("keeps a failed submitted message visible and actionable", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: { id: 4, status: "open" }, messages: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: { id: 3, author: "admin", content: "Retry me", status: "failed", error: "temporary" } }), { status: 201 }));
    render(<AgentChat />);
    await screen.findByText("Chat interno vacío");
    fireEvent.change(screen.getByRole("textbox", { name: /mensaje/i }), { target: { value: "Retry me" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("No se pudo procesar el mensaje")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo procesar el mensaje");
    fireEvent.click(screen.getByRole("button", { name: /reintentar/i }));
    expect(screen.getByRole("textbox", { name: /mensaje/i })).toHaveValue("Retry me");
  });

  it("keeps the existing refusal text in the authorized thread without escalation copy", async () => {
    const refusal = "No puedo realizar esa acción fuera del approved operational workflow.";
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({
      thread: { id: 4, status: "open" },
      messages: [{ id: 5, author: "agent", content: refusal, status: "processed" }],
    }), { status: 200 }));

    render(<AgentChat />);

    expect(await screen.findByText(refusal)).toBeInTheDocument();
    expect(screen.queryByText(/herramientas privilegiadas|escalamiento nuevo/i)).not.toBeInTheDocument();
  });

  it("renders an actionable permission error without internal thread content", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: "No tienes permiso para ver el chat interno" }), { status: 403 }));

    render(<AgentChat />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver el chat interno");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByText("No hay mensajes todavía")).not.toBeInTheDocument();
  });

  it("renders a streamed plan, evidence, and final response in event order", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: { id: 4, status: "open" }, messages: [] }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: { id: 2, thread_id: 4, author: "admin", content: "Schedule it", status: "processing", assistant_metadata: { run_id: "run-1" } } }), { status: 201 }))
      .mockResolvedValueOnce(sseResponse([
        { type: "plan", thread_id: 4, run_id: "run-1", sequence: 0, plan: { tool: "appointments.create", arguments: { date: "tomorrow" }, status: "pending" } },
        { type: "status", thread_id: 4, run_id: "run-1", sequence: 1, status: "streaming" },
        { type: "tool", thread_id: 4, run_id: "run-1", sequence: 2, tool: "appointments.create", status: "completed" },
        { type: "evidence", thread_id: 4, run_id: "run-1", sequence: 3, evidence: [{ tool: "appointments.create", status: "completed", detail: "Appointment created" }] },
        { type: "response", thread_id: 4, run_id: "run-1", sequence: 4, content: "Done." },
      ]));

    render(<AgentChat />);
    await screen.findByText("Chat interno vacío");
    fireEvent.change(screen.getByRole("textbox", { name: /mensaje/i }), { target: { value: "Schedule it" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect((await screen.findAllByText("appointments.create")).length).toBeGreaterThan(0);
    expect(screen.getByText("Appointment created")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Done.")).toBeInTheDocument());
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("allows approving and rejecting a persisted pending plan after reload", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: {
        id: 4, status: "open", active_run_id: "run-2",
        current_plan: { tool: "automation.create_rule", arguments: { name: "Notify" }, status: "pending" },
        assistant_state: { stage: "approval_pending", approval: { token: "secret", status: "pending" } },
      }, messages: [] }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "rejected", message: { id: 3, author: "admin", content: "Write rule", status: "rejected" } }), { status: 200 }));

    render(<AgentChat />);
    expect(await screen.findByText("automation.create_rule")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /rechazar/i }));
    await waitFor(() => expect(screen.getByText(/rechazado/i)).toBeInTheDocument());
    expect(globalThis.fetch).toHaveBeenLastCalledWith(
      "/panel/api/chat/threads/4/approval",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ run_id: "run-2", token: "secret", reject: true }) }),
    );
  });
});
