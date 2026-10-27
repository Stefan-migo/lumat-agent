import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Settings as SettingsData } from "../../types";
import { Settings } from "./Settings";
import { WEEKDAY_NAMES } from "../shared/agendaTime";

const replyTextValues = {
  handoff_cobertura: "Sin cobertura en {{comuna}}.",
  handoff_persona: "Te paso con una persona del equipo.",
  handoff_unknown_intent_thrice: "Te dejo con una persona del equipo.",
  handoff_campo_sin_respuesta: "Un asesor te contacta para coordinar.",
  handoff_booking_unavailable: "No hay horarios: un asesor te contacta.",
  booking_offer: "Horarios: {{opciones}}",
  booking_no_more_today: "Sin más horarios para hoy: {{opciones}}",
  booking_unclear: "No entendí el horario.",
  booking_confirmed: "Visita agendada.",
  manage_no_visits: "No tienes visitas.",
  manage_confirm_cancel: "¿Confirmas cancelar?",
  manage_select: "Elige una visita.",
  manage_slots_offer: "Nuevos horarios: {{opciones}}",
  manage_expired: "La visita ya pasó.",
  manage_appointment_unclear: "No entendí qué visita.",
  manage_slots_unclear: "No entendí el horario.",
  manage_kept: "Quedó igual.",
  manage_reschedule_unavailable: "No hay horarios para reagendar.",
  manage_rescheduled: "Visita reagendada.",
  manage_cancel_prompt: "¿Quieres cancelar?",
  manage_cancel_unavailable: "No se puede cancelar.",
  manage_cancelled: "Visita cancelada.",
  handoff: "Te paso con un asesor.",
  capture_evidence: "¿Puedes enviar evidencia?",
  capture_consent: "¿Autorizas el tratamiento de tus datos?",
};
type SettingsWithOptions = SettingsData & { options: { tones: string[]; tarifa_labels: Record<string, string> } };
const settings = (overrides: Partial<SettingsWithOptions> = {}): SettingsWithOptions => ({
  model_api_key: { configured: false, source: "none", masked: "" },
  email: { host: "localhost", port: 25, from_address: "notificaciones@lumat.cl", user: "", tls: "none", password: { configured: false, masked: "" } },
  scope_rules: { general: "bot_resolve" }, keywords: ["gas"], tone: "cercano",
  options: { tones: ["cercano", "formal", "directo"], tarifa_labels: { visita_tecnica: "Visita técnica", mantencion_calefont: "Mantención de calefont", mantencion_caldera: "Mantención de caldera", lavado_red: "Lavado de red" } },
  messages: { greeting: "Hola", greeting_short: "Hola, ¿qué necesitas?", greeting_name: "Hola, Ana", greeting_short_name: "Hola, Ana", smalltalk: "Con gusto.", cannot_answer: "No sé", clarification: "¿Cuál?", cannot_understand_offer: "¿Visita o persona?", kb_miss_offer: "No tengo ese dato.", farewell: "Chao", out_of_hours: "Cerrado" },
  templates: [],
  hours: { timezone: "America/Santiago", schedule: [{ days: [1], open: "09:00", close: "18:00" }] },
  tarifa: { visita_tecnica: [{ desde_mes: 1, hasta_mes: 12, valor: 30000 }], mantencion_calefont: [{ desde_mes: 1, hasta_mes: 12, valor: 50000 }], mantencion_caldera: [{ desde_mes: 1, hasta_mes: 12, valor: 80000 }], lavado_red: [{ desde_mes: 1, hasta_mes: 12, valor: 140000 }] },
  coverage: ["Las Condes"], service_durations: {},
  conversation_limit: 4, daily_limit: 20, meta_cost: 0.05, booking: { lead_hours: 2 },
  persona: { orchestrator: "Eres Max.", orchestrator_brief: "Sé breve.", customized: false },
  emergency: { safety_instructions: ["Corta el gas."], contacts: ["Bomberos 132."], notify_message: "Notificado.", customized: false },
  conduct: {
    orden: ["failure", "comuna", "name"],
    redaccion: "plantilla",
    max_preguntas_por_mensaje: 1,
    derivaciones: ["cobertura"],
    customized: false,
    options: {
      redaccion: ["llm", "plantilla"],
      fields: [
        { value: "failure", label: "Problema" },
        { value: "equipment", label: "Equipo" },
        { value: "comuna", label: "Comuna" },
        { value: "availability", label: "Disponibilidad" },
        { value: "name", label: "Nombre" },
        { value: "email", label: "Correo" },
        { value: "address", label: "Dirección" },
      ],
      max_preguntas_por_mensaje: [1, 2],
      derivaciones: ["cobertura"],
    },
  },
  capture_questions: { questions: { failure: "¿Qué pasa con el equipo?", comuna: "¿En qué comuna estás?", name: "¿Cuál es tu nombre?" }, customized: false },
  reply_texts: { texts: { ...replyTextValues }, slots: { booking_offer: ["opciones"], handoff_cobertura: ["comuna"] }, customized: false },
  snapshot: { date: "2026-10-08", conversation_spend: 1, conversation_limit: 4, conversation_percent: 25, daily_spend: 2, daily_limit: 20, daily_percent: 10, mode: "normal" },
  ...overrides,
});
const capabilities = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };
const groupForSection: Record<string, string> = {
  Agente: "Chatbot", Persona: "Chatbot", Conducta: "Chatbot", Mensajes: "Chatbot",
  "Horarios y avisos": "Operación", Cobertura: "Operación", Tarifas: "Operación",
  Capacidades: "Integraciones", "API key de modelos": "Integraciones", Correo: "Integraciones", Costos: "Costos",
};
async function selectSection(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(within(screen.getByRole("tablist", { name: "Super-secciones de configuración" })).getByRole("tab", { name: groupForSection[label] }));
  await user.click(within(screen.getByRole("tablist", { name: "Secciones de configuración" })).getByRole("tab", { name: label }));
}

