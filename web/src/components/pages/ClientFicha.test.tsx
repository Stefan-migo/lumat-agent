import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, apiFetch, addClientNote, changeClientState, postJson, resolveMemoryRelation, updateCaseAmount, updateCustomerProfile, updateCustomerConsent, archiveCustomer, unarchiveCustomer, createClientEquipment, updateClientEquipment, listClientEquipment } from "../../api";
import { ClientFicha } from "./ClientFicha";
import type { ClientFichaResponse, Memory } from "../../types";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, apiFetch: vi.fn(), addClientNote: vi.fn(), changeClientState: vi.fn(), postJson: vi.fn(), resolveMemoryRelation: vi.fn(), updateCaseAmount: vi.fn(), updateCustomerProfile: vi.fn(), updateCustomerConsent: vi.fn(), archiveCustomer: vi.fn(), unarchiveCustomer: vi.fn(), createClientEquipment: vi.fn(), updateClientEquipment: vi.fn(), listClientEquipment: vi.fn() };
});

describe("ClientFicha equipment", () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(listClientEquipment).mockResolvedValue({ equipment: [] }); });

  const equipment = [
    { id: 11, customer_id: 7, equipment_type: "calefont", brand: "Bosch", model: "Therm 5600", age: "5 años", details: "Calefont Bosch, instalado hace cinco años", source_conversation_id: 4, created_at: null, updated_at: null },
    { id: 12, customer_id: 7, equipment_type: null, brand: null, model: null, age: null, details: "Tiene una caldera antigua", source_conversation_id: 5, created_at: null, updated_at: null },
  ];

  it("renders equipment fields and a details-only row gracefully", async () => {
    vi.mocked(listClientEquipment).mockResolvedValue({ equipment });
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    const section = await screen.findByRole("region", { name: "Equipos" });
    expect(within(section).getByText("Calefont")).toBeInTheDocument();
    expect(within(section).getByText("Bosch · Therm 5600 · 5 años")).toBeInTheDocument();
    expect(within(section).getByText("Calefont Bosch, instalado hace cinco años")).toBeInTheDocument();
    expect(within(section).getByText("Tiene una caldera antigua")).toBeInTheDocument();
  });

  it("adds equipment from the dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(createClientEquipment).mockResolvedValue({ equipment: equipment[0] });
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(await screen.findByRole("button", { name: "Agregar equipo" }));
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Tipo"), "calefont");
    await user.type(within(dialog).getByLabelText("Marca"), "Bosch");
    await user.click(within(dialog).getByRole("button", { name: "Guardar equipo" }));

    expect(createClientEquipment).toHaveBeenCalledWith(7, { equipment_type: "calefont", brand: "Bosch", model: null, age: null, details: null });
  });

  it("edits equipment through the dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(updateClientEquipment).mockResolvedValue({ equipment: equipment[0] });
    vi.mocked(listClientEquipment).mockResolvedValue({ equipment: [equipment[0]] });
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(await screen.findByRole("button", { name: "Editar equipo" }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Marca"));
    await user.type(within(dialog).getByLabelText("Marca"), "Bosch renovado");
    await user.click(within(dialog).getByRole("button", { name: "Guardar equipo" }));

    expect(updateClientEquipment).toHaveBeenCalledWith(7, 11, { equipment_type: "calefont", brand: "Bosch renovado", model: "Therm 5600", age: "5 años", details: "Calefont Bosch, instalado hace cinco años" });
  });
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
    cases: [
      { id: 2, conversation_id: 1, customer_id: 7, created_at: "2026-07-15T12:00:00Z", service: "Reparación", amount: null, priority: "alta", status: "open", summary: "Calefón", emergency: true, responsible_id: 9, escalated_at: null, closed_at: null, acknowledged_at: null, ack_by: null, is_open: true },
      { id: 1, conversation_id: 1, customer_id: 7, created_at: "2026-07-14T12:00:00Z", service: "Gasfitería", amount: null, priority: "normal", status: "cerrado", summary: "Llave", emergency: false, responsible_id: null, escalated_at: null, closed_at: "2026-07-14T14:00:00Z", acknowledged_at: null, ack_by: null, is_open: false },
    ],
    messages: [{ id: 3, conversation_id: 1, direction: "inbound", msg_type: "text", text: "Necesito ayuda", media_url: null, created_at: "2026-07-15T12:00:00Z" }],
    messages_total: 12,
    appointments: [],
  },
  users: [{ id: 9, username: "operador" }],
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
    expect(screen.getByRole("heading", { name: "Casos anteriores" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mensajes" })).toBeInTheDocument();
    expect(container.querySelector('ol[aria-label="Ciclo de vida de visitas"]')).toBeNull();
  });

  it("renders active case facts and keeps it out of the archive", () => {
    render(<ClientFicha data={ficha} memories={memories} />);
    expect(screen.getByRole("heading", { name: "Caso activo" })).toBeInTheDocument();
    expect(screen.getByText("Emergencia sin reconocer")).toBeInTheDocument();
    expect(screen.getAllByText("operador").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Estado caso 2")).toBeInTheDocument();
    const archive = screen.getByRole("region", { name: "Casos anteriores" });
    expect(within(archive).queryByText("#2")).not.toBeInTheDocument();
    expect(within(archive).getByText("#1")).toBeInTheDocument();
  });

  it("renders a nullable CLP case amount and saves it through the existing update API", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCaseAmount).mockResolvedValue({ ok: true, case: { ...ficha.history.cases[0], amount: 200000, customer: ficha.customer } });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const withAmount = { ...ficha, history: { ...ficha.history, cases: ficha.history.cases.map((row) => row.id === 2 ? { ...row, amount: 125000 } : row) } };
    render(<ClientFicha customerId={7} data={withAmount} memories={memories} />);

    expect(screen.getByText(/125\.000/)).toBeInTheDocument();
    expect(screen.getByText("Sin monto registrado")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Editar monto del caso" }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Monto CLP"));
    await user.type(within(dialog).getByLabelText("Monto CLP"), "200000");
    await user.click(within(dialog).getByRole("button", { name: "Guardar monto" }));

    expect(updateCaseAmount).toHaveBeenCalledWith(2, 200000);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10"));
  });

  it("updates and acknowledges an active case, then refetches the ficha", async () => {
    const user = userEvent.setup();
    vi.mocked(postJson).mockResolvedValue({ ok: true });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await user.selectOptions(screen.getByLabelText("Estado caso 2"), "cerrado");
    await user.selectOptions(screen.getByLabelText("Responsable caso 2"), "");
    await user.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(postJson).toHaveBeenCalledWith("/panel/api/cases/2/update", { status: "cerrado", responsible_id: null });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10"));
    await user.click(screen.getByRole("button", { name: "Reconocer" }));
    expect(postJson).toHaveBeenCalledWith("/panel/api/cases/2/ack");
  });

  it("shows local feedback when a case update fails", async () => {
    const user = userEvent.setup();
    vi.mocked(postJson).mockRejectedValue(new ApiError(500, "private error"));
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await user.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(await screen.findByRole("heading", { name: "No pudimos guardar el caso" })).toBeInTheDocument();
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
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10");
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

    expect(await screen.findByRole("heading", { name: "No pudimos guardar el estado" })).toBeInTheDocument();
    expect(screen.getAllByRole("alert").every((alert) => !alert.textContent?.includes("database password leaked"))).toBe(true);
  });

  it("rejects an empty note before making the request", async () => {
    const user = userEvent.setup();
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: "Agregar nota" }));

    expect(addClientNote).not.toHaveBeenCalled();
    expect(screen.getByText("La nota no puede estar vacía")).toBeInTheDocument();
  });
});

