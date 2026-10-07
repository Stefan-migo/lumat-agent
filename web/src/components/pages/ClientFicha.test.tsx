import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, apiFetch, addClientNote, cancelAppointment, changeClientState, closeAppointment, deleteClientNote, postJson, resolveMemoryRelation, updateCaseAmount, updateCustomerProfile, updateCustomerConsent, archiveCustomer, unarchiveCustomer, createClientEquipment, updateClientEquipment, updateClientNote, listClientEquipment, fetchClients, getConversation, previewClientMerge, mergeClient } from "../../api";
import { ClientFicha } from "./ClientFicha";
import type { ClientFichaResponse, ConversationThread, Memory } from "../../types";

vi.mock("../../api", async () => {
  const actual = await vi.importActual<typeof import("../../api")>("../../api");
  return { ...actual, apiFetch: vi.fn(), addClientNote: vi.fn(), cancelAppointment: vi.fn(), changeClientState: vi.fn(), closeAppointment: vi.fn(), deleteClientNote: vi.fn(), postJson: vi.fn(), resolveMemoryRelation: vi.fn(), updateCaseAmount: vi.fn(), updateCustomerProfile: vi.fn(), updateCustomerConsent: vi.fn(), archiveCustomer: vi.fn(), unarchiveCustomer: vi.fn(), createClientEquipment: vi.fn(), updateClientEquipment: vi.fn(), updateClientNote: vi.fn(), listClientEquipment: vi.fn(), fetchClients: vi.fn(), getConversation: vi.fn(), previewClientMerge: vi.fn(), mergeClient: vi.fn() };
});

// The Mensajes card loads the selected conversation thread through `getConversation`.
beforeEach(() => {
  vi.mocked(getConversation).mockResolvedValue({ conversation: ficha.history.conversations[0], messages: ficha.history.messages, messages_total: ficha.history.messages.length } as unknown as ConversationThread);
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
    expect(within(dialog).getByText("Registra un equipo asociado al cliente.")).toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText("Tipo de equipo"));
    await user.type(within(dialog).getByLabelText("Tipo de equipo"), "Calefont");
    await user.type(within(dialog).getByLabelText("Marca (opcional)"), "Bosch");
    await user.click(within(dialog).getByRole("button", { name: "Agregar equipo" }));

    expect(createClientEquipment).toHaveBeenCalledWith(7, { equipment_type: "Calefont", brand: "Bosch", model: null, age: null, details: null });
  });

  it("edits equipment through the dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(updateClientEquipment).mockResolvedValue({ equipment: equipment[0] });
    vi.mocked(listClientEquipment).mockResolvedValue({ equipment: [equipment[0]] });
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(await screen.findByRole("button", { name: "Editar equipo" }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Marca (opcional)"));
    await user.type(within(dialog).getByLabelText("Marca (opcional)"), "Bosch renovado");
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
    allowed_transitions: ["pendiente", "agendado"],
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
  tipo: "customer_memo",
  titulo: "Horario",
  contenido: "Prefiere contacto por la tarde.",
  topic_key: "customer_memo",
  pin: true,
  status: "active",
  created_at: null,
  updated_at: null,
}];

async function clickCustomerMenuItem(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole("button", { name: `Acciones para ${ficha.customer.name}` }));
  await user.click(await screen.findByRole("menuitem", { name: label }));
}

async function clickCaseMenuItem(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole("button", { name: "Acciones del caso" }));
  await user.click(await screen.findByRole("menuitem", { name: label }));
}

// The archived rows render twice (desktop table + mobile cards); scope to the desktop copy.
function archivedRowMenu(id: number) {
  return screen.getAllByRole("button", { name: `Acciones del caso #${id}` }).find((button) => button.closest(".table-card__desktop"))!;
}

// Visit rows also render twice (desktop table + mobile cards); scope to the desktop copy.
function desktopOnly<T extends HTMLElement>(elements: T[]): T[] {
  return elements.filter((element) => element.closest(".table-card__desktop"));
}