describe("Settings", () => {
  it("operation uses the shared save bar for hours and durations with an explicit empty state", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ technicians: [] }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");
    const durations = screen.getByRole("heading", { name: "Duraciones por servicio" }).closest(".card") as HTMLElement;
    expect(within(durations).getByText("Aún no hay duraciones configuradas")).toBeInTheDocument();
    expect(within(durations.querySelector(".card__header")!).getByRole("button", { name: "Agregar servicio" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar anticipación" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar horarios" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar duraciones" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Configurar notificaciones/ })).toHaveAttribute("href", "/panel/app/push");
    expect(screen.getByRole("button", { name: /Editar en Mensajes/ })).toBeInTheDocument();
    await user.click(within(durations).getByRole("button", { name: "Agregar servicio" }));
    fireEvent.change(screen.getByLabelText("Servicio 1"), { target: { value: " Calefont " } });
    fireEvent.change(screen.getByLabelText("Minutos 1"), { target: { value: "90" } });
    fireEvent.change(screen.getByLabelText("Anticipación mínima"), { target: { value: "0" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    expect(screen.getByLabelText("Anticipación mínima")).toHaveValue(0);
    expect(screen.getByLabelText("Servicio 1")).toHaveValue(" Calefont ");
    await user.click(screen.getByRole("button", { name: "Descartar" }));
    expect(screen.getByLabelText("Anticipación mínima")).toHaveValue(2);
    expect(screen.queryByLabelText("Servicio 1")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
  });

  it("operation adapts coverage help and keeps empty rejection and exact normalized payload", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Cobertura");
    expect(screen.getByRole("button", { name: "Ayuda sobre cobertura" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar cobertura" })).not.toBeInTheDocument();
    const field = screen.getByLabelText("Comunas con cobertura");
    fireEvent.change(field, { target: { value: " \n " } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    expect(field).toHaveValue(" \n ");
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeEnabled();
    fireEvent.change(field, { target: { value: " Ñuñoa \n\n Las Condes " } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/coverage", expect.objectContaining({
      method: "POST", body: JSON.stringify({ communes: ["Ñuñoa", "Las Condes"] }),
    })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled());
  });

  it("operation adapts tariff help while preserving season fields, validation and save payload", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200 }));
    const data = settings();
    render(<Settings data={data} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Tarifas");
    expect(screen.getByRole("button", { name: "Ayuda sobre tarifas" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar tarifas" })).not.toBeInTheDocument();
    const field = screen.getByLabelText(/Visita técnica/);
    fireEvent.change(field, { target: { value: "0" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    expect(field).toHaveValue(null);
    fireEvent.change(field, { target: { value: "35000" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/tarifa", expect.objectContaining({
      method: "POST", body: JSON.stringify({ precios: { ...data.tarifa, visita_tecnica: [{ desde_mes: 1, hasta_mes: 12, valor: 35000 }] } }),
    })));
  });

  it("operation keeps unsaved coverage and tariff drafts isolated and discards only the active section", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Cobertura");
    fireEvent.change(screen.getByLabelText("Comunas con cobertura"), { target: { value: "Ñuñoa" } });
    await selectSection(user, "Tarifas");
    fireEvent.change(screen.getByLabelText(/Visita técnica/), { target: { value: "35000" } });
    await user.click(screen.getByRole("button", { name: "Descartar" }));
    expect(screen.getByLabelText(/Visita técnica/)).toHaveValue(30000);
    await selectSection(user, "Cobertura");
    expect(screen.getByLabelText("Comunas con cobertura")).toHaveValue("Ñuñoa");
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeEnabled();
    expect(fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  });
  it("uses contextual decorative icons for all five derivation cases", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    const nav = screen.getByRole("navigation", { name: "Situaciones de respuesta" });
    for (const [label, icon] of [
      ["Comuna sin cobertura", "map-pin-off"], ["Pide hablar con una persona", "headset"],
      ["Tres mensajes sin entender", "message-circle-question-mark"],
      ["Un dato no se logró tomar", "clipboard-x"], ["No hay horarios para agendar", "calendar-x"],
    ]) {
      const button = within(nav).getByRole("button", { name: label });
      expect(button.querySelector("svg")).toHaveClass(`lucide-${icon}`);
      expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
      await user.click(button);
      expect(button).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByRole("heading", { name: label })).toBeInTheDocument();
    }
  });

  it("shows a contextual icon on each option inside all four reply accordions", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    const nav = screen.getByRole("navigation", { name: "Situaciones de respuesta" });
    const groups = [
      { title: "Agendar", entries: [
        ["Oferta de horarios", "calendar-days"], ["Sin más horarios para ese día", "calendar-x"],
        ["No se entendió el horario pedido", "circle-help"], ["Visita agendada", "calendar-check"],
      ] },
      { title: "Gestionar una visita", entries: [
        ["No tiene visitas", "calendar-x"], ["Confirmar la cancelación", "circle-help"],
        ["Elegir una visita", "list-checks"], ["Ofrecer nuevos horarios", "calendar-days"],
        ["La visita ya pasó", "history"], ["No se entendió la visita", "calendar-search"],
        ["No se entendió el horario", "circle-help"], ["La visita sigue igual", "calendar-check"],
        ["Sin horarios para reagendar", "calendar-x"], ["Visita reagendada", "calendar-clock"],
        ["Pedir confirmación para cancelar", "circle-help"], ["No se puede cancelar", "ban"],
        ["Visita cancelada", "calendar-x"],
      ] },
      { title: "Derivar a una persona", entries: [["Derivación a un asesor", "headset"]] },
      { title: "Captura", entries: [["Pedir evidencia", "camera"], ["Pedir consentimiento", "shield-check"]] },
    ];
    for (const { title, entries } of groups) {
      await user.click(within(nav).getByRole("button", { name: new RegExp(title) }));
      for (const [label, icon] of entries) {
        const button = within(nav).getByRole("button", { name: label });
        expect(button.querySelector("svg")).toHaveClass(`lucide-${icon}`);
        expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
      }
    }
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
  });

  it("groups specific derivation cases in a collapsible list separate from generic handoff", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    const nav = screen.getByRole("navigation", { name: "Situaciones de respuesta" });
    const cases = within(nav).getByRole("button", { name: /Casos de derivación/ });
    expect(cases).toHaveAttribute("aria-expanded", "true");
    expect(cases).toHaveTextContent("5");
    fireEvent.change(screen.getByLabelText("Mensaje al cliente"), { target: { value: "Borrador específico" } });
    await user.click(cases);
    expect(cases).toHaveAttribute("aria-expanded", "false");
    expect(within(nav).queryByRole("button", { name: "Comuna sin cobertura" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Mensaje al cliente")).toHaveValue("Borrador específico");
    await user.click(cases);
    expect(within(nav).getByRole("button", { name: "Comuna sin cobertura" })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(nav).getByRole("button", { name: /Derivar a una persona/ }));
    await user.click(within(nav).getByRole("button", { name: "Derivación a un asesor" }));
    expect(screen.getByLabelText("Mensaje al cliente")).not.toHaveValue("Borrador específico");
    await user.click(within(nav).getByRole("button", { name: "Comuna sin cobertura" }));
    expect(screen.getByLabelText("Mensaje al cliente")).toHaveValue("Borrador específico");
  });

  afterEach(() => vi.restoreAllMocks());

  it("renders every section and selects Agente by default", () => {
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getAllByRole("tablist").map((tablist) => within(tablist).getAllByRole("tab").map((tab) => tab.textContent))).toEqual([
      ["Chatbot", "Operación", "Integraciones", "Costos"],
      ["Agente", "Persona", "Conducta", "Mensajes"],
    ]);
    expect(screen.getByRole("tab", { name: "Chatbot" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Agente" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
  });

  it("renders only the active group's members", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    const members = () => within(screen.getByRole("tablist", { name: "Secciones de configuración" })).getAllByRole("tab").map((tab) => tab.textContent);
    expect(members()).toEqual(["Agente", "Persona", "Conducta", "Mensajes"]);
    await user.click(screen.getByRole("tab", { name: "Operación" }));
    expect(members()).toEqual(["Horarios y avisos", "Cobertura", "Tarifas"]);
    await user.click(screen.getByRole("tab", { name: "Integraciones" }));
    expect(members()).toEqual(["Capacidades", "API key de modelos", "Correo"]);
    await user.click(screen.getByRole("tab", { name: "Costos" }));
    expect(members()).toEqual(["Costos"]);
  });

  it("saves a DeepSeek key and reports a valid key without balance", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, validation: "no_balance", model_api_key: { configured: true, source: "panel", masked: "…1234" } }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "API key de modelos");
    expect(screen.getByText("No configurada")).toBeInTheDocument();
    const keyInput = screen.getByLabelText("API key de DeepSeek");
    expect(keyInput).toHaveAttribute("type", "password");
    await user.type(keyInput, "sk-test-key");
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Clave válida, pero la cuenta no tiene saldo.")).toBeInTheDocument();
    expect(screen.getByText("Configurada desde el panel")).toBeInTheDocument();
    expect(screen.getByText("…1234")).toBeInTheDocument();
    expect(keyInput).toHaveValue("");
  });

  it("reports a successfully validated key", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, validation: "valid", model_api_key: { configured: true, source: "panel", masked: "…1234" } }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "API key de modelos");
    await user.type(screen.getByLabelText("API key de DeepSeek"), "sk-test-key");
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Clave validada.")).toBeInTheDocument();
  });

  it("maps invalid-key and unavailable validation errors to honest feedback", async () => {
    const user = userEvent.setup();
    const fetch = vi.spyOn(globalThis, "fetch");
    fetch.mockResolvedValueOnce(new Response(JSON.stringify({ detail: "invalid api key" }), { status: 400 }));
    fetch.mockResolvedValueOnce(new Response(JSON.stringify({ detail: "could not validate the api key" }), { status: 502 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "API key de modelos");
    await user.type(screen.getByLabelText("API key de DeepSeek"), "sk-test-key");
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Clave inválida.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("No se pudo validar la clave.")).toBeInTheDocument();
  });

  it("deletes a panel-managed key and refreshes its displayed status", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, model_api_key: { configured: false, source: "none", masked: "" } }), { status: 200 }));
    render(<Settings data={settings({ model_api_key: { configured: true, source: "panel", masked: "…1234" } })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "API key de modelos");
    expect(screen.getByText("Configurada desde el panel")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Borrar" }));
    expect(await screen.findByText("Clave eliminada del panel.")).toBeInTheDocument();
    expect(screen.getByText("No configurada")).toBeInTheDocument();
  });

  it("renders Agente contextual help in popovers and keeps the advanced rule editor", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detección de emergencias" })).toBeInTheDocument();
    expect(screen.getByText("Avanzado")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Cómo funciona" })).toHaveAttribute("popover", "auto");
    expect(screen.queryByText("Usa una categoría por línea. Conserva las reglas actuales si no estás seguro del efecto de un cambio.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ayuda: Alcance del agente" }));
    expect(screen.getByText("El agente responde de forma automática en las categorías configuradas y deriva a una persona cuando la regla lo indica.")).toBeInTheDocument();
    expect(screen.getByText("Usa una categoría por línea. Conserva las reglas actuales si no estás seguro del efecto de un cambio.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ayuda: Detección de emergencias" }));
    expect(screen.getByText("Las palabras clave se revisan en cada mensaje entrante y activan el aviso correspondiente.")).toBeInTheDocument();
    expect(screen.getByText("Incluye términos claros y evita agregar palabras ambiguas que puedan generar avisos innecesarios.")).toBeInTheDocument();
    expect(screen.getByText("Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona.")).toBeInTheDocument();
    expect(screen.getByLabelText("Reglas de alcance")).toHaveAttribute("placeholder", "Ej: reparación=bot_resolve");
    await user.click(screen.getByText("Configuración avanzada"));
    expect(screen.getByLabelText("Reglas de alcance")).toBeVisible();
    expect(screen.getByText("Configuración avanzada").closest("details")).toHaveTextContent(/bot_resolve.*responde por su cuenta.*always_escalate.*deriva la conversación a una persona/);
    expect(screen.getByText("Configuración avanzada").closest("details")).toHaveTextContent("presupuesto=bot_resolve");
  });

  it("shows Historial only for Agente and Persona", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getByRole("button", { name: "Historial" })).toBeInTheDocument();
    await selectSection(user, "Mensajes");
    expect(screen.queryByRole("button", { name: "Historial" })).not.toBeInTheDocument();
    await selectSection(user, "Persona");
    expect(screen.getByRole("button", { name: "Historial" })).toBeInTheDocument();
  });

  it("tracks dirty state, discards without a request, and disables save when clean", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    const save = screen.getByRole("button", { name: "Guardar cambios" });
    expect(screen.getByText("Sin cambios pendientes")).toBeInTheDocument();
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Instrucciones de seguridad"), { target: { value: "Corta el gas.\nVentila." } });
    expect(screen.getByText("Cambios sin guardar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Descartar" }));
    expect(screen.getByLabelText("Instrucciones de seguridad")).toHaveValue("Corta el gas.");
    expect(screen.getByText("Sin cambios pendientes")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("adds and removes emergency keyword chips and persists them through the sticky save bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    const input = screen.getByLabelText("Escribe una frase y presiona Enter");
    await user.type(input, " humo{enter}");
    expect(screen.getByRole("button", { name: "Quitar palabra clave humo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/keywords", expect.objectContaining({
      method: "POST", body: JSON.stringify({ keywords: ["gas", "humo"] }),
    })));
    await user.click(screen.getByRole("button", { name: "Quitar palabra clave humo" }));
    expect(screen.queryByRole("button", { name: "Quitar palabra clave humo" })).not.toBeInTheDocument();
    expect(screen.getByText("Cambios sin guardar")).toBeInTheDocument();
  });

  it("switches sections from the accessible mobile menus", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument());
    const groupMenu = screen.getByRole("button", { name: "Grupo de configuración" });
    expect(groupMenu).toHaveTextContent("Chatbot");
    await user.click(groupMenu);
    await user.click(screen.getByRole("menuitem", { name: "Costos" }));
    expect(screen.getByRole("button", { name: "Sección de configuración" })).toHaveTextContent("Costos");
    expect(screen.getByRole("heading", { name: "Gasto actual" })).toBeInTheDocument();
  });

  it("cannot save a spend limit of zero (S19: 0 would disable the cost gate)", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Costos");
    const conversationLimit = screen.getByLabelText("Límite por conversación");
    const saveLimits = screen.getByRole("button", { name: "Guardar límites" });

    await user.clear(conversationLimit);
    await user.type(conversationLimit, "0");
    expect(saveLimits).toBeDisabled();

    await user.clear(conversationLimit);
    await user.type(conversationLimit, "1.5");
    expect(saveLimits).toBeEnabled();
  });

  it("renders backend-provided tone options and tariff labels", async () => {
    const user = userEvent.setup();
    const payload = settings({ options: {
      tones: ["directo", "formal", "cercano"],
      tarifa_labels: { visita_tecnica: "Servicio A", mantencion_calefont: "Servicio B", mantencion_caldera: "Servicio C", lavado_red: "Servicio D" },
    } });
    render(<Settings data={payload} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await user.click(screen.getByRole("button", { name: "Tono" }));
    expect(within(screen.getByRole("menu")).getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["Directo", "Formal", "Cercano"]);
    await user.click(screen.getByRole("menuitem", { name: "Formal" }));
    await selectSection(user, "Tarifas");
    for (const label of Object.values(payload.options.tarifa_labels)) expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("uses the shared weekday labels for the settings scheduler", async () => {
    const previous = WEEKDAY_NAMES[0];
    WEEKDAY_NAMES[0] = "Lunes compartido";
    try {
      const user = userEvent.setup();
      render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
      await selectSection(user, "Horarios y avisos");
      expect(screen.getByText("Lunes compartido")).toBeInTheDocument();
    } finally {
      WEEKDAY_NAMES[0] = previous;
    }
  });

  it("renders the tone selector in the row header and saves only through the sticky bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    const tone = screen.getByRole("button", { name: "Tono" });
    expect(tone.closest(".card__header")).toContainElement(tone);
    expect(tone).toHaveTextContent("Cercano");
    expect(screen.queryByRole("button", { name: "Guardar tono" })).not.toBeInTheDocument();
    await user.click(tone);
    await user.click(screen.getByRole("menuitem", { name: "Formal" }));
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/tone", expect.objectContaining({ method: "POST", body: JSON.stringify({ tone: "formal" }) })));
  });

  it("disables sticky saving when no tone is configured", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ tone: "" })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
  });

  it("switches the message template editor and previews its edited text", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");

    const greetingPanel = screen.getAllByRole("tabpanel").find((panel) => panel.getAttribute("aria-labelledby")?.includes("trigger-greeting"));
    expect(within(greetingPanel!).getByLabelText("Texto del mensaje")).toHaveValue("Hola");
    await user.click(screen.getByRole("tab", { name: /^Aclaración/ }));
    const clarificationPanel = screen.getAllByRole("tabpanel").find((panel) => panel.getAttribute("aria-labelledby")?.includes("trigger-clarification"));
    const clarification = within(clarificationPanel!).getByLabelText("Texto del mensaje");
    expect(clarification).toHaveValue("¿Cuál?");
    await user.clear(clarification);
    await user.type(clarification, "¿Me puedes indicar tu comuna?");
    const editor = screen.getByRole("heading", { name: "Aclaración" }).closest(".settings-messages__edit");
    expect(within(editor as HTMLElement).getByRole("heading", { name: "Vista previa en WhatsApp" })).toBeInTheDocument();
    expect(within(editor as HTMLElement).getByRole("region", { name: "Vista previa en WhatsApp" }).querySelector(".message-preview__bubble")).toHaveTextContent("¿Me puedes indicar tu comuna?");
  });

  it("labels each greeting according to whether the name is available", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    expect(screen.getByRole("tab", { name: /^Saludo cuando falta el nombre/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^Saludo con nombre/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^Saludo corto cuando falta el nombre/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^Saludo corto con nombre/ })).toBeInTheDocument();
  });

  it("edits the short greeting and saves all ten messages", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await user.click(screen.getByRole("tab", { name: /^Saludo corto cuando falta el nombre/ }));

    const panel = screen.getAllByRole("tabpanel").find((each) => each.getAttribute("aria-labelledby")?.includes("trigger-greeting_short"));
    const textarea = within(panel!).getByLabelText("Texto del mensaje");
    expect(textarea).toHaveValue("Hola, ¿qué necesitas?");
    await user.clear(textarea);
    await user.type(textarea, "Hola, cuéntame");
    expect(screen.queryByRole("button", { name: "Guardar mensajes" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/messages", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ greeting: "Hola", greeting_short: "Hola, cuéntame", greeting_name: "Hola, Ana", greeting_short_name: "Hola, Ana", smalltalk: "Con gusto.", cannot_answer: "No sé", clarification: "¿Cuál?", cannot_understand_offer: "¿Visita o persona?", kb_miss_offer: "No tengo ese dato.", farewell: "Chao", out_of_hours: "Cerrado" }),
    })));
  });

  it("switches the selected template from the mobile selector", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    const selector = screen.getByRole("button", { name: "Plantilla" });
    expect(selector).toHaveTextContent("Saludo cuando falta el nombre");
    expect(screen.getByText("Inicio de conversación; pregunta el nombre del cliente", { selector: ".settings-messages__mobile-selector p" })).toBeInTheDocument();
    await user.click(selector);
    await user.click(screen.getByRole("menuitem", { name: "Despedida" }));
    expect(selector).toHaveTextContent("Despedida");
    expect(screen.getByText("Cierre de conversación", { selector: ".settings-messages__mobile-selector p" })).toBeInTheDocument();
    expect(screen.getAllByRole("tabpanel").find((panel) => panel.getAttribute("aria-labelledby")?.includes("trigger-farewell"))).toBeInTheDocument();
  });

  it("shows the 11 fixed messages, filters them, and previews inside the selected editor", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    expect(screen.getByText("11 mensajes")).toBeInTheDocument();
    expect(screen.getAllByText("Mensaje fijo")).toHaveLength(1);
    const list = screen.getByRole("tablist", { name: "Plantillas de mensajes" });
    expect(within(list).getAllByRole("tab")).toHaveLength(11);
    expect(within(list).queryByText("Mensaje fijo")).not.toBeInTheDocument();
    expect(within(list).getByRole("tab", { name: "Despedida" })).toHaveTextContent("Despedida");
    expect(within(list).queryByText("Cierre de conversación")).not.toBeInTheDocument();
    expect(screen.getByText("Ilustrativa")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vista previa en WhatsApp" }).closest(".settings-messages__edit")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^Saludo con nombre/ })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar mensaje" }), { target: { value: "Aclaración" } });
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /^Aclaración/ })).toBeInTheDocument();
      expect(screen.queryByRole("tab", { name: /^Saludo con nombre/ })).not.toBeInTheDocument();
    });
    const clarification = screen.getByLabelText("Texto del mensaje");
    expect(clarification).toHaveValue("¿Cuál?");
    fireEvent.change(clarification, { target: { value: "Texto aclaratorio" } });
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar mensaje" }), { target: { value: "" } });
    await user.click(await screen.findByRole("tab", { name: /^Saludo con nombre/ }));
    expect(screen.getByLabelText("Texto del mensaje")).toHaveValue("Hola, Ana");
  });

  it("shows the exact empty state and informational band for preset answers", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ templates: [] })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    expect(screen.getByText("Aún no hay respuestas prediseñadas")).toBeInTheDocument();
    expect(screen.getByText("Crea una plantilla para una consulta frecuente.")).toBeInTheDocument();
    expect(screen.getByText("Si falta un dato necesario, el bot responde normalmente.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar respuesta" })).toBeInTheDocument();
  });

  it("saves tone, messages and preset answers through the sticky bar with unchanged payloads", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    const tone = screen.getByRole("button", { name: "Tono" });
    await user.click(tone);
    await user.click(screen.getByRole("menuitem", { name: "Formal" }));
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/tone", expect.objectContaining({ body: JSON.stringify({ tone: "formal" }) })));
    fireEvent.change(screen.getByLabelText("Texto del mensaje"), { target: { value: "Hola editado" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/messages", expect.objectContaining({ body: JSON.stringify({ ...settings().messages, greeting: "Hola editado" }) })));
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    fireEvent.change(screen.getByLabelText("Texto de respuesta 1"), { target: { value: "Respuesta nueva" } });
    fireEvent.change(screen.getByLabelText("ID de respuesta 1"), { target: { value: "respuesta_nueva" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/message-templates", expect.objectContaining({ body: JSON.stringify({ templates: [{ id: "respuesta_nueva", text: "Respuesta nueva" }] }) })));
  });

  it("renders the preset answers card and explains how it differs from fixed messages", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    expect(screen.getByRole("heading", { name: "Respuestas prediseñadas" })).toBeInTheDocument();
    expect(screen.getByText("Plantillas que el bot puede elegir según la consulta y los datos disponibles.")).toBeInTheDocument();
    expect(screen.getByText("Si falta un dato necesario, el bot responde normalmente.")).toBeInTheDocument();
  });

  it("generates a readable template id, can regenerate it, and unlocks explicit manual editing", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    const id = screen.getByLabelText("ID de respuesta 1");
    const text = screen.getByLabelText("Texto de respuesta 1");
    expect(id).toHaveAttribute("readonly");
    await user.type(text, "Tenemos garantía de 12 meses en repuestos.");
    expect(id).toHaveValue("garantia_repuestos");
    expect(screen.getByText("El cliente nunca ve este ID.")).toBeInTheDocument();
    fireEvent.change(text, { target: { value: "Garantía y servicio técnico" } });
    await user.click(screen.getByRole("button", { name: "Editar id de respuesta 1" }));
    expect(id).not.toHaveAttribute("readonly");
    await user.clear(id);
    await user.type(id, "id_manual");
    expect(id).toHaveValue("id_manual");
    await user.click(screen.getByRole("button", { name: "Regenerar ID de respuesta 1" }));
    expect(id).toHaveValue("garantia_servicio_tecnico");
    expect(id).toHaveAttribute("readonly");
  });

  it("shows template slots, sample-data preview, and the permanent missing-data warning", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ templates: [{ id: "garantia", text: "Hola {{nombre}}, cobertura en {{comuna}}." }] })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    expect(screen.getByText(/Datos disponibles:/).parentElement).toHaveTextContent("Datos disponibles: {{nombre}}, {{comuna}}");
    expect(screen.getByRole("heading", { name: "Vista previa de la respuesta 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vista previa de la respuesta 1" }).parentElement?.querySelector(".message-preview__bubble")).toHaveTextContent("Hola Ana, cobertura en Las Condes.");
    expect(screen.getByText("Si falta un dato necesario, el bot responde normalmente.")).toBeInTheDocument();
  });

  it("adds a preset answer row and saves its templates", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    await user.type(screen.getByLabelText("Texto de respuesta 1"), "Hola, cliente");
    await user.click(screen.getByRole("button", { name: "Editar id de respuesta 1" }));
    await user.clear(screen.getByLabelText("ID de respuesta 1"));
    await user.type(screen.getByLabelText("ID de respuesta 1"), "saludo_personalizado");
    expect(screen.queryByRole("button", { name: "Guardar respuestas" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/message-templates", expect.objectContaining({ method: "POST", body: JSON.stringify({ templates: [{ id: "saludo_personalizado", text: "Hola, cliente" }] }) })));
  });

  it("removes a preset answer row", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    expect(screen.getByLabelText("ID de respuesta 1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Eliminar respuesta 1" }));
    expect(screen.queryByLabelText("ID de respuesta 1")).not.toBeInTheDocument();
  });

  it("disables saving preset answers while a row is blank", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findByText("Sintaxis no válida")).toBeInTheDocument();
  });

  it("keeps an edited draft when refreshed persisted data changes", () => {
    const { rerender } = render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    fireEvent.change(screen.getByLabelText("Escribe una frase y presiona Enter"), { target: { value: "incendio" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar" }));
    rerender(<Settings data={settings({ keywords: ["gas", "humo"] })} state="ready" capabilities={capabilities} />);
    expect(screen.getByRole("button", { name: "Quitar palabra clave incendio" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Quitar palabra clave humo" })).not.toBeInTheDocument();
  });

  it("disables invalid save controls and disables a valid save while pending", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ hours: { timezone: "America/Santiago", schedule: [] } })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Horarios de atención" })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Guardar horarios" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
    await selectSection(user, "Mensajes");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument());
    const saveResponse = new Promise<Response>(() => undefined);
    vi.spyOn(globalThis, "fetch").mockReturnValue(saveResponse);
    const tone = screen.getByRole("button", { name: "Tono" });
    await user.click(tone);
    await user.click(screen.getByRole("menuitem", { name: "Formal" }));
    expect(tone).toHaveTextContent("Formal");
    expect(screen.queryByRole("button", { name: "Guardar tono" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeDisabled());
  });

  it("groups, searches, and filters capability tools by ordered category", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={{
      tools: [
        { name: "kb.retrieve", description: "Busca documentos", read_only: true, write: false },
        { name: "kb.index", description: "Indexa documentos", read_only: false, write: true },
        { name: "memory.read", description: "Lee memoria", read_only: true, write: false },
        { name: "web.search", description: "Busca en web", read_only: true, write: false },
        { name: "project.list", description: "Lista proyectos", read_only: true, write: false },
        { name: "plain_tool", description: "Herramienta general", read_only: true, write: false },
      ], personas: ["Cercana"], prompts: ["Atención inicial"], kb_available: true, memory_available: false,
    }} />);
    await selectSection(user, "Capacidades");
    expect(screen.getByRole("heading", { name: "Herramientas del asistente" })).toBeInTheDocument();
    const regions = screen.getAllByRole("region", { hidden: true });
    expect(regions.filter((region) => region.getAttribute("aria-labelledby") && region.textContent?.includes("kb.retrieve"))).toHaveLength(1);
    const groupButtons = screen.getAllByRole("button").filter((button) => button.classList.contains("accordion__trigger"));
    expect(groupButtons.map((button) => button.querySelector(".accordion__title")?.textContent)).toEqual(["Conocimiento y memoria", "Web", "Automatizaciones y proyectos", "Sistema"]);
    await user.click(groupButtons[0]);
    expect(screen.getByText("Consultar base de conocimientos")).toBeInTheDocument();
    expect(screen.getByText("kb.retrieve").tagName).toBe("CODE");
    expect(document.querySelectorAll(".settings-capabilities__tool .badge")).toHaveLength(6);
    await user.selectOptions(screen.getByLabelText("Acceso"), "write");
    expect(screen.getByText("Index")).toBeInTheDocument();
    expect(screen.queryByText("kb.retrieve")).toBeNull();
    fireEvent.change(screen.getByLabelText("Buscar herramientas"), { target: { value: "no existe" } });
    await waitFor(() => expect(screen.getByText("No hay herramientas que coincidan con la búsqueda.")).toBeInTheDocument());
    expect(screen.getByText("Disponible")).toBeInTheDocument();
    expect(screen.getByText("No disponible")).toBeInTheDocument();
  });
  it("renders the persona draft as Markdown and switches to its editor", async () => {
    const user = userEvent.setup();
    const markdown = "# Identidad\n\nEres Max.\n\n- Responde con claridad";
    render(<Settings data={settings({ persona: { orchestrator: markdown, orchestrator_brief: "Sé breve.", customized: false } })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Persona");

    expect(screen.getByRole("heading", { name: "Identidad" })).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Responde con claridad");
    expect(screen.getByText((_content, element) => element?.classList.contains("settings-persona__info") ?? false)).toHaveTextContent("Los datos del cliente se agregan automáticamente. No incluyas variables como {{nombre}}.");
    expect(screen.queryByLabelText("Texto de la persona")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Editar Markdown" }));
    expect(screen.getByLabelText("Texto de la persona")).toHaveValue(markdown);
  });

  it("keeps persona mode and expand controls together below the card heading", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Persona");
    const toolbar = screen.getByRole("toolbar", { name: "Herramientas de persona" });
    expect(within(toolbar).getByRole("button", { name: "Vista previa" })).toHaveAttribute("aria-pressed", "true");
    expect(within(toolbar).getByRole("button", { name: "Editar Markdown" })).toHaveAttribute("aria-pressed", "false");
    await user.click(within(toolbar).getByRole("button", { name: "Ampliar" }));
    expect(screen.getByRole("dialog", { name: "Vista previa de la persona" })).toBeInTheDocument();
  });

  it("opens the persona Markdown in an enlarged dialog", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ persona: { orchestrator: "# Identidad\n\nEres Max.", orchestrator_brief: "Sé breve.", customized: false } })} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Persona");
    await user.click(screen.getByRole("button", { name: "Ampliar" }));

    const dialog = screen.getByRole("dialog", { name: "Vista previa de la persona" });
    expect(dialog).toHaveClass("dialog--wide");
    expect(within(dialog).getByRole("heading", { name: "Identidad" })).toBeInTheDocument();
    expect(within(dialog).getByText("Eres Max.")).toBeInTheDocument();
  });

  it("saves the edited persona and its brief through the sticky bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Persona");
    await user.click(screen.getByRole("button", { name: "Editar Markdown" }));

    const persona = screen.getByLabelText("Texto de la persona");
    expect(persona).toHaveValue("Eres Max.");
    fireEvent.change(persona, { target: { value: "Eres Max, edición del panel." } });
    expect(screen.getByText("Cambios sin guardar")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/persona", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ orchestrator: "Eres Max, edición del panel.", orchestrator_brief: "Sé breve." }),
    })));
  });

  it("saves the emergency protocol with one item per line", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);

    fireEvent.change(screen.getByLabelText("Instrucciones de seguridad"), { target: { value: "Corta el gas.\nVentila el lugar." } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/emergency", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        safety_instructions: ["Corta el gas.", "Ventila el lugar."],
        contacts: ["Bomberos 132."],
        notify_message: "Notificado.",
      }),
    })));
  });
  it("renders ordered capture fields and their inline questions in the Datos y preguntas table", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    const card = screen.getByRole("heading", { name: "Datos y preguntas" }).closest(".card") as HTMLElement;
    expect(within(card).getByText("Define el orden y edita lo que recibe el cliente en cada paso.")).toBeInTheDocument();
    expect(within(card).getByText("3 datos")).toBeInTheDocument();
    expect(within(card).getByRole("columnheader", { name: "#" })).toBeInTheDocument();
    expect(within(card).getByRole("columnheader", { name: "Campo" })).toBeInTheDocument();
    expect(within(card).getByRole("columnheader", { name: "Pregunta al cliente" })).toBeInTheDocument();
    const rows = within(card).getAllByRole("row");
    expect(rows.slice(1).map((row) => row.textContent)).toEqual([
      expect.stringContaining("Problema"), expect.stringContaining("Comuna"), expect.stringContaining("Nombre"),
    ]);
    expect(within(card).getByLabelText("Problema")).toHaveValue("¿Qué pasa con el equipo?");
    expect(within(card).getByLabelText("Comuna")).toHaveValue("¿En qué comuna estás?");
    expect(within(card).getByLabelText("Nombre")).toHaveValue("¿Cuál es tu nombre?");
    expect(within(card).queryByRole("button", { name: /^Guardar/ })).not.toBeInTheDocument();
  });

  it("reorders the table and saves the conduct order through the sticky bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    await user.click(screen.getByRole("button", { name: "Bajar Problema" }));
    expect(screen.getByText("Cambios sin guardar")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/conduct", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ conduct: { orden: ["comuna", "failure", "name"], redaccion: "plantilla", max_preguntas_por_mensaje: 1, derivaciones: ["cobertura"] } }),
    })));
  });

  it("saves inline capture-question edits through the sticky bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    const comuna = screen.getByLabelText("Comuna");
    expect(comuna).toHaveValue("¿En qué comuna estás?");
    fireEvent.change(comuna, { target: { value: "¿En qué comuna queda tu casa?" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/capture-questions", expect.objectContaining({
      body: JSON.stringify({ questions: { failure: "¿Qué pasa con el equipo?", comuna: "¿En qué comuna queda tu casa?", name: "¿Cuál es tu nombre?" } }),
    })));
  });

  it("changes Preguntas por mensaje with the bounded stepper and saves conduct", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    expect(screen.getByText("Los textos se envían tal como están escritos.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aumentar preguntas por mensaje" }));
    expect(screen.getByText("2", { selector: ".settings-conduct__stepper-value" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aumentar preguntas por mensaje" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/conduct", expect.objectContaining({
      body: JSON.stringify({ conduct: { orden: ["failure", "comuna", "name"], redaccion: "plantilla", max_preguntas_por_mensaje: 2, derivaciones: ["cobertura"] } }),
    })));
  });

  it("lets the owner choose how the capture questions are written", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    const trigger = () => screen.getByRole("button", { name: "Redacción de las preguntas" });
    expect(trigger()).toHaveTextContent("Textos fijos");
    await user.click(trigger());
    await user.click(screen.getByRole("menuitem", { name: "Redactada por el modelo" }));
    expect(trigger()).toHaveTextContent("Redactada por el modelo");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/conduct", expect.objectContaining({
      body: JSON.stringify({ conduct: { orden: ["failure", "comuna", "name"], redaccion: "llm", max_preguntas_por_mensaje: 1, derivaciones: ["cobertura"] } }),
    })));
  });

  it("removes a capture field from the table through its kebab menu without removing the last field", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    await user.click(screen.getByRole("button", { name: "Acciones de Problema" }));
    await user.click(screen.getByRole("menuitem", { name: "Quitar" }));
    expect(screen.queryByLabelText("Problema")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Datos y preguntas" }).closest(".card")).toHaveTextContent("2 datos");

    await user.click(screen.getByRole("button", { name: "Acciones de Comuna" }));
    await user.click(screen.getByRole("menuitem", { name: "Quitar" }));
    await user.click(screen.getByRole("button", { name: "Acciones de Nombre" }));
    expect(screen.getByRole("menuitem", { name: "Quitar" })).toHaveAttribute("aria-disabled", "true");
  });

  it("keeps capture-question validation and both capture-order rules in the card", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");

    const card = screen.getByRole("heading", { name: "Datos y preguntas" }).closest(".card") as HTMLElement;
    expect(within(card).getByText("Nombre, correo y dirección se solicitan después de la disponibilidad.")).toBeInTheDocument();
    expect(within(card).getByText("Si quitas un dato, el bot deja de preguntarlo.")).toBeInTheDocument();
    fireEvent.change(within(card).getByLabelText("Nombre"), { target: { value: "{{nombre}}, ¿cómo te llamas?" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findByText("Sintaxis no válida")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("selects a grouped reply and saves its edit through the sticky bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    await user.click(screen.getByRole("button", { name: /Agendar/ }));
    await user.click(screen.getByRole("button", { name: "Oferta de horarios" }));

    expect(screen.getByLabelText("Mensaje al cliente")).toHaveValue("Horarios: {{opciones}}");
    expect(screen.getByRole("heading", { name: "Agendar" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Mensaje al cliente"), { target: { value: "Estos horarios tengo: {{opciones}}" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/reply-texts", expect.objectContaining({
      body: JSON.stringify({ texts: { ...replyTextValues, booking_offer: "Estos horarios tengo: {{opciones}}" } }),
    })));
  });

  // Drives 25 editors on one page: scoped queries keep it fast, and the explicit timeout covers the
  // slowdown of the full suite running many files in parallel.
  it("makes Conducta the single editable owner of all 25 reply texts", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    const situationList = screen.getByRole("navigation", { name: "Situaciones de respuesta" });

    const labels = [
      "Comuna sin cobertura", "Pide hablar con una persona", "Tres mensajes sin entender", "Un dato no se logró tomar", "No hay horarios para agendar",
      "Oferta de horarios", "Sin más horarios para ese día", "No se entendió el horario pedido", "Visita agendada", "No tiene visitas",
      "Confirmar la cancelación", "Elegir una visita", "Ofrecer nuevos horarios", "La visita ya pasó", "No se entendió la visita",
      "No se entendió el horario", "La visita sigue igual", "Sin horarios para reagendar", "Visita reagendada", "Pedir confirmación para cancelar",
      "No se puede cancelar", "Visita cancelada", "Derivación a un asesor", "Pedir evidencia", "Pedir consentimiento",
    ];
    const selectEntry = (label: string) => {
      if (labels.indexOf(label) >= 5 && labels.indexOf(label) <= 8) {
        if (within(situationList).getByRole("button", { name: /Agendar/ }).getAttribute("aria-expanded") !== "true") fireEvent.click(within(situationList).getByRole("button", { name: /Agendar/ }));
      } else if (labels.indexOf(label) >= 9 && labels.indexOf(label) <= 21) {
        if (within(situationList).getByRole("button", { name: /Gestionar una visita/ }).getAttribute("aria-expanded") !== "true") fireEvent.click(within(situationList).getByRole("button", { name: /Gestionar una visita/ }));
      } else if (label === "Derivación a un asesor") {
        if (within(situationList).getByRole("button", { name: /Derivar a una persona/ }).getAttribute("aria-expanded") !== "true") fireEvent.click(within(situationList).getByRole("button", { name: /Derivar a una persona/ }));
      }
      else if (["Pedir evidencia", "Pedir consentimiento"].includes(label)) {
        if (within(situationList).getByRole("button", { name: /Captura/ }).getAttribute("aria-expanded") !== "true") fireEvent.click(within(situationList).getByRole("button", { name: /Captura/ }));
      }
      fireEvent.click(within(situationList).getByRole("button", { name: label }));
    };
    const replyKeys = Object.keys(replyTextValues) as Array<keyof typeof replyTextValues>;
    const changed: Record<string, string> = Object.fromEntries(Object.entries(replyTextValues).map(([key, value]) => [key, `${value} Edición.`]));
    for (let index = 0; index < labels.length; index += 1) {
      selectEntry(labels[index]);
      const editor = screen.getByLabelText("Mensaje al cliente");
      expect(editor).toHaveValue(replyTextValues[replyKeys[index]]);
      fireEvent.change(editor, { target: { value: changed[replyKeys[index]] } });
    }
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/reply-texts", expect.objectContaining({ method: "POST", body: JSON.stringify({ texts: changed }) }));
  }, 60_000);

  it("blocks the sticky save if any of the 25 reply texts is blank", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    const save = screen.getByRole("button", { name: "Guardar cambios" });

    await user.click(screen.getByRole("button", { name: /Agendar/ }));
    await user.click(screen.getByRole("button", { name: "Visita agendada" }));
    fireEvent.change(screen.getByLabelText("Mensaje al cliente"), { target: { value: "   " } });
    expect(save).toBeEnabled();
    await user.click(save);
    expect(await screen.findByText("Sintaxis no válida")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not render flow reply-text editing in Mensajes, while retaining its three other cards", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Mensajes");

    expect(screen.queryByRole("heading", { name: "Respuestas del flujo" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tono del asistente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Respuestas prediseñadas" })).toBeInTheDocument();
  });

  it("keeps the exhausted-day notice editable and saves it through the sticky bar", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Conducta");
    await user.click(screen.getByRole("button", { name: /Agendar/ }));
    await user.click(screen.getByRole("button", { name: "Sin más horarios para ese día" }));

    const notice = screen.getByLabelText("Mensaje al cliente");
    expect(notice).toHaveValue("Sin más horarios para hoy: {{opciones}}");
    fireEvent.change(notice, { target: { value: "Sin más para ese día: {{opciones}}" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/reply-texts", expect.objectContaining({
      body: JSON.stringify({ texts: { ...replyTextValues, booking_no_more_today: "Sin más para ese día: {{opciones}}" } }),
    })));
  });

  describe("derivaciones (S6.5–S6.6)", () => {
    it("shows the five specific cases first and their existing team rule only when offered", async () => {
      const user = userEvent.setup();
      render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
      await selectSection(user, "Conducta");

      expect(screen.getByRole("heading", { name: "Derivaciones y respuestas" })).toBeInTheDocument();
      expect(screen.getByText("Selecciona una situación para editar el mensaje que recibe el cliente.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Comuna sin cobertura" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Pide hablar con una persona" })).toBeInTheDocument();
      expect(screen.getByLabelText("Mensaje al cliente")).toHaveValue("Sin cobertura en {{comuna}}.");
      expect(screen.getByLabelText("Derivar al equipo")).toBeChecked();
      expect(screen.queryByRole("button", { name: "Guardar respuestas" })).not.toBeInTheDocument();
    });

    it("search narrows the situation list", async () => {
      const user = userEvent.setup();
      render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
      await selectSection(user, "Conducta");
      fireEvent.change(screen.getByLabelText("Buscar situación"), { target: { value: "horarios" } });
      await waitFor(() => {
        expect(screen.getByRole("button", { name: "No hay horarios para agendar" })).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Comuna sin cobertura" })).not.toBeInTheDocument();
      });
    });

    it("updates the available derivation rule and marks conduct dirty", async () => {
      const user = userEvent.setup();
      render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
      await selectSection(user, "Conducta");
      await user.click(screen.getByLabelText("Derivar al equipo"));
      expect(screen.getByLabelText("Derivar al equipo")).not.toBeChecked();
      expect(screen.getByText("Cambios sin guardar")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeEnabled();
    });

    it("appends an available slot and previews its sample value", async () => {
      const user = userEvent.setup();
      render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
      await selectSection(user, "Conducta");
      expect(screen.getByText("Sin cobertura en Las Condes.")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Insertar dato {{comuna}}" }));
      expect(screen.getByLabelText("Mensaje al cliente")).toHaveValue("Sin cobertura en {{comuna}}. {{comuna}}");
      expect(screen.getByText("Sin cobertura en Las Condes. Las Condes")).toBeInTheDocument();
    });
  });

  it("links to the standalone push settings page instead of mounting push controls here", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");

    expect(screen.getByRole("link", { name: /configurar notificaciones/i })).toHaveAttribute("href", "/panel/app/push");
    expect(screen.queryByRole("button", { name: /activar notificaciones/i })).not.toBeInTheDocument();
  });

  it("opens Horarios y avisos from the Agenda shortcut fragment", async () => {
    const previousUrl = window.location.href;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ technicians: [] }), { status: 200 }));
    window.history.replaceState({}, "", "/panel/app/settings#schedule");
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(within(screen.getByRole("tablist", { name: "Super-secciones de configuración" })).getByRole("tab", { name: "Operación" })).toHaveAttribute("aria-selected", "true");
    expect(within(screen.getByRole("tablist", { name: "Secciones de configuración" })).getByRole("tab", { name: "Horarios y avisos" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("No hay técnicos disponibles.")).toBeInTheDocument();
    window.history.replaceState({}, "", previousUrl);
  });

  it("saves the minimum booking lead time in hours using the panel contract", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");
    const leadHours = screen.getByLabelText("Anticipación mínima");
    expect(leadHours).toHaveValue(2);
    await user.clear(leadHours);
    await user.type(leadHours, "6");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/booking-lead", expect.objectContaining({
      method: "POST", body: JSON.stringify({ hours: 6 }),
    })));
  });

  it("renders the technician schedule editor under Horarios y avisos", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/panel/api/technicians")) return new Response(JSON.stringify({ technicians: [{ id: 30, username: "Luis Pérez" }] }), { status: 200 });
      if (url.endsWith("/panel/api/technicians/30/schedule")) return new Response(JSON.stringify({ technician_id: 30, schedule: [{ weekday: 1, opens_at: "09:00:00", closes_at: "18:00:00" }] }), { status: 200 });
      return new Response("{}", { status: 200 });
    });
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");
    expect(await screen.findByRole("heading", { name: "Luis Pérez" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Días y horarios de atención")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/technicians", expect.objectContaining({ credentials: "include" }));
  });

  it("retries a technician lookup and shows an empty state when none are available", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("{}", { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ technicians: [] }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar los técnicos");
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("No hay técnicos disponibles.")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("adds a service duration and saves the map", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await selectSection(user, "Horarios y avisos");

    await user.click(screen.getByRole("button", { name: "Agregar servicio" }));
    fireEvent.change(screen.getByLabelText("Servicio 1"), { target: { value: "Calefont" } });
    fireEvent.change(screen.getByLabelText("Minutos 1"), { target: { value: "90" } });
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/durations", expect.objectContaining({
      body: JSON.stringify({ service_durations: { Calefont: 90 } }),
    })));
  });
});
