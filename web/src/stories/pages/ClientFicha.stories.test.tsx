import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ClientFicha } from "../../components/pages/ClientFicha";
import { ClientFichaView, NoMemo } from "./ClientFicha.stories";
import { clients } from "./_shared/mockData/clients";

const customer = clients[0];
const fichaResponse = {
  customer,
  history: { conversations: [], cases: [], messages: [] },
  notes: [],
  memo: "Acta de cierre de Marcela",
  states: ["nuevo", "activo", "inactivo", "bloqueado"],
};
const memoriesResponse = {
  memories: [{
    id: 11,
    scope: "customer",
    entity_id: String(customer.id),
    tipo: "preference" as const,
    titulo: "Horario",
    contenido: "Prefiere contacto por la tarde.",
    topic_key: "contacto",
    pin: false,
    status: "active" as const,
    created_at: null,
    updated_at: null,
  }],
};

beforeEach(() => vi.restoreAllMocks());

describe("ClientFicha page", () => {
  it("renders the ficha sections and customer memories from the API", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(
      JSON.stringify(String(input).endsWith("/memories") ? memoriesResponse : fichaResponse),
      { status: 200 },
    ));

    render(<ClientFicha customerId={customer.id} />);
    expect(screen.getByRole("heading", { name: "Cargando ficha" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("heading", { name: `Ficha: ${customer.name}` })).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Memo del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Memorias del cliente" })).toBeInTheDocument();
    expect(screen.getByText("Prefiere contacto por la tarde.")).toBeInTheDocument();
    expect(screen.getByText("Acta de cierre de Marcela")).toBeInTheDocument();
  });

  it("renders the no-memo state without an error surface", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => new Response(
      JSON.stringify(String(input).endsWith("/memories") ? { memories: [] } : { ...fichaResponse, memo: "" }),
      { status: 200 },
    ));

    render(<ClientFicha customerId={customer.id} />);
    await waitFor(() => expect(screen.getByText("Todavía no hay memo para este cliente.")).toBeInTheDocument());
    expect(screen.getByText("Sin memorias todavía")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("preserves story wrappers for populated and no-memo variants", () => {
    render(<><ClientFichaView /><NoMemo /></>);
    expect(screen.getAllByRole("heading", { name: "Ficha: Marcela Fuentes" })).toHaveLength(2);
    expect(screen.getByText("Todavía no hay memo para este cliente.")).toBeInTheDocument();
  });
});
