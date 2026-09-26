import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, apiFetch, addClientNote, changeClientState, resolveMemoryRelation } from "../../api";
import { ClientFicha } from "./ClientFicha";
import type { ClientFichaResponse, Memory } from "../../types";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, apiFetch: vi.fn(), addClientNote: vi.fn(), changeClientState: vi.fn(), resolveMemoryRelation: vi.fn() };
});

const ficha: ClientFichaResponse = {
  customer: {
    id: 7,
    name: "Marcela Fuentes",
    phone_e164: "+56912345678",
    email: "marcela@example.com",
    comuna: "Ñuñoa",
    address: "Av. Italia 123",
    state: "contactado",
    consent_status: true,
    consent_at: null,
    created_at: "2026-07-15T12:00:00Z",
  },
  history: {
    conversations: [{ id: 1, state: "human", summary: "Coordinar visita", created_at: "2026-07-15T12:00:00Z", closed_at: null }],
   cases: [{ id: 2, conversation_id: 1, service: "Reparación", priority: "alta", status: "open", summary: "Calefón" }],
    messages: [{ id: 3, conversation_id: 1, direction: "inbound", msg_type: "text", text: "Necesito ayuda", media_url: null, created_at: "2026-07-15T12:00:00Z" }],
    appointments: [],
  },
  notes: [{ id: 4, customer_id: 7, note: "Confirmar por WhatsApp", author: "operador", created_at: null }],
  memo: "Prefiere contacto por la tarde.",
  states: ["nuevo", "contactado", "pendiente", "agendado", "en_evaluacion", "finalizado", "cancelado", "postventa"],
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
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("uses page rhythm and customer context without reserving a shell inspector", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("main")).toHaveTextContent("Ficha: Marcela Fuentes");
    expect(screen.getByText("+56912345678 · Estado: Contactado")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Resumen del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("main").querySelector(".detail-region")).toBeInTheDocument();
    expect(screen.getByRole("main").querySelector(".detail-region__rail")).toBeInTheDocument();
    expect(screen.getByRole("main").querySelector(".detail-region__main")).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Inspector operacional" })).not.toBeInTheDocument();
  });

  it("retains operational cards, memory and note content, badges, and history tables", () => {
    const { container } = render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("heading", { name: "Memo del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Memorias del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Notas" })).toBeInTheDocument();
    expect(screen.getAllByText("Prefiere contacto por la tarde.")).toHaveLength(2);
    expect(screen.getByText("operador · Confirmar por WhatsApp")).toBeInTheDocument();
    expect(screen.getAllByText("Contactado").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("table")).toHaveLength(4);
    expect(screen.getByRole("heading", { name: "Visitas" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Conversaciones" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Casos" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mensajes" })).toBeInTheDocument();
    expect(container.querySelector('ol[aria-label="Ciclo de vida de visitas"]')).toBeNull();
  });

  it("posts state changes and notes, then refreshes ficha and memories", async () => {
    const user = userEvent.setup();
    vi.mocked(changeClientState).mockResolvedValue({ ok: true, state: "pendiente" });
    vi.mocked(addClientNote).mockResolvedValue({ ok: true, note: ficha.notes[0] });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.selectOptions(screen.getByLabelText("Estado del cliente"), "pendiente");
    await user.click(screen.getByRole("button", { name: "Guardar estado" }));
    await user.type(screen.getByLabelText("Nueva nota"), "Llamar mañana");
    await user.click(screen.getByRole("button", { name: "Agregar nota" }));

    expect(changeClientState).toHaveBeenCalledWith(7, "pendiente");
    expect(addClientNote).toHaveBeenCalledWith(7, "Llamar mañana");
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7");
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7/memories");
    expect(await screen.findByRole("heading", { name: "Nota agregada" })).toBeInTheDocument();
  });

  it("shows a pending relation and resolves it through the panel API", async () => {
    const user = userEvent.setup();
    const pending = {
      id: 12,
      memory_a: memories[0],
      memory_b: { ...memories[0], id: 6, titulo: "Mañana", contenido: "Prefiere contacto por la mañana." },
      relation: "conflicts" as const,
      confidence: 0.42,
      reason: "The judge is unsure which preference is current.",
      source: "judge",
      human_resolved_at: null,
      created_at: null,
    };
    let queue = true;
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path.endsWith("/memories")) return { memories };
      if (path.endsWith("/pending")) return { relations: queue ? [pending] : [] };
      return ficha;
    });
    vi.mocked(resolveMemoryRelation).mockImplementation(async () => {
      queue = false;
      return { ok: true, relation: { ...pending, relation: "not_conflict" } };
    });

    render(<ClientFicha customerId={7} />);

    expect(await screen.findByText(/The judge is unsure/)).toBeInTheDocument();
    expect(screen.getByText("Prefiere contacto por la mañana.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "not_conflict" }));

    expect(resolveMemoryRelation).toHaveBeenCalledWith(7, 12, "not_conflict");
    await waitFor(() => expect(screen.queryByText(/The judge is unsure/)).not.toBeInTheDocument());
  });

  it("shows safe mutation errors and disables controls while saving", async () => {
    const user = userEvent.setup();
    let reject!: (error: unknown) => void;
    vi.mocked(changeClientState).mockReturnValue(new Promise((_, nextReject) => { reject = nextReject; }));
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.selectOptions(screen.getByLabelText("Estado del cliente"), "pendiente");
    const save = screen.getByRole("button", { name: "Guardar estado" });
    await user.click(save);
    expect(save).toBeDisabled();
    reject(new ApiError(500, "database password leaked"));

    expect(await screen.findByRole("heading", { name: "No pudimos guardar estado" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).not.toHaveTextContent("database password leaked");
  });

  it("rejects an empty note before making the request", async () => {
    const user = userEvent.setup();
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: "Agregar nota" }));

    expect(addClientNote).not.toHaveBeenCalled();
    expect(screen.getByText("La nota no puede estar vacía")).toBeInTheDocument();
  });
});

