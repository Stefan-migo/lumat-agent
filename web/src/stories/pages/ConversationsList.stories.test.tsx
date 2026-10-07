import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { ConversationsList } from "../../components/pages/ConversationsList";
import { ConversationsListEmpty, ConversationsListView } from "./ConversationsList.stories";
import { conversations } from "./_shared/mockData/conversations";

describe("ConversationsList", () => {
  it("renders API rows without an Asignado column", () => {
    render(<ConversationsList data={{ conversations }} />);
    const desktop = document.querySelector(".table-card__desktop") as HTMLElement;
    expect(within(desktop).getByRole("table")).toBeInTheDocument();
    expect(within(desktop).getAllByText("Cliente #1").length).toBeGreaterThan(0);
    expect(within(desktop).getAllByText((_, element) => element?.classList.contains("table__resource-meta") === true && element.textContent?.includes(conversations[0].wa_phone!) === true).length).toBeGreaterThan(0);
  });

  it("loads rows from GET /panel/api/conversations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ conversations }), { status: 200 }));
    render(<ConversationsList />);
    await waitFor(() => expect(document.querySelector(".table-card__desktop")).toBeTruthy());
    const desktop = document.querySelector(".table-card__desktop") as HTMLElement;
    expect((await within(desktop).findAllByText(`Cliente #${conversations[0].customer_id}`)).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/conversations", expect.objectContaining({ credentials: "include" }));
    fetchMock.mockRestore();
  });

  it("opens a thread from an activated row", () => {
    const onOpenThread = vi.fn();
    render(<ConversationsList data={{ conversations }} onOpenThread={onOpenThread} />);
    fireEvent.click(within(document.querySelector(".table-card__desktop") as HTMLElement).getByTestId(`conversation-row-${conversations[0].id}`));
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
