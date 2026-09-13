import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { PlanningSessions } from "./PlanningSessions";

describe("planning sessions", () => {
  afterEach(() => vi.restoreAllMocks());
  const session = { slug: "budget-review-8", topic: "Budget review", status: "closed" as const, thread_id: 8, opened_at: "2026-01-01", closed_at: "2026-01-02", turn_index: 2, next_decision: null, last_class: "decision", decision_keys: [], report_key: "report", handoff: { status: "pending" as const, sdb_phase: "SPEC" as const } };
  it("renders list and detail with thread identity and report state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ sessions: [session] }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ session, thread: { id: 8, status: "open" }, decisions: [], report: null }), { status: 200 }));
    const { rerender } = render(<PlanningSessions />);
    expect(await screen.findByText("Budget review")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /budget review/i }));
    rerender(<PlanningSessions sessionSlug="budget-review-8" />);
    expect(await screen.findByText(/Thread 8/)).toBeInTheDocument();
    expect(screen.getByText(/No closing report/i)).toBeInTheDocument();
  });
  it("shows an accessible failed read without fabricated sessions", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }));
    render(<PlanningSessions />);
    expect(await screen.findByRole("alert")).toHaveTextContent("administrator access");
    expect(screen.queryByText("Budget review")).not.toBeInTheDocument();
  });
  it("navigates from a list row to its detail route", async () => {
    const onOpenSession = vi.fn();
    render(<PlanningSessions data={{ sessions: [session] }} onOpenSession={onOpenSession} />);
    fireEvent.click(screen.getByRole("button", { name: /budget review/i }));
    expect(onOpenSession).toHaveBeenCalledWith("budget-review-8");
  });
});
