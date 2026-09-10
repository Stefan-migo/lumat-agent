import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ConversationsList } from "../../components/pages/ConversationsList";
import { ConversationsListEmpty, ConversationsListView } from "./ConversationsList.stories";
import { conversations } from "./_shared/mockData/conversations";

describe("ConversationsList", () => {
  it("renders API rows without an Asignado column", () => {
    render(<ConversationsList data={{ conversations }} />);
    const list = screen.getByRole("list");
    expect(within(list).getAllByText("Cliente #1").length).toBeGreaterThan(0);
    expect(within(list).getAllByText(conversations[0].wa_phone!).length).toBeGreaterThan(0);
  });

  it("loads rows from GET /panel/api/conversations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ conversations }), { status: 200 }));
    render(<ConversationsList />);
    expect((await screen.findAllByText(`Cliente #${conversations[0].customer_id}`)).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/conversations", expect.objectContaining({ credentials: "include" }));
    fetchMock.mockRestore();
  });

  it("opens a thread from an activated row", () => {
    const onOpenThread = vi.fn();
    render(<ConversationsList data={{ conversations }} onOpenThread={onOpenThread} />);
    fireEvent.click(screen.getByTestId(`conversation-row-${conversations[0].id}`));
    expect(onOpenThread).toHaveBeenCalledWith(conversations[0].id);
  });

  it("renders the story empty state", () => {
    render(<ConversationsListEmpty />);
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });

  it("preserves the story view export", () => {
    render(<ConversationsListView />);
    expect(screen.getByRole("heading", { name: "Conversaciones" })).toBeInTheDocument();
  });
});
