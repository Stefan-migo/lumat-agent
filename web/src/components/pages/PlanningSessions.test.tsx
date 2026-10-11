import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PlanningSessions } from "./PlanningSessions";

describe("planning sessions", () => {
  afterEach(() => vi.restoreAllMocks());
  const session = { slug: "budget-review-8", proyecto: "default", topic: "Budget review", status: "closed" as const, thread_id: 8, opened_at: "2026-01-01", closed_at: "2026-01-02", report_key: "report" };
  it("renders list and detail with thread identity and report state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ sessions: [session] }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ session, thread: { id: 8, status: "open" }, report: null }), { status: 200 }));
    const { rerender } = render(<PlanningSessions />);
    expect(await screen.findByRole("button", { name: "Budget review" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Budget review" }));
    rerender(<PlanningSessions sessionSlug="budget-review-8" />);
    expect(await screen.findByText(/Hilo 8/)).toBeInTheDocument();
    expect(screen.getByText(/Hilo 8 · Cerrada/)).toBeInTheDocument();
    expect(screen.getByText(/Hilo 8 · Cerrada/).closest("p")?.querySelector(".badge")).toBeNull();
    expect(screen.queryByText("Decisiones")).not.toBeInTheDocument();
    expect(screen.queryByText("Derivación SDB")).not.toBeInTheDocument();
    expect(screen.getByText(/Apertura:/)).toHaveTextContent(new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(session.opened_at)));
    expect(screen.getByText(/Cierre:/)).toHaveTextContent(new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(session.closed_at)));
    expect(screen.getByText(/No hay un informe de cierre disponible/i)).toBeInTheDocument();
    const back = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    fireEvent.click(screen.getByRole("button", { name: "Volver a las sesiones de planificación" }));
    expect(back).toHaveBeenCalled();
  });
  it("shows an accessible failed read without fabricated sessions", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }));
    render(<PlanningSessions />);
    expect(await screen.findByRole("alert")).toHaveTextContent("acceso de administrador");
    expect(screen.queryByText("Budget review")).not.toBeInTheDocument();
  });
  it("navigates from a list row to its detail route", async () => {
    const onOpenSession = vi.fn();
    render(<PlanningSessions data={{ sessions: [session] }} onOpenSession={onOpenSession} />);
    fireEvent.click(screen.getByRole("button", { name: /budget review/i }));
    expect(onOpenSession).toHaveBeenCalledWith("budget-review-8");
  });

  it("opens the session thread from the row quick action", () => {
    const onOpenThread = vi.fn();
    render(<PlanningSessions data={{ sessions: [session] }} onOpenThread={onOpenThread} />);
    fireEvent.click(screen.getByRole("button", { name: "Abrir hilo" }));
    expect(onOpenThread).toHaveBeenCalledWith(8);
  });

  it("reopens a closed session and opens its thread", async () => {
    const onOpenThread = vi.fn();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ session, thread: { id: 8, status: "open" }, report: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ session, thread_id: 8 }), { status: 200 }));
    render(<PlanningSessions sessionSlug={session.slug} data={{ sessions: [] }} onOpenThread={onOpenThread} />);
    fireEvent.click(await screen.findByRole("button", { name: "Reabrir sesión" }));
    await waitFor(() => expect(onOpenThread).toHaveBeenCalledWith(8));
  });

  it("surfaces a failed reopen instead of navigating away silently", async () => {
    const onOpenThread = vi.fn();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ session, thread: { id: 8, status: "open" }, report: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "planning session is already active" }), { status: 409 }));
    render(<PlanningSessions sessionSlug={session.slug} data={{ sessions: [] }} onOpenThread={onOpenThread} />);
    fireEvent.click(await screen.findByRole("button", { name: "Reabrir sesión" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos reabrir la sesión de planificación");
    expect(screen.getByRole("alert")).toHaveTextContent("planning session is already active");
    expect(onOpenThread).not.toHaveBeenCalled();
  });
});
