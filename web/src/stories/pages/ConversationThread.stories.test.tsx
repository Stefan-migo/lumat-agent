import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConversationThread } from "../../components/pages/ConversationThread";
import { ConversationThreadBubbles, ConversationThreadView, ConversationThreadWithManyMessagesView, InteractiveConversationThreadView } from "./ConversationThread.stories";
import { conversations, messages } from "./_shared/mockData/conversations";

const conversation = conversations[0];
describe("ConversationThread", () => {
  it("loads a read-only thread from the thread endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ conversation, messages, messages_total: messages.length }), { status: 200 }));
    render(<ConversationThread conversationId={conversation.id} />);
    expect(await screen.findByText(messages[0].text!)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(`/panel/api/conversations/${conversation.id}?messages_limit=10`, expect.objectContaining({ credentials: "include" }));
    expect(screen.getAllByText(/canal automático/i).length).toBeGreaterThan(0);
    fetchMock.mockRestore();
  });

  it("renders directional bubbles and no reply controls", () => {
    render(<ConversationThread data={{ conversation, messages, messages_total: messages.length }} />);
    expect(screen.queryAllByRole("table")).toHaveLength(0);
    expect(screen.getAllByText(/Marcela Fuentes|Lumat/).length).toBeGreaterThan(0);
    expect(screen.queryByRole("textbox")).toBeNull();
    // The read-only thread keeps navigation chrome (client file, client details) but offers no reply
    // control at all, which is the rule this assertion protects.
    expect(screen.queryByRole("button", { name: /responder|enviar|adjuntar|grabar/i })).toBeNull();
    expect(screen.queryByRole("button", { name: "Tomar conversación" })).toBeNull();
  });

  it("renders the empty thread state", () => {
    render(<ConversationThread data={{ conversation, messages: [], messages_total: 0 }} />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("preserves the thread story exports", () => {
    render(<ConversationThreadView />);
    expect(screen.getByRole("heading", { name: "Marcela Fuentes" })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`#${conversation.id}`))).toBeInTheDocument();
    render(<ConversationThreadBubbles />);
    expect(screen.queryAllByRole("table")).toHaveLength(0);
    expect(screen.getAllByLabelText(/mensaje/i).length).toBeGreaterThan(0);
  });

  it("renders the interactive story action set", async () => {
    const user = userEvent.setup();
    render(<InteractiveConversationThreadView />);
    expect(screen.getByRole("button", { name: "Tomar conversación" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Acciones de la conversación" }));
    for (const label of ["Devolver al agente", "Cerrar conversación", "Reconocer emergencia"]) {
      expect(await screen.findByRole("menuitem", { name: label })).toBeInTheDocument();
    }
  });

  it("shows the message disclosure in the many-messages story", () => {
    render(<ConversationThreadWithManyMessagesView />);
    expect(screen.getByRole("button", { name: "2 mensajes anteriores · Ver todos" })).toBeInTheDocument();
  });

  it("renders the interactive story inspector content", () => {
    render(<InteractiveConversationThreadView />);
    expect(screen.getByRole("heading", { name: "Cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Caso vinculado" })).toBeInTheDocument();
    expect(screen.getByText("Datos capturados")).toBeInTheDocument();
    expect(screen.getByText("https://portal.aguas.cl/ordenes/2026/cliente-301/seguimiento-reparacion-urgente-987654321")).toBeInTheDocument();
  });
});
