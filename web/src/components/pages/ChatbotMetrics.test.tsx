import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatbotMetrics } from "./ChatbotMetrics";

const METRICS = {
  conversations: 4,
  handoffs: 1,
  handoff_rate: 0.2,
  containment_rate: 0.8,
  handoff_reasons: { kb_miss: 1 },
  unknown_intents: 2,
  kb_hits: 3,
  kb_misses: 1,
  kb_hit_rate: 0.75,
  turns_to_resolve: 2.5,
  cost_per_conversation: 0.4,
  window_days: 7,
};

const EMPTY_DRILLDOWN = { window_days: 7, signal: "unknown_intent", conversations: [] };

function mockFetch(metricsBody: unknown, drilldownBody: unknown = EMPTY_DRILLDOWN) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = new URL(String(input), "http://localhost").pathname;
    const body = path.endsWith("/analytics/chatbot/conversations") ? drilldownBody : metricsBody;
    return new Response(JSON.stringify(body), { status: 200 });
  });
}

afterEach(() => vi.restoreAllMocks());

describe("ChatbotMetrics", () => {
  it("renders the bot KPIs from the analytics endpoint", async () => {
    mockFetch(METRICS);
    render(<ChatbotMetrics />);

    expect(await screen.findByText("Contención")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("Intenciones no reconocidas")).toBeInTheDocument();
    expect(screen.getByText("$0.40")).toBeInTheDocument();
    expect(screen.getByText("Últimos 7 días")).toBeInTheDocument();
  });

  it("refetches the metrics when the window changes", async () => {
    const fetchMock = mockFetch(METRICS);
    const user = userEvent.setup();
    render(<ChatbotMetrics />);
    await screen.findByText("Contención");

    await user.click(screen.getByRole("button", { name: "30 días" }));

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input]) => String(input).includes("window_days=30")),
      ).toBe(true),
    );
  });

  it("loads the drilldown for a signal and opens the conversation", async () => {
    const fetchMock = mockFetch(METRICS, {
      window_days: 7,
      signal: "unknown_intent",
      conversations: [
        {
          conversation_id: 42,
          customer_id: 7,
          wa_phone: "+56911111111",
          state: "active",
          last_message_at: "2026-10-13T10:00:00Z",
          signals: { escalation: 0, unknown_intent: 2, kb_miss: 0 },
        },
      ],
    });
    const onOpenConversation = vi.fn();
    const user = userEvent.setup();
    render(<ChatbotMetrics onOpenConversation={onOpenConversation} />);
    await screen.findByText("Contención");

    await user.click(screen.getByRole("button", { name: "Intención no reconocida" }));

    expect(await screen.findByText("#42")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Abrir" }));
    expect(onOpenConversation).toHaveBeenCalledWith(42);
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes("signal=unknown_intent")),
    ).toBe(true);
  });

  it("shows the denied state when the API returns 403", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "admin role required" }), { status: 403 }),
    );
    render(<ChatbotMetrics />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No tienes permiso para ver este panel",
    );
  });
});