describe("ClientFicha page grammar", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it("uses page rhythm and customer context without reserving a shell inspector", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.getByRole("heading", { level: 1, name: "Marcela Fuentes" })).toBeInTheDocument();
    expect(screen.getAllByText(/Cliente desde/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Agendar visita" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver conversación" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Resumen del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("main").querySelector(".detail-region")).toBeInTheDocument();
    expect(screen.getByRole("main").querySelector(".detail-region__rail")).toBeInTheDocument();
    expect(screen.getByRole("main").querySelector(".detail-region__main")).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Inspector operacional" })).not.toBeInTheDocument();
  });

  it("retains operational cards, memory and note content, badges, and history tables", () => {
    const { container } = render(<ClientFicha data={ficha} memories={memories} />);

    expect(screen.queryByRole("heading", { name: "Memo del cliente" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Memoria del cliente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Notas" })).toBeInTheDocument();
    expect(screen.getAllByText("Prefiere contacto por la tarde.")).toHaveLength(1);
    expect(screen.getByText("Confirmar por WhatsApp")).toBeInTheDocument();
    expect(screen.getAllByText("Contactado").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Casos anteriores" })).not.toBeInTheDocument();
    expect(screen.getByRole("tablist", { name: "Secciones de la ficha del cliente" })).toBeInTheDocument();
    expect(container.querySelector('ol[aria-label="Ciclo de vida de visitas"]')).toBeNull();
  });

  it("renders active case facts and keeps it out of the archive", async () => {
    const user = userEvent.setup();
    render(<ClientFicha data={ficha} memories={memories} />);
    expect(screen.getByText("CASO ACTIVO")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Reparación" })).toBeInTheDocument();
    expect(screen.getByText("Emergencia sin reconocer")).toBeInTheDocument();
    expect(screen.getByText("operador", { selector: ".client-ficha__case-details strong" })).toBeInTheDocument();
    expect(screen.queryByText("operador⌄")).not.toBeInTheDocument();
    await clickCaseMenuItem(user, "Editar caso");
    expect(screen.getByLabelText("Estado")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Casos" }));
    const archive = screen.getByRole("region", { name: "Casos anteriores" });
    expect(within(archive).queryByText("#2")).not.toBeInTheDocument();
    expect(within(archive).getAllByText("#1").length).toBeGreaterThan(0);
    expect(within(archive).getByText("Mostrando 1 caso anterior")).toBeInTheDocument();
  });

  it("renders a nullable CLP case amount and saves it through the existing update API", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCaseAmount).mockResolvedValue({ ok: true, case: { ...ficha.history.cases[0], amount: 200000, customer: ficha.customer } });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const withAmount = { ...ficha, history: { ...ficha.history, cases: ficha.history.cases.map((row) => row.id === 2 ? { ...row, amount: 125000 } : row) } };
    render(<ClientFicha customerId={7} data={withAmount} memories={memories} />);

    expect(screen.getAllByText(/125\.000/).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("tab", { name: "Casos" }));
    expect(within(screen.getByRole("region", { name: "Casos anteriores" })).getAllByText("Sin registrar").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("tab", { name: "Resumen" }));
    await clickCaseMenuItem(user, "Definir monto");
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Monto del servicio"));
    await user.type(within(dialog).getByLabelText("Monto del servicio"), "200000");
    await user.click(within(dialog).getByRole("button", { name: "Guardar monto" }));

    expect(updateCaseAmount).toHaveBeenCalledWith(2, 200000);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10"));
  });

  it("rejects a negative case amount before calling the API", async () => {
    const user = userEvent.setup();
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCaseMenuItem(user, "Definir monto");
    const dialog = screen.getByRole("dialog");
    const input = within(dialog).getByLabelText("Monto del servicio");
    // fireEvent bypasses native constraint validation, mirroring the advisory's
    // "submitted outside the HTML form UI" case for a `type="number"` field.
    // A malformed/non-finite value is not representable here: the number input
    // sanitizes it to "" (the documented "clear" input), so there is no NaN path.
    fireEvent.change(input, { target: { value: "-1" } });
    fireEvent.submit(input.closest("form")!);

    expect(updateCaseAmount).not.toHaveBeenCalled();
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Ingresa un monto CLP válido y no negativo");
  });

  it("updates and acknowledges an active case, then refetches the ficha", async () => {
    const user = userEvent.setup();
    vi.mocked(postJson).mockResolvedValue({ ok: true });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await clickCaseMenuItem(user, "Editar caso");
    await user.selectOptions(screen.getByLabelText("Estado"), "cerrado");
    await user.selectOptions(screen.getByLabelText("Responsable"), "");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(postJson).toHaveBeenCalledWith("/panel/api/cases/2/update", { status: "cerrado", responsible_id: null });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10"));
    await user.click(screen.getByRole("tab", { name: "Casos" }));
    await clickCaseMenuItem(user, "Editar caso");
    await user.click(screen.getByRole("button", { name: "Reconocer" }));
    expect(postJson).toHaveBeenCalledWith("/panel/api/cases/2/ack");
  });

  it("edits an archived case from its row menu on the Casos tab", async () => {
    const user = userEvent.setup();
    vi.mocked(postJson).mockResolvedValue({ ok: true });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Casos" }));
    await user.click(archivedRowMenu(1));
    await user.click(await screen.findByRole("menuitem", { name: "Editar caso" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("#1 · Gasfitería")).toBeInTheDocument();
    await user.selectOptions(within(dialog).getByLabelText("Estado"), "cerrado");
    await user.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));

    expect(postJson).toHaveBeenCalledWith("/panel/api/cases/1/update", { status: "cerrado", responsible_id: null });
  });

  it("defines the amount of an archived case from its row menu on the Casos tab", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCaseAmount).mockResolvedValue({ ok: true, case: { ...ficha.history.cases[1], amount: 90000, customer: ficha.customer } });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Casos" }));
    await user.click(archivedRowMenu(1));
    await user.click(await screen.findByRole("menuitem", { name: "Definir monto" }));

    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Monto del servicio"), "90000");
    await user.click(within(dialog).getByRole("button", { name: "Guardar monto" }));

    expect(updateCaseAmount).toHaveBeenCalledWith(1, 90000);
  });

  it("renders an archived case with a null priority without crashing", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const withoutPriority: ClientFichaResponse = {
      ...ficha,
      history: { ...ficha.history, cases: ficha.history.cases.map((row) => row.id === 1 ? { ...row, priority: null as unknown as string } : row) },
    };
    render(<ClientFicha customerId={7} data={withoutPriority} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Casos" }));

    const archive = screen.getByRole("region", { name: "Casos anteriores" });
    expect(within(archive).getByText("—")).toBeInTheDocument();
  });

  it("shows local feedback when a case update fails", async () => {
    const user = userEvent.setup();
    vi.mocked(postJson).mockRejectedValue(new ApiError(500, "private error"));
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await clickCaseMenuItem(user, "Editar caso");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findAllByRole("heading", { name: "No pudimos guardar el caso" })).toHaveLength(1);
  });

  it("posts state changes and notes, then refreshes ficha and memories", async () => {
    const user = userEvent.setup();
    vi.mocked(changeClientState).mockResolvedValue({ ok: true, state: "pendiente" });
    vi.mocked(addClientNote).mockResolvedValue({ ok: true, note: ficha.notes[0] });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Cambiar estado");
    await user.click(screen.getByRole("radio", { name: "Pendiente" }));
    await user.click(screen.getByRole("button", { name: "Guardar estado" }));
    await user.click(screen.getByRole("button", { name: "⊕ Agregar nota" }));
    const noteDialog = screen.getByRole("dialog", { name: "Agregar nota" });
    await user.type(within(noteDialog).getByLabelText("Nota"), "Llamar mañana");
    await user.click(within(noteDialog).getByRole("button", { name: "Guardar nota" }));

    expect(changeClientState).toHaveBeenCalledWith(7, "pendiente");
    expect(addClientNote).toHaveBeenCalledWith(7, "Llamar mañana");
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10");
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7/memories");
    expect(await screen.findByRole("heading", { name: "Nota agregada" })).toBeInTheDocument();
  });

  it("edits a customer note and refreshes the ficha", async () => {
    const user = userEvent.setup();
    vi.mocked(updateClientNote).mockResolvedValue({ ok: true, note: { ...ficha.notes[0], note: "Nueva nota" } });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: "Acciones de nota" }));
    await user.click(await screen.findByRole("menuitem", { name: "Editar" }));
    const dialog = screen.getByRole("dialog", { name: "Editar nota" });
    await user.clear(within(dialog).getByLabelText("Nota"));
    await user.type(within(dialog).getByLabelText("Nota"), "Nueva nota");
    await user.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));

    expect(updateClientNote).toHaveBeenCalledWith(7, 4, "Nueva nota");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10"));
  });

  it("confirms deletion of a customer note", async () => {
    const user = userEvent.setup();
    vi.mocked(deleteClientNote).mockResolvedValue({ ok: true });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: "Acciones de nota" }));
    await user.click(await screen.findByRole("menuitem", { name: "Eliminar" }));
    const dialog = screen.getByRole("dialog", { name: "Eliminar nota" });
    expect(within(dialog).getByText("Esta acción no se puede deshacer.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Eliminar nota" }));

    expect(deleteClientNote).toHaveBeenCalledWith(7, 4);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/7?messages_limit=10"));
  });

  it("renders the ficha allowed transitions as selectable radio cards and hides save for terminal states", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Cambiar estado");
    const group = screen.getByRole("radiogroup", { name: "Nuevo estado" });
    expect(within(group).getAllByRole("radio")).toHaveLength(2);
    expect(within(group).getByRole("radio", { name: "Pendiente" })).toHaveAttribute("aria-checked", "true");
    await user.click(within(group).getByRole("radio", { name: "Agendado" }));
    expect(within(group).getByRole("radio", { name: "Agendado" })).toHaveAttribute("aria-checked", "true");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }));

    rerender(<ClientFicha customerId={7} data={{ ...ficha, customer: { ...ficha.customer, state: "cancelado", allowed_transitions: [] } }} memories={memories} />);
    await clickCustomerMenuItem(user, "Cambiar estado");
    const terminalDialog = screen.getByRole("dialog");
    expect(within(terminalDialog).queryByRole("radio")).not.toBeInTheDocument();
    expect(within(terminalDialog).queryByRole("button", { name: "Guardar estado" })).not.toBeInTheDocument();
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

    await clickCustomerMenuItem(user, "Cambiar estado");
    await user.click(screen.getByRole("radio", { name: "Pendiente" }));
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

    await user.click(screen.getByRole("button", { name: "⊕ Agregar nota" }));
    await user.click(within(screen.getByRole("dialog", { name: "Agregar nota" })).getByRole("button", { name: "Guardar nota" }));

    expect(addClientNote).not.toHaveBeenCalled();
    expect(screen.getByText("La nota no puede estar vacía")).toBeInTheDocument();
  });
});

