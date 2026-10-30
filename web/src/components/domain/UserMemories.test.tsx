import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { UserMemories } from "./UserMemories";

afterEach(() => vi.restoreAllMocks());

const memories = [
  { id: 12, titulo: "Prefiere mensajes breves", contenido: "Prefiere que le escriban de forma directa.", tipo: "preference", topic_key: "communication-style", created_at: "2026-10-29T12:00:00Z", updated_at: "2026-10-29T12:00:00Z", review_after: null },
  { id: 11, titulo: "Vive en Ñuñoa", contenido: "Su casa está en Ñuñoa.", tipo: "discovery", topic_key: "home-location", created_at: "2026-10-28T12:00:00Z", updated_at: "2026-10-28T12:00:00Z", review_after: null },
];

function mockFetch(handler: (input: RequestInfo | URL, init?: RequestInit) => Response | Promise<Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => handler(input, init));
}

describe("UserMemories", () => {
  it("loads and renders title, content, type, and date for each memory", async () => {
    const fetchMock = mockFetch(() => new Response(JSON.stringify({ memories }), { status: 200 }));
    render(<UserMemories />);

    expect(await screen.findByText("Prefiere mensajes breves")).toBeInTheDocument();
    expect(screen.getByText("Prefiere que le escriban de forma directa.")).toBeInTheDocument();
    expect(screen.getByText("Preferencia")).toBeInTheDocument();
    expect(screen.getByText("29 oct 2026")).toBeInTheDocument();
    expect(screen.getByText("Vive en Ñuñoa")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/panel/api/assistant/memories", expect.objectContaining({ credentials: "include" }));
  });

  it("shows an empty state when there are no memories", async () => {
    mockFetch(() => new Response(JSON.stringify({ memories: [] }), { status: 200 }));
    render(<UserMemories />);

    expect(await screen.findByText("Sin memorias todavía")).toBeInTheDocument();
  });

  it("shows an error state when memories cannot be loaded", async () => {
    mockFetch(() => new Response(JSON.stringify({ detail: "failure" }), { status: 500 }));
    render(<UserMemories />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar tus memorias");
  });

  it("deletes a memory through the API and removes it from the list", async () => {
    const fetchMock = mockFetch((_, init) => {
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      return new Response(JSON.stringify({ memories }), { status: 200 });
    });
    render(<UserMemories />);

    const row = await screen.findByText("Prefiere mensajes breves");
    const article = row.closest("article");
    expect(article).not.toBeNull();
    fireEvent.click(within(article!).getByRole("button", { name: "Eliminar" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/assistant/memories/12",
      expect.objectContaining({ method: "DELETE", credentials: "include" }),
    ));
    await waitFor(() => expect(screen.queryByText("Prefiere mensajes breves")).not.toBeInTheDocument());
    expect(screen.getByText("Vive en Ñuñoa")).toBeInTheDocument();
  });
});
