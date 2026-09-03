import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { NotificationCenter } from "./NotificationCenter";

describe("NotificationCenter", () => {
  it("renders newest notifications and exposes unread filtering", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ notifications: [
      { id: 1, title: "Nueva visita", content: "Caso 9", source: "case", channel: "email", status: "sent", read_at: null, created_at: "2026-09-03T12:00:00Z" },
    ] }), { status: 200 }));
    render(<NotificationCenter />);
    expect(await screen.findByText("Nueva visita")).toBeInTheDocument();
    expect(screen.getByLabelText("Filtrar no leídas")).toBeInTheDocument();
  });
});