describe("ClientFicha slice 2 — product register", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.restoreAllMocks());

  // T10 — the panel primitives, not raw native controls.
  it("uses the panel primitives for its controls instead of raw elements", () => {
    const { container } = render(<ClientFicha data={ficha} memories={memories} />);

    expect(container.querySelector("select")).toHaveClass("field__control");
    expect(container.querySelector("textarea")).toHaveClass("field__control");
    expect(container.querySelectorAll("button:not(.btn)")).toHaveLength(0);
  });

  // T11 — no raw backend identifier on the surface.
  it("does not expose the raw memory type identifier", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.queryByText("customer_memo")).not.toBeInTheDocument();
  });

  // T12 — labelled identity facts instead of bare paragraphs.
  it("renders the identity facts as labelled values", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    const summary = screen.getByRole("region", { name: "Resumen del cliente" });
    expect(within(summary).getByText("Teléfono")).toBeInTheDocument();
    expect(within(summary).getByText("+56912345678")).toBeInTheDocument();
    expect(within(summary).getByText("Comuna")).toBeInTheDocument();
    expect(within(summary).getByText("Ñuñoa")).toBeInTheDocument();
    expect(within(summary).getByText("Consentimiento")).toBeInTheDocument();
  });

  // T13 — feedback at the locus of the action.
  it("shows save feedback beside the control that caused it, not in the page banner", async () => {
    const user = userEvent.setup();
    vi.mocked(changeClientState).mockResolvedValue({ ok: true, state: "pendiente" });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const { container } = render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.selectOptions(screen.getByLabelText("Estado del cliente"), "pendiente");
    await user.click(screen.getByRole("button", { name: "Guardar estado" }));

    const control = container.querySelector(".client-ficha__state-control");
    expect(control).not.toBeNull();
    expect(await within(control as HTMLElement).findByText("Estado guardado")).toBeInTheDocument();
    // The page banner must not carry action feedback.
    expect(container.querySelector(".page-frame__banner")?.textContent ?? "").not.toContain("Estado guardado");
  });

  // T14 — history decomposed into named regions with Chilean-locale dates.
  it("splits the history into named regions instead of one card", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("region", { name: "Visitas" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Conversaciones" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Casos" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Mensajes" })).toBeInTheDocument();
  });

  it("formats history dates in the Chilean locale instead of slicing the ISO string", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    // The raw ISO slice is gone; what remains is the `es-CL` short shape (dd-mm-yy here).
    expect(screen.queryByText("2026-07-15")).not.toBeInTheDocument();
    expect(screen.getAllByText(/\d{2}-\d{2}-\d{2}/).length).toBeGreaterThan(0);
  });

  // T15 — the layout decision: two regions with a summary rail.
  it("composes the ficha into a summary rail plus a main region, with no conversation component", () => {
    const { container } = render(<ClientFicha data={ficha} memories={memories} />);

    expect(container.querySelector(".detail-region__rail")).not.toBeNull();
    expect(container.querySelector(".detail-region__main")).not.toBeNull();
    expect(container.querySelector(".ai-agent-grammar__bubble, .assistant-chat__conversation")).toBeNull();
  });

  // New requirement from the owner's review: the ficha had no way back.
  it("offers an explicit back control to the clients list", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("button", { name: "Volver a clientes" })).toBeInTheDocument();
  });

  it("returns through history when the back control is used", async () => {
    const user = userEvent.setup();
    const back = vi.spyOn(window.history, "back").mockImplementation(() => {});
    render(<ClientFicha data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: "Volver a clientes" }));

    expect(back).toHaveBeenCalledTimes(1);
  });
});