describe("ClientFicha customer controls", () => {
  beforeEach(() => vi.clearAllMocks());

  it("edits profile fields in a dialog without allowing phone changes", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCustomerProfile).mockResolvedValue({ customer: ficha.customer });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: "Editar identidad" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Teléfono")).toHaveAttribute("readonly");
    await user.clear(within(dialog).getByLabelText("Nombre"));
    await user.type(within(dialog).getByLabelText("Nombre"), "Marcela Rojas");
    await user.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));

    expect(updateCustomerProfile).toHaveBeenCalledWith(7, { name: "Marcela Rojas" });
    expect(await screen.findByRole("heading", { name: "Identidad guardada" })).toBeInTheDocument();
  });

  it("shows a local message rather than silently dropping a blank changed field", async () => {
    const user = userEvent.setup();
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await user.click(screen.getByRole("button", { name: "Editar identidad" }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Nombre"));
    await user.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));
    expect(updateCustomerProfile).not.toHaveBeenCalled();
    expect(within(dialog).getByRole("alert")).toHaveTextContent("No puedes dejar vacío un campo editado");
  });

  it("updates consent and surfaces failures beside its control", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCustomerConsent).mockRejectedValue(new ApiError(500, "private"));
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await user.click(screen.getByRole("button", { name: "Cambiar consentimiento" }));
    expect(updateCustomerConsent).toHaveBeenCalledWith(7, false);
    expect(await screen.findByRole("heading", { name: "No pudimos guardar el consentimiento" })).toBeInTheDocument();
  });

  it("warns with loaded open-case and future-appointment counts before archiving", async () => {
    const user = userEvent.setup();
    const futureStart = new Date(Date.now() + 86_400_000).toISOString();
    const futureAppointment = { id: 44, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: futureStart, timezone: "UTC", starts_at: futureStart, ends_at: futureStart, duration_minutes: 60, status: "booked" };
    vi.mocked(archiveCustomer).mockResolvedValue({ customer: ficha.customer });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={{ ...ficha, history: { ...ficha.history, appointments: [futureAppointment] } }} memories={memories} />);
    await user.click(screen.getByRole("button", { name: "Archivar" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("1 caso abierto");
    expect(dialog).toHaveTextContent("1 visita futura");
    await user.click(within(dialog).getByRole("button", { name: "Confirmar archivo" }));
    expect(archiveCustomer).toHaveBeenCalledWith(7);
    expect(await screen.findByRole("heading", { name: "Cliente archivado" })).toBeInTheDocument();
  });

  it("shows an archive failure once, with a readable label", async () => {
    const user = userEvent.setup();
    vi.mocked(archiveCustomer).mockRejectedValue(new ApiError(500, "private"));
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await user.click(screen.getByRole("button", { name: "Archivar" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmar archivo" }));
    expect(await screen.findAllByRole("heading", { name: "No pudimos guardar el archivo" })).toHaveLength(1);
  });

  it("shows archived state and offers restore with visible failure feedback", async () => {
    const user = userEvent.setup();
    vi.mocked(unarchiveCustomer).mockRejectedValue(new ApiError(500, "private"));
    render(<ClientFicha customerId={7} data={{ ...ficha, customer: { ...ficha.customer, archived_at: "2026-09-01T00:00:00Z" } }} memories={memories} />);
    expect(screen.getByText("Cliente archivado")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Restaurar" }));
    expect(unarchiveCustomer).toHaveBeenCalledWith(7);
    expect(await screen.findByRole("heading", { name: "No pudimos guardar el archivo" })).toBeInTheDocument();
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
    expect(container.querySelectorAll("button:not(.btn):not(.dialog__close)")).toHaveLength(0);
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
    expect(within(summary).getByText("Teléfono", { selector: "dt" })).toBeInTheDocument();
    expect(within(summary).getByText("+56912345678")).toBeInTheDocument();
    expect(within(summary).getByText("Comuna", { selector: "dt" })).toBeInTheDocument();
    expect(within(summary).getByText("Ñuñoa")).toBeInTheDocument();
    expect(within(summary).getByText("Consentimiento", { selector: "dt" })).toBeInTheDocument();
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
    expect(screen.getByRole("region", { name: "Casos anteriores" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Mensajes" })).toBeInTheDocument();
  });

  it("formats history dates in the Chilean locale instead of slicing the ISO string", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    // The raw ISO slice is gone; what remains is the `es-CL` short shape (dd-mm-yy here).
    expect(screen.queryByText("2026-07-15")).not.toBeInTheDocument();
    expect(screen.getAllByText(/\d{2}-\d{2}-\d{2}/).length).toBeGreaterThan(0);
  });

  it("links each visit to its appointment detail and keeps calendar retry outside the link", async () => {
    const user = userEvent.setup();
    const visit = { id: 42, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: "2026-07-15T12:00:00Z", timezone: "UTC", starts_at: "2026-07-15T12:00:00Z", ends_at: "2026-07-15T13:00:00Z", duration_minutes: 60, status: "booked", calendar_error: "Proveedor no disponible" };
    render(<ClientFicha data={{ ...ficha, history: { ...ficha.history, appointments: [visit] } }} memories={memories} onRetryCalendar={vi.fn()} />);

    const link = screen.getByRole("link", { name: /Reparación/ });
    expect(link).toHaveAttribute("href", "/panel/app/agenda/42");
    const retry = screen.getByRole("button", { name: "Reintentar calendario" });
    expect(retry.closest("a")).toBeNull();
    await user.click(retry);
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/appointments/42/calendar/sync", { method: "POST" });
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

  it("links each message to its conversation and offers expansion when more than ten exist", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("link", { name: "#1" })).toHaveAttribute("href", "/panel/app/conversations/1");
    expect(screen.getByRole("button", { name: "Ver todos (12)" })).toBeInTheDocument();
  });

  it("loads a ten-message preview and fetches the full list when expanded", async () => {
    const user = userEvent.setup();
    const allMessages = Array.from({ length: 12 }, (_, index) => ({
      ...ficha.history.messages[0], id: index + 1, text: `Mensaje ${index + 1}`,
    }));
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path.endsWith("/memories")) return { memories };
      if (path.endsWith("/pending")) return { relations: [] };
      return {
        ...ficha,
        history: {
          ...ficha.history,
          messages: path.includes("messages_limit=10") ? allMessages.slice(-10) : allMessages,
        },
      };
    });

    render(<ClientFicha customerId={7} memories={memories} />);
    expect(await screen.findByText("Mensaje 3")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10");
    await user.click(screen.getByRole("button", { name: "Ver todos (12)" }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7"));
    expect(await screen.findByText("Mensaje 1")).toBeInTheDocument();
    expect(screen.getByText("Mensaje 12")).toBeInTheDocument();
  });

  it("hides the disclosure control when ten or fewer messages exist", () => {
    render(<ClientFicha data={{ ...ficha, history: { ...ficha.history, messages_total: 10 } }} memories={memories} />);

    expect(screen.queryByRole("button", { name: /Ver todos/ })).not.toBeInTheDocument();
  });
});
