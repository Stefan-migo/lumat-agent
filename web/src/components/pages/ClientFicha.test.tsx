import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ClientFicha } from "./ClientFicha";
import type { ClientFichaResponse, Memory } from "../../types";

const ficha: ClientFichaResponse = {
  customer: {
    id: 7,
    name: "Marcela Fuentes",
    phone_e164: "+56912345678",
    email: "marcela@example.com",
    comuna: "Ñuñoa",
    address: "Av. Italia 123",
    state: "activo",
    consent_status: true,
    consent_at: null,
    created_at: "2026-07-15T12:00:00Z",
  },
  history: {
    conversations: [{ id: 1, state: "human", summary: "Coordinar visita", created_at: "2026-07-15T12:00:00Z", closed_at: null }],
   cases: [{ id: 2, conversation_id: 1, service: "Reparación", priority: "alta", status: "open", summary: "Calefón" }],
    messages: [{ id: 3, conversation_id: 1, direction: "inbound", msg_type: "text", text: "Necesito ayuda", media_url: null, created_at: "2026-07-15T12:00:00Z" }],
    appointments: [],
    visit_history: [],
  },
  notes: [{ id: 4, customer_id: 7, note: "Confirmar por WhatsApp", author: "operador", created_at: null }],
  memo: "Prefiere contacto por la tarde.",
  states: ["nuevo", "activo", "inactivo", "bloqueado"],
};

const memories: Memory[] = [{
  id: 5,
  scope: "customer",
  entity_id: "7",
  tipo: "preference",
  titulo: "Horario",
  contenido: "Prefiere contacto por la tarde.",
  topic_key: "horario",
  pin: true,
  status: "active",
  created_at: null,
  updated_at: null,
}];

describe("ClientFicha page grammar", () => {
  it("uses page rhythm and customer context without reserving a shell inspector", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("main")).toHaveTextContent("Ficha: Marcela Fuentes");
    expect(screen.getByText("+56912345678 · Estado: Activo")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Resumen del cliente" })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Inspector operacional" })).not.toBeInTheDocument();
  });

  it("retains operational cards, memory and note content, badges, and history tables", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("heading", { name: "Memo del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Memorias del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Notas" })).toBeInTheDocument();
    expect(screen.getAllByText("Prefiere contacto por la tarde.")).toHaveLength(2);
    expect(screen.getByText("operador · Confirmar por WhatsApp")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.getAllByRole("table")).toHaveLength(4);
    expect(screen.getByRole("heading", { name: "Visitas" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Conversaciones" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Casos" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mensajes" })).toBeInTheDocument();
  });
});
