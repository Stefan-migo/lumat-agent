import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NotificationCenter } from "./NotificationCenter";

describe("NotificationCenter", () => {
  it("renders newest notifications and exposes unread filtering", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ notifications: [
      { id: 1, title: "Nueva visita", content: "Caso 9", source: "case", channel: "email", status: "sent", read_at: null, created_at: "2026-09-03T12:00:00Z" },
    ] }), { status: 200 }));
    render(<NotificationCenter />);
    expect(await screen.findByText("Nueva visita")).toBeInTheDocument();
    expect(screen.getByLabelText("Solo no leídas")).toBeInTheDocument();
  });

  it("marks a row read immediately without refetching the list and refetches when the filter changes", async () => {
    let listRequests = 0;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).includes("/read")) return new Response(JSON.stringify({ notification: { id: 1, read_at: "2026-09-03T12:00:01Z" } }), { status: 200 });
      listRequests += 1;
      return new Response(JSON.stringify({ notifications: [{ id: 1, title: "Nueva visita", content: "Caso 9", source: "case", channel: "email", status: "sent", read_at: null, created_at: null }] }), { status: 200 });
    });
    render(<NotificationCenter />);

    fireEvent.click(await screen.findByRole("button", { name: "Marcar como leída" }));
    expect(await screen.findByText("Leída")).toBeInTheDocument();
    expect(listRequests).toBe(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/notifications/1/read",
      expect.objectContaining({ method: "POST" }),
    );
    fireEvent.click(screen.getByLabelText("Solo no leídas"));
    await waitFor(() => expect(listRequests).toBe(2));
  });

  it("restores a row and announces the failure when marking it read is rejected", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).includes("/read")) return new Response("failure", { status: 500 });
      return new Response(JSON.stringify({ notifications: [{ id: 1, title: "Nueva visita", content: "Caso 9", source: "case", channel: "email", status: "sent", read_at: null, created_at: null }] }), { status: 200 });
    });
    render(<NotificationCenter />);

    fireEvent.click(await screen.findByRole("button", { name: "Marcar como leída" }));
    expect(await screen.findByRole("button", { name: "Marcar como leída" })).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos marcar la notificación como leída");
  });

  it("renders accessible empty and failed source states", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ notifications: [] }), { status: 200 }),
    );
    const { rerender } = render(<NotificationCenter />);
    expect(await screen.findByText("No hay notificaciones")).toBeInTheDocument();
    fetchMock.mockResolvedValueOnce(new Response("failure", { status: 500 }));
    rerender(<NotificationCenter key="failed" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar las notificaciones");
  });
});
