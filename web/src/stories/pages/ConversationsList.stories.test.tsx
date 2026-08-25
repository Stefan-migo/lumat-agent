import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ConversationsList } from "../../components/pages/ConversationsList";
import { ConversationsListEmpty, ConversationsListView } from "./ConversationsList.stories";
import { conversations } from "./_shared/mockData/conversations";

describe("ConversationsList", () => {
  it("renders API rows without an Asignado column", () => {
    render(<ConversationsList data={{ conversations }} />);
    const table = screen.getByRole("table");
    expect(within(table).getByText(`#${conversations[0].id}`)).toBeInTheDocument();
    expect(within(table).getAllByText("Cliente #1").length).toBeGreaterThan(0);
    expect(within(table).queryByRole("columnheader", { name: "Asignado" })).toBeNull();
  });

  it("loads rows from GET /panel/api/conversations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ conversations }), { status: 200 }));
    render(<ConversationsList />);
    expect(await screen.findByText(`#${conversations[0].id}`)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/conversations", expect.objectContaining({ credentials: "include" }));
    fetchMock.mockRestore();
  });

  it("opens a thread from an activated row", () => {
    const onOpenThread = vi.fn();
    render(<ConversationsList data={{ conversations }} onOpenThread={onOpenThread} />);
    fireEvent.click(screen.getByRole("button", { name: `Abrir conversación #${conversations[0].id}` }));
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
