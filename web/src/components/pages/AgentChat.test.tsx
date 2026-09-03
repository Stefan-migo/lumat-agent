import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AgentChat } from "./AgentChat";

describe("AgentChat", () => {
  it("loads persisted messages and submits a new message", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: { id: 4, status: "open" }, messages: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: { id: 2, author: "admin", content: "Answer", status: "processed" } }), { status: 201 }));
    render(<AgentChat />);
    expect(await screen.findByText("No hay mensajes todavía")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: /mensaje/i }), { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Answer")).toBeInTheDocument();
  });

  it("keeps a failed submitted message visible and actionable", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ thread: { id: 4, status: "open" }, messages: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: { id: 3, author: "admin", content: "Retry me", status: "failed", error: "temporary" } }), { status: 201 }));
    render(<AgentChat />);
    await screen.findByText("No hay mensajes todavía");
    fireEvent.change(screen.getByRole("textbox", { name: /mensaje/i }), { target: { value: "Retry me" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("No se pudo procesar el mensaje")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
  });
});