describe("ClientFicha customer controls", () => {
  beforeEach(() => vi.clearAllMocks());

  it("groups the customer summary into one card with one primary action and a named actions menu", async () => {
    const user = userEvent.setup();
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    const rail = screen.getByRole("region", { name: "Resumen del cliente" });
    expect(rail.querySelectorAll(":scope > .card")).toHaveLength(1);
    expect(within(rail).getByRole("heading", { name: "Datos del cliente" })).toBeInTheDocument();
    expect(within(rail).queryByRole("heading", { name: "Identidad" })).not.toBeInTheDocument();
    expect(within(rail).queryByRole("heading", { name: "Estado" })).not.toBeInTheDocument();
    expect(within(rail).getByText("Teléfono", { selector: "dt" })).toBeInTheDocument();
    expect(within(rail).getByText("+56912345678", { selector: "dd" })).toBeInTheDocument();
    expect(within(rail).getAllByText("Contactado", { selector: ".badge" }).length).toBeGreaterThan(0);

    const actions = rail.querySelector(".client-ficha__customer-controls") as HTMLElement;
    expect(within(actions).queryByRole("button", { name: "Editar identidad" })).not.toBeInTheDocument();
    expect(actions.querySelectorAll(".menu__trigger--icon")).toHaveLength(1);
    expect(within(actions).getByRole("button", { name: "Acciones para Marcela Fuentes" })).toBeInTheDocument();
    expect(within(actions).getAllByRole("button").every((button) => !button.textContent?.includes("Marcela Fuentes"))).toBe(true);

    await user.click(within(actions).getByRole("button", { name: "Acciones para Marcela Fuentes" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: "Editar" })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: "Cambiar consentimiento" })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: "Fusionar con otro cliente" })).toHaveClass("menu__item--danger");
    expect(within(menu).getByRole("menuitem", { name: "Archivar" })).toHaveClass("menu__item--danger");
  });

  it("edits profile fields in a dialog without allowing phone changes", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCustomerProfile).mockResolvedValue({ customer: ficha.customer });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Editar");
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Teléfono *")).toHaveAttribute("readonly");
    await user.clear(within(dialog).getByLabelText("Nombre"));
    await user.type(within(dialog).getByLabelText("Nombre"), "Marcela Rojas");
    await user.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));

    expect(updateCustomerProfile).toHaveBeenCalledWith(7, { name: "Marcela Rojas" });
    expect(await screen.findByRole("heading", { name: "Identidad guardada" })).toBeInTheDocument();
  });

  it("shows a local message rather than silently dropping a blank changed field", async () => {
    const user = userEvent.setup();
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await clickCustomerMenuItem(user, "Editar");
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Nombre"));
    await user.click(within(dialog).getByRole("button", { name: "Guardar cambios" }));
    expect(updateCustomerProfile).not.toHaveBeenCalled();
    expect(within(dialog).getByRole("alert")).toHaveTextContent("No puedes dejar vacío un campo editado");
  });

  it("opens the consent dialog, saves the chosen value, and surfaces failures in the dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(updateCustomerConsent).mockRejectedValue(new ApiError(500, "private"));
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await clickCustomerMenuItem(user, "Cambiar consentimiento");
    const dialog = screen.getByRole("dialog");
    expect(updateCustomerConsent).not.toHaveBeenCalled();
    const group = within(dialog).getByRole("radiogroup", { name: "Nuevo consentimiento" });
    expect(within(group).getByRole("radio", { name: /Sí El cliente acepta/ })).toHaveAttribute("aria-checked", "true");
    await user.click(within(group).getByRole("radio", { name: /No El cliente prefiere/ }));
    expect(within(group).getByRole("radio", { name: /No El cliente prefiere/ })).toHaveAttribute("aria-checked", "true");
    await user.click(within(dialog).getByRole("button", { name: "Guardar consentimiento" }));
    expect(updateCustomerConsent).toHaveBeenCalledWith(7, false);
    expect(await within(dialog).findByRole("heading", { name: "No pudimos guardar el consentimiento" })).toBeInTheDocument();
  });

  it("warns with loaded open-case and future-appointment counts before archiving", async () => {
    const user = userEvent.setup();
    const futureStart = new Date(Date.now() + 86_400_000).toISOString();
    const futureAppointment = { id: 44, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: futureStart, timezone: "UTC", starts_at: futureStart, ends_at: futureStart, duration_minutes: 60, status: "booked" };
    vi.mocked(archiveCustomer).mockResolvedValue({ customer: ficha.customer });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={{ ...ficha, history: { ...ficha.history, appointments: [futureAppointment] } }} memories={memories} />);
    await clickCustomerMenuItem(user, "Archivar");
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("caso abierto")).toBeInTheDocument();
    expect(within(dialog).getByText("visita futura")).toBeInTheDocument();
    expect(within(dialog).getByText("Información del cliente")).toBeInTheDocument();
    expect(within(dialog).getByText("Estos trabajos seguirán registrados.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Archivar cliente" })).toHaveClass("btn--danger");
    await user.click(within(dialog).getByRole("button", { name: "Archivar cliente" }));
    expect(archiveCustomer).toHaveBeenCalledWith(7);
    expect(await screen.findByRole("heading", { name: "Cliente archivado" })).toBeInTheDocument();
  });

  it("shows an archive failure once, with a readable label", async () => {
    const user = userEvent.setup();
    vi.mocked(archiveCustomer).mockRejectedValue(new ApiError(500, "private"));
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);
    await clickCustomerMenuItem(user, "Archivar");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Archivar cliente" }));
    expect(await screen.findAllByRole("heading", { name: "No pudimos guardar el archivo" })).toHaveLength(1);
  });

  it("shows archived state and offers restore with visible failure feedback", async () => {
    const user = userEvent.setup();
    vi.mocked(unarchiveCustomer).mockRejectedValue(new ApiError(500, "private"));
    render(<ClientFicha customerId={7} data={{ ...ficha, customer: { ...ficha.customer, archived_at: "2026-09-01T00:00:00Z" } }} memories={memories} />);
    expect(screen.getByText("Cliente archivado")).toBeInTheDocument();
    await clickCustomerMenuItem(user, "Restaurar");
    expect(unarchiveCustomer).toHaveBeenCalledWith(7);
    expect(await screen.findByRole("heading", { name: "No pudimos guardar el archivo" })).toBeInTheDocument();
  });
});

