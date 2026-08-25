import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ConversationThread } from "../../components/pages/ConversationThread";
import { ConversationThreadBubbles, ConversationThreadView } from "./ConversationThread.stories";
import { conversations, messages } from "./_shared/mockData/conversations";

const conversation = conversations[0];
describe("ConversationThread", () => {
  it("loads a read-only thread from the thread endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ conversation, messages }), { status: 200 }));
    render(<ConversationThread conversationId={conversation.id} />);
    expect(await screen.findByText(messages[0].text!)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(`/panel/api/conversations/${conversation.id}`, expect.objectContaining({ credentials: "include" }));
    expect(screen.getByRole("status")).toHaveTextContent(/canal automático/i);
    fetchMock.mockRestore();
  });

  it("renders message rows and no reply controls", () => {
    render(<ConversationThread data={{ conversation, messages }} />);
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Dirección" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders the empty thread state", () => {
    render(<ConversationThread data={{ conversation, messages: [] }} />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("preserves the thread story exports", () => {
    render(<ConversationThreadView />);
    expect(screen.getByRole("heading", { name: `# ${conversation.id}` })).toBeInTheDocument();
    render(<ConversationThreadBubbles />);
    expect(screen.getAllByRole("table").length).toBeGreaterThan(0);
  });
});