describe("ClientFicha merge dialog", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads the selected pair preview and confirms the merge", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ ...ficha.customer, id: 8, name: "José Soto", phone_e164: "+56987654321" }] });
    vi.mocked(previewClientMerge).mockResolvedValue({ survivor_id: 7, loser_id: 8, moved: { conversations: 2, cases: 1, customer_notes: 3, customer_equipment: 1, appointments: 0 }, memory_conflicts: 2, scalar_conflicts: ["name"] });
    vi.mocked(mergeClient).mockResolvedValue({ survivor: ficha.customer, moved: { conversations: 2, cases: 1, customer_notes: 3, customer_equipment: 1, appointments: 0 } });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Fusionar con otro cliente");
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Otro cliente"), "8");
    expect(within(dialog).getByText("Revisa las fichas antes de confirmar.")).toBeInTheDocument();
    expect(within(dialog).getByText(/Vista previa: se moverán/)).toHaveTextContent("conversaciones: 2 · casos: 1 · notas: 3 · equipos: 1 · visitas: 0");
    expect(within(dialog).getByText(/2 conflictos de memoria/)).toBeInTheDocument();
    expect(within(dialog).getByText(/se conservan los datos del cliente superviviente en name/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Confirmar fusión" })).toHaveClass("btn--danger");
    await user.click(within(dialog).getByRole("button", { name: "Confirmar fusión" }));

    expect(previewClientMerge).toHaveBeenCalledWith(7, 8);
    expect(mergeClient).toHaveBeenCalledWith(7, 8);
  });

  it("reloads equipment after a survivor-side merge", async () => {
    const user = userEvent.setup();
    vi.mocked(listClientEquipment).mockResolvedValue({ equipment: [] });
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ ...ficha.customer, id: 8 }] });
    vi.mocked(previewClientMerge).mockResolvedValue({ survivor_id: 7, loser_id: 8, moved: { conversations: 0, cases: 0, customer_notes: 0, customer_equipment: 1, appointments: 0 }, memory_conflicts: 0, scalar_conflicts: [] });
    vi.mocked(mergeClient).mockResolvedValue({ survivor: ficha.customer, moved: { conversations: 0, cases: 0, customer_notes: 0, customer_equipment: 1, appointments: 0 } });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await waitFor(() => expect(listClientEquipment).toHaveBeenCalledTimes(1));
    await clickCustomerMenuItem(user, "Fusionar con otro cliente");
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Otro cliente"), "8");
    await user.click(await within(dialog).findByRole("button", { name: "Confirmar fusión" }));

    await waitFor(() => expect(listClientEquipment).toHaveBeenCalledTimes(2));
  });

  it("loads the survivor ficha when the current client becomes the loser", async () => {
    const user = userEvent.setup();
    const survivor = { ...ficha.customer, id: 8, name: "José Soto" };
    vi.mocked(fetchClients).mockResolvedValue({ clients: [survivor] });
    vi.mocked(previewClientMerge).mockResolvedValue({ survivor_id: 8, loser_id: 7, moved: { conversations: 0, cases: 0, customer_notes: 0, customer_equipment: 0, appointments: 0 }, memory_conflicts: 0, scalar_conflicts: [] });
    vi.mocked(mergeClient).mockResolvedValue({ survivor, moved: { conversations: 0, cases: 0, customer_notes: 0, customer_equipment: 0, appointments: 0 } });
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path.endsWith("/memories")) return { memories };
      if (path.endsWith("/pending")) return { relations: [] };
      return { ...ficha, customer: survivor };
    });
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Fusionar con otro cliente");
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Otro cliente"), "8");
    await user.click(await within(dialog).findByRole("button", { name: "Confirmar fusión" }));

    expect(await screen.findByRole("heading", { level: 1, name: "José Soto" })).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/clients/8?messages_limit=10");
  });

  it("surfaces the backend guard detail in the merge dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ ...ficha.customer, id: 8 }] });
    vi.mocked(previewClientMerge).mockRejectedValue(new ApiError(400, "cannot merge a customer tombstone"));
    render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Fusionar con otro cliente");
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Otro cliente"), "8");

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("cannot merge a customer tombstone");
    expect(within(dialog).getByRole("button", { name: "Confirmar fusión" })).toBeDisabled();
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
    expect(container.querySelectorAll("button:not(.btn):not(.dialog__close):not(.menu__trigger):not(.tabs__tab):not(.client-ficha__history-entry)")).toHaveLength(0);
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
    expect(within(summary).getByText("+56912345678", { selector: "dd" })).toBeInTheDocument();
    expect(within(summary).getByText("Dirección", { selector: "dt" })).toBeInTheDocument();
    expect(within(summary).getByText("Dirección", { selector: "dt" }).parentElement).toHaveTextContent(/Av\. Italia 123\s*Ñuñoa/);
    expect(within(summary).getByText("Consentimiento", { selector: "dt" })).toBeInTheDocument();
  });

  // T13 — feedback at the locus of the action.
  it("shows save feedback beside the control that caused it, not in the page banner", async () => {
    const user = userEvent.setup();
    vi.mocked(changeClientState).mockResolvedValue({ ok: true, state: "pendiente" });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const { container } = render(<ClientFicha customerId={7} data={ficha} memories={memories} />);

    await clickCustomerMenuItem(user, "Cambiar estado");
    await user.click(screen.getByRole("radio", { name: "Pendiente" }));
    await user.click(screen.getByRole("button", { name: "Guardar estado" }));

    expect(container.querySelector(".client-ficha__state-control")).toBeNull();
    expect(await screen.findAllByText("Estado guardado")).not.toHaveLength(0);
    // The page banner must not carry action feedback.
    expect(container.querySelector(".page-frame__banner")?.textContent ?? "").not.toContain("Estado guardado");
  });

  // T14 — history decomposed into named regions with Chilean-locale dates.
  it("moves existing history content into its matching tabs", async () => {
    const user = userEvent.setup();
    render(<ClientFicha data={ficha} memories={memories} />);
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Resumen", "Casos", "Visitas", "Conversaciones"]);
    await user.click(screen.getByRole("tab", { name: "Casos" }));
    expect(screen.getByRole("heading", { name: "Casos anteriores" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Datos del cliente" })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Visitas" }));
    expect(screen.getByRole("heading", { name: "Próximas visitas" })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Conversaciones" }));
    expect(screen.getByRole("heading", { name: /Mensajes de la conversación/ })).toBeInTheDocument();
  });

  it("opens one combined history dialog from the summary history entry", async () => {
    const user = userEvent.setup();
    render(<ClientFicha data={ficha} memories={memories} />);

    await user.click(screen.getByRole("button", { name: /Historial del cliente/ }));
    const dialog = screen.getByRole("dialog", { name: "Historial del cliente" });
    expect(within(dialog).getByRole("heading", { name: "Casos anteriores" })).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { name: "Visitas" })).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { name: "Conversaciones" })).toBeInTheDocument();
    expect(within(dialog).getByText("Gasfitería")).toBeInTheDocument();
    expect(within(dialog).getByText("Coordinar visita")).toBeInTheDocument();
  });

  it("formats history dates in the Chilean locale instead of slicing the ISO string", () => {
    render(<ClientFicha data={ficha} memories={memories} />);

    // The raw ISO slice is gone; what remains is the `es-CL` day-month-year shape (e.g. "11 sep 2026").
    expect(screen.queryByText("2026-07-15")).not.toBeInTheDocument();
    expect(screen.getAllByText(/\d{1,2} [a-z]{3} \d{4}/i).length).toBeGreaterThan(0);
  });

  it("links each visit to its appointment detail and keeps calendar retry outside the link", async () => {
    const user = userEvent.setup();
    const visit = { id: 42, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: "2026-07-15T12:00:00Z", timezone: "UTC", starts_at: "2026-07-15T12:00:00Z", ends_at: "2026-07-15T13:00:00Z", duration_minutes: 60, status: "booked", calendar_error: "Proveedor no disponible" };
    render(<ClientFicha data={{ ...ficha, history: { ...ficha.history, appointments: [visit] } }} memories={memories} onRetryCalendar={vi.fn()} />);

    await user.click(screen.getByRole("tab", { name: "Visitas" }));
    const link = desktopOnly(screen.getAllByRole("link", { name: /Reparación/ }))[0];
    expect(link).toHaveAttribute("href", "/panel/app/agenda/42");
    const retry = screen.getByRole("button", { name: "Reintentar calendario" });
    expect(retry.closest("a")).toBeNull();
    await user.click(retry);
    expect(apiFetch).toHaveBeenCalledWith("/panel/api/appointments/42/calendar/sync", { method: "POST" });
  });

  it("moves the reschedule action into the visit row menu", async () => {
    const user = userEvent.setup();
    const visit = { id: 42, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: "2099-07-15T12:00:00Z", timezone: "UTC", starts_at: "2099-07-15T12:00:00Z", ends_at: "2099-07-15T13:00:00Z", duration_minutes: 60, status: "booked" };
    render(<ClientFicha data={{ ...ficha, history: { ...ficha.history, appointments: [visit] } }} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Visitas" }));
    expect(screen.queryByRole("button", { name: "Reprogramar" })).not.toBeInTheDocument();
    await user.click(desktopOnly(screen.getAllByRole("button", { name: "Acciones de la visita #42" }))[0]);
    expect(await screen.findByRole("menuitem", { name: "Reprogramar" })).toBeInTheDocument();
  });

  it("cancels an upcoming visit from the row menu with a reason", async () => {
    const user = userEvent.setup();
    vi.mocked(cancelAppointment).mockResolvedValue({ ok: true, appointment: {} });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const visit = { id: 42, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: "2099-07-15T12:00:00Z", timezone: "UTC", starts_at: "2099-07-15T12:00:00Z", ends_at: "2099-07-15T13:00:00Z", duration_minutes: 60, status: "booked" };
    render(<ClientFicha customerId={7} data={{ ...ficha, history: { ...ficha.history, appointments: [visit] } }} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Visitas" }));
    await user.click(desktopOnly(screen.getAllByRole("button", { name: "Acciones de la visita #42" }))[0]);
    await user.click(await screen.findByRole("menuitem", { name: "Cancelar visita" }));
    const dialog = screen.getByRole("dialog", { name: "Cancelar visita" });
    await user.type(within(dialog).getByLabelText("Motivo de cancelación"), "Cliente avisó");
    await user.click(within(dialog).getByRole("button", { name: "Confirmar cancelación" }));

    expect(cancelAppointment).toHaveBeenCalledWith(42, "Cliente avisó");
  });

  it("closes an upcoming visit as a no-show from the row menu", async () => {
    const user = userEvent.setup();
    vi.mocked(closeAppointment).mockResolvedValue({ ok: true, appointment: {} });
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    const visit = { id: 43, service: "Reparación", customer_id: 7, case_id: 2, technician_id: 3, local_start: "2099-07-15T12:00:00Z", timezone: "UTC", starts_at: "2099-07-15T12:00:00Z", ends_at: "2099-07-15T13:00:00Z", duration_minutes: 60, status: "booked" };
    render(<ClientFicha customerId={7} data={{ ...ficha, history: { ...ficha.history, appointments: [visit] } }} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Visitas" }));
    await user.click(desktopOnly(screen.getAllByRole("button", { name: "Acciones de la visita #43" }))[0]);
    await user.click(await screen.findByRole("menuitem", { name: "Cerrar visita" }));
    const dialog = screen.getByRole("dialog", { name: "Cerrar visita" });
    await user.click(within(dialog).getByRole("radio", { name: /No completada/ }));
    await user.click(within(dialog).getByRole("button", { name: "Confirmar cierre" }));

    expect(closeAppointment).toHaveBeenCalledWith(43, "no_show");
  });

  // T15 — the layout decision: two regions with a summary rail.
  it("composes the ficha into tabbed content, with no conversation component", () => {
    const { container } = render(<ClientFicha data={ficha} memories={memories} />);

    expect(container.querySelector(".detail-region__rail")).not.toBeNull();
    expect(container.querySelector(".detail-region__main")).not.toBeNull();
    expect(container.querySelector(".ai-agent-grammar__bubble, .assistant-chat__conversation")).toBeNull();
  });

  // New requirement from the owner's review: the ficha had no way back.
  it("keeps history messages reachable from the conversations tab", async () => {
    const user = userEvent.setup();
    render(<ClientFicha data={ficha} memories={memories} />);
    await user.click(screen.getByRole("tab", { name: "Conversaciones" }));
    expect(screen.getByRole("link", { name: "#1" })).toHaveAttribute("href", "/panel/app/conversations/1");
  });

  it("links each message to its conversation and never offers inline expansion", async () => {
    const user = userEvent.setup();
    render(<ClientFicha data={ficha} memories={memories} />);
    await user.click(screen.getByRole("tab", { name: "Conversaciones" }));
    expect(screen.getByRole("link", { name: "#1" })).toHaveAttribute("href", "/panel/app/conversations/1");
    expect(screen.queryByRole("button", { name: /Ver todos/ })).not.toBeInTheDocument();
  });

  it("loads only the last ten messages of the selected conversation", async () => {
    const user = userEvent.setup();
    const allMessages = Array.from({ length: 12 }, (_, index) => ({
      ...ficha.history.messages[0], id: index + 1, text: `Mensaje ${index + 1}`,
    }));
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : ficha);
    vi.mocked(getConversation).mockResolvedValue({ conversation: ficha.history.conversations[0], messages: allMessages.slice(-10), messages_total: allMessages.length } as unknown as ConversationThread);

    render(<ClientFicha customerId={7} memories={memories} />);
    await user.click(await screen.findByRole("tab", { name: "Conversaciones" }));
    expect(getConversation).toHaveBeenCalledWith(1, 10);
    expect(screen.getAllByText("Mensaje 3").length).toBeGreaterThan(0);
    expect(screen.queryByText("Mensaje 2")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ver todos/ })).not.toBeInTheDocument();
  });

  it("lets the owner pick the conversation when there is more than one", async () => {
    const user = userEvent.setup();
    const earlierConversation = { ...ficha.history.conversations[0], id: 2, state: "closed", summary: "Consulta anterior" };
    const earlierMessages = [{ ...ficha.history.messages[0], id: 9, conversation_id: 2, text: "Hola de nuevo" }];
    vi.mocked(apiFetch).mockImplementation(async (path) => path.endsWith("/memories") ? { memories } : path.endsWith("/pending") ? { relations: [] } : { ...ficha, history: { ...ficha.history, conversations: [earlierConversation, ficha.history.conversations[0]] } });
    vi.mocked(getConversation).mockImplementation(async (id) => id === 2
      ? ({ conversation: earlierConversation, messages: earlierMessages, messages_total: 1 } as unknown as ConversationThread)
      : ({ conversation: ficha.history.conversations[0], messages: ficha.history.messages, messages_total: 1 } as unknown as ConversationThread));

    render(<ClientFicha customerId={7} memories={memories} />);
    await user.click(await screen.findByRole("tab", { name: "Conversaciones" }));
    expect((await screen.findAllByText("Necesito ayuda")).length).toBeGreaterThan(0);

    await user.selectOptions(screen.getByLabelText("Conversación"), "2");
    expect((await screen.findAllByText("Hola de nuevo")).length).toBeGreaterThan(0);
    expect(getConversation).toHaveBeenCalledWith(2, 10);
  });

  it("hides the disclosure control when ten or fewer messages exist", () => {
    render(<ClientFicha data={{ ...ficha, history: { ...ficha.history, messages_total: 10 } }} memories={memories} />);

    expect(screen.queryByRole("button", { name: /Ver todos/ })).not.toBeInTheDocument();
  });

  it("renders the conversations and messages tables with the reference labels and chips", async () => {
    const user = userEvent.setup();
    render(<ClientFicha data={ficha} memories={memories} />);

    await user.click(screen.getByRole("tab", { name: "Conversaciones" }));

    expect(screen.getAllByRole("columnheader", { name: "Conversación" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("columnheader", { name: "Turno" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mensajes de la conversación #1" })).toBeInTheDocument();
    expect(screen.getAllByText("Entrante").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Texto").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Turno 1 · Texto").length).toBeGreaterThan(0);
    expect(screen.getByText("Mostrando 1 mensaje")).toBeInTheDocument();
  });
});
