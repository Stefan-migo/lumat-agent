import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Settings as SettingsData } from "../../types";
import { Settings } from "./Settings";

const settings = (overrides: Partial<SettingsData> = {}): SettingsData => ({
  model_api_key: { configured: false, source: "none", masked: "" },
  email: { host: "localhost", port: 25, from_address: "notificaciones@lumat.cl", user: "", tls: "none", password: { configured: false, masked: "" } },
  scope_rules: { general: "bot_resolve" }, keywords: ["gas"], tone: "cercano",
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
    max_preguntas_por_mensaje: 1,
    derivaciones: ["cobertura"],
    customized: false,
    options: {
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
  reply_texts: { texts: { booking_offer: "Horarios: {{opciones}}", manage_kept: "Quedó igual." }, slots: { booking_offer: ["opciones"], manage_kept: [] }, customized: false },
  snapshot: { date: "2026-10-08", conversation_spend: 1, conversation_limit: 4, conversation_percent: 25, daily_spend: 2, daily_limit: 20, daily_percent: 10, mode: "normal" },
  ...overrides,
});
const capabilities = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };

describe("Settings", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders every section and selects Agente by default", () => {
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Agente", "Persona", "Conducta", "Mensajes", "Horarios y avisos", "Tarifas", "Cobertura", "Costos", "Capacidades", "API key de modelos", "Correo"]);
    expect(screen.getByRole("tab", { name: "Agente" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
  });

  it("saves a DeepSeek key and reports a valid key without balance", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true, validation: "no_balance", model_api_key: { configured: true, source: "panel", masked: "…1234" } }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "API key de modelos" }));
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
    await user.click(screen.getByRole("tab", { name: "API key de modelos" }));
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
    await user.click(screen.getByRole("tab", { name: "API key de modelos" }));
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
    await user.click(screen.getByRole("tab", { name: "API key de modelos" }));
    expect(screen.getByText("Configurada desde el panel")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Borrar" }));
    expect(await screen.findByText("Clave eliminada del panel.")).toBeInTheDocument();
    expect(screen.getByText("No configurada")).toBeInTheDocument();
  });

  it("renders the Agente cards, help panels, and editable advanced rules", () => {
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detección de emergencias" })).toBeInTheDocument();
    expect(screen.getByText("Avanzado")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cómo funciona" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Consideraciones" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cómo funciona" }).closest(".help-panel")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alcance del agente" }).closest(".card")).toContainElement(screen.getByRole("heading", { name: "Cómo funciona" }));
    expect(screen.getByRole("heading", { name: "Detección de emergencias" }).closest(".card")).toContainElement(screen.getByRole("heading", { name: "Consideraciones" }));
    expect(screen.getByText("Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona.")).toBeInTheDocument();
    expect(screen.getByLabelText("Reglas de alcance")).toHaveAttribute("placeholder", "Ej: reparación=bot_resolve");
    fireEvent.click(screen.getByText("Sintaxis avanzada"));
    expect(screen.getByText("Sintaxis avanzada").parentElement).toHaveTextContent(/bot_resolve.*responde por su cuenta.*always_escalate.*deriva la conversación a una persona/);
    expect(screen.getByText("Sintaxis avanzada").parentElement).toHaveTextContent("presupuesto=bot_resolve");
    const rules = screen.getByLabelText("Reglas de alcance");
    expect(rules).toHaveValue("general=bot_resolve");
    expect(rules).toBeEnabled();
  });

  it("switches sections from the accessible mobile menu", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument());
    const sectionMenu = screen.getByRole("button", { name: "Sección" });
    expect(sectionMenu).toHaveTextContent("Mensajes");
    await user.click(sectionMenu);
    await user.click(screen.getByRole("menuitem", { name: "Costos" }));
    expect(screen.getByRole("tab", { name: "Costos" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Gasto actual" })).toBeInTheDocument();
  });

  it("cannot save a spend limit of zero (S19: 0 would disable the cost gate)", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Costos" }));
    const conversationLimit = screen.getByLabelText("Límite por conversación");
    const saveLimits = screen.getByRole("button", { name: "Guardar límites" });

    await user.clear(conversationLimit);
    await user.type(conversationLimit, "0");
    expect(saveLimits).toBeDisabled();

    await user.clear(conversationLimit);
    await user.type(conversationLimit, "1.5");
    expect(saveLimits).toBeEnabled();
  });

  it("renders the tone selector and save action together", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    const tone = screen.getByRole("button", { name: "Tono" });
    const saveTone = screen.getByRole("button", { name: "Guardar tono" });
    expect(tone.closest(".settings-messages__tone-row")).toContainElement(saveTone);
    expect(tone).toHaveTextContent("Cercano");
  });

  it("disables saving when no tone is configured", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ tone: "" })} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    expect(screen.getByRole("button", { name: "Guardar tono" })).toBeDisabled();
  });

  it("switches the message template editor and previews its edited text", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));

    const greetingPanel = screen.getAllByRole("tabpanel").find((panel) => panel.getAttribute("aria-labelledby")?.includes("trigger-greeting"));
    expect(within(greetingPanel!).getByLabelText("Texto del mensaje")).toHaveValue("Hola");
    await user.click(screen.getByRole("tab", { name: "Aclaración" }));
    const clarificationPanel = screen.getAllByRole("tabpanel").find((panel) => panel.getAttribute("aria-labelledby")?.includes("trigger-clarification"));
    const clarification = within(clarificationPanel!).getByLabelText("Texto del mensaje");
    expect(clarification).toHaveValue("¿Cuál?");
    await user.clear(clarification);
    await user.type(clarification, "¿Me puedes indicar tu comuna?");
    expect(screen.getByRole("heading", { name: "Vista previa" }).closest("section")?.querySelector(".message-preview__bubble")).toHaveTextContent("¿Me puedes indicar tu comuna?");
  });

  it("labels each greeting according to whether the name is available", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    expect(screen.getByRole("tab", { name: "Saludo cuando falta el nombre" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Saludo con nombre" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Saludo corto cuando falta el nombre" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Saludo corto con nombre" })).toBeInTheDocument();
  });

  it("edits the short greeting and saves all ten messages", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("tab", { name: "Saludo corto cuando falta el nombre" }));

    const panel = screen.getAllByRole("tabpanel").find((each) => each.getAttribute("aria-labelledby")?.includes("trigger-greeting_short"));
    const textarea = within(panel!).getByLabelText("Texto del mensaje");
    expect(textarea).toHaveValue("Hola, ¿qué necesitas?");
    await user.clear(textarea);
    await user.type(textarea, "Hola, cuéntame");
    await user.click(screen.getByRole("button", { name: "Guardar mensajes" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/messages", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ greeting: "Hola", greeting_short: "Hola, cuéntame", greeting_name: "Hola, Ana", greeting_short_name: "Hola, Ana", smalltalk: "Con gusto.", cannot_answer: "No sé", clarification: "¿Cuál?", cannot_understand_offer: "¿Visita o persona?", kb_miss_offer: "No tengo ese dato.", farewell: "Chao", out_of_hours: "Cerrado" }),
    })));
  });

  it("switches the selected template from the mobile selector", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    const selector = screen.getByRole("button", { name: "Plantilla" });
    expect(selector).toHaveTextContent("Saludo cuando falta el nombre");
    expect(screen.getByText("Inicio de conversación; pregunta el nombre del cliente", { selector: ".settings-messages__mobile-selector p" })).toBeInTheDocument();
    await user.click(selector);
    await user.click(screen.getByRole("menuitem", { name: "Despedida" }));
    expect(selector).toHaveTextContent("Despedida");
    expect(screen.getByText("Cierre de conversación", { selector: ".settings-messages__mobile-selector p" })).toBeInTheDocument();
    expect(screen.getAllByRole("tabpanel").find((panel) => panel.getAttribute("aria-labelledby")?.includes("trigger-farewell"))).toBeInTheDocument();
  });

  it("renders the preset answers card and explains how it differs from fixed messages", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    expect(screen.getByRole("heading", { name: "Respuestas prediseñadas" })).toBeInTheDocument();
    expect(screen.getByText("Plantillas que el bot elige solo según lo que pregunta el cliente. Se envían con los datos reales ya cargados (nombre, comuna, equipo o la visita agendada).")).toBeInTheDocument();
    expect(screen.getByText("A diferencia de los Mensajes del asistente de arriba —que son fijos y se disparan solos en momentos puntuales (saludo, derivación, fuera de horario)— estas respuestas las selecciona el bot en cada conversación.")).toBeInTheDocument();
  });

  it("generates a readable template id, can regenerate it, and unlocks explicit manual editing", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
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
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    expect(screen.getByText(/Datos disponibles:/).parentElement).toHaveTextContent("Datos disponibles: {{nombre}}, {{comuna}}");
    expect(screen.getByRole("heading", { name: "Vista previa de la respuesta 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vista previa de la respuesta 1" }).parentElement?.querySelector(".message-preview__bubble")).toHaveTextContent("Hola Ana, cobertura en Las Condes.");
    expect(screen.getByText(/Si a la conversación le falta uno de esos datos, el bot omite esta respuesta y responde normalmente\./)).toBeInTheDocument();
  });

  it("adds a preset answer row and saves its templates", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    await user.type(screen.getByLabelText("Texto de respuesta 1"), "Hola, cliente");
    await user.click(screen.getByRole("button", { name: "Editar id de respuesta 1" }));
    await user.clear(screen.getByLabelText("ID de respuesta 1"));
    await user.type(screen.getByLabelText("ID de respuesta 1"), "saludo_personalizado");
    await user.click(screen.getByRole("button", { name: "Guardar respuestas" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/message-templates", expect.objectContaining({ method: "POST", body: JSON.stringify({ templates: [{ id: "saludo_personalizado", text: "Hola, cliente" }] }) })));
  });

  it("removes a preset answer row", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    expect(screen.getByLabelText("ID de respuesta 1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Eliminar respuesta 1" }));
    expect(screen.queryByLabelText("ID de respuesta 1")).not.toBeInTheDocument();
  });

  it("disables saving preset answers while a row is blank", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    expect(screen.getByRole("button", { name: "Guardar respuestas" })).toBeDisabled();
  });

  it("keeps an edited draft when refreshed persisted data changes", () => {
    const { rerender } = render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    fireEvent.change(screen.getByLabelText("Palabras clave de emergencia"), { target: { value: "gas\nincendio" } });
    rerender(<Settings data={settings({ keywords: ["gas", "humo"] })} state="ready" capabilities={capabilities} />);
    expect(screen.getByLabelText("Palabras clave de emergencia")).toHaveValue("gas\nincendio");
  });

  it("disables invalid save controls and disables a valid save while pending", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings({ hours: { timezone: "America/Santiago", schedule: [] } })} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Horarios y avisos" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Horarios de atención" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Guardar horarios" })).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument());
    const saveResponse = new Promise<Response>(() => undefined);
    vi.spyOn(globalThis, "fetch").mockReturnValue(saveResponse);
    const tone = screen.getByRole("button", { name: "Tono" });
    await user.click(tone);
    await user.click(screen.getByRole("menuitem", { name: "Formal" }));
    expect(tone).toHaveTextContent("Formal");
    await user.click(screen.getByRole("button", { name: "Guardar tono" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Guardar tono" })).toBeDisabled());
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
    await user.click(screen.getByRole("tab", { name: "Capacidades" }));
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
  it("saves the persona and its brief in one request", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Persona" }));

    const persona = screen.getByLabelText("Texto de la persona");
    expect(persona).toHaveValue("Eres Max.");
    fireEvent.change(persona, { target: { value: "Eres Max, edición del panel." } });
    await user.click(screen.getByRole("button", { name: "Guardar persona" }));

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
    await user.click(screen.getByRole("button", { name: "Guardar protocolo" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/emergency", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        safety_instructions: ["Corta el gas.", "Ventila el lugar."],
        contacts: ["Bomberos 132."],
        notify_message: "Notificado.",
      }),
    })));
  });
  it("reorders the capture fields and saves the conduct object", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Conducta" }));

    await user.click(screen.getByRole("button", { name: "Bajar Problema" }));
    await user.click(screen.getByRole("button", { name: "Guardar conducta" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/conduct", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ conduct: { orden: ["comuna", "failure", "name"], max_preguntas_por_mensaje: 1, derivaciones: ["cobertura"] } }),
    })));
  });

  it("saves the capture-question wording exactly as typed", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Conducta" }));

    const comuna = screen.getByLabelText("Comuna");
    expect(comuna).toHaveValue("¿En qué comuna estás?");
    fireEvent.change(comuna, { target: { value: "¿En qué comuna queda tu casa?" } });
    await user.click(screen.getByRole("button", { name: "Guardar preguntas" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/capture-questions", expect.objectContaining({
      body: JSON.stringify({ questions: { failure: "¿Qué pasa con el equipo?", comuna: "¿En qué comuna queda tu casa?", name: "¿Cuál es tu nombre?" } }),
    })));
  });

  it("blocks a capture question that carries braces", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Conducta" }));

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "{{nombre}}, ¿cómo te llamas?" } });

    expect(screen.getByRole("button", { name: "Guardar preguntas" })).toBeDisabled();
  });

  it("saves one deterministic reply from its group", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("button", { name: /Agendar/ }));

    const offer = screen.getByLabelText("Oferta de horarios");
    expect(offer).toHaveValue("Horarios: {{opciones}}");
    expect(screen.getByText("{{opciones}}")).toBeInTheDocument();
    fireEvent.change(offer, { target: { value: "Estos horarios tengo: {{opciones}}" } });
    await user.click(screen.getByRole("button", { name: "Guardar respuestas del flujo" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/reply-texts", expect.objectContaining({
      body: JSON.stringify({ texts: { booking_offer: "Estos horarios tengo: {{opciones}}", manage_kept: "Quedó igual." } }),
    })));
  });

  it("renders the exhausted-day notice inside the booking group", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("button", { name: /Agendar/ }));

    const notice = screen.getByLabelText("Sin más horarios para ese día");
    fireEvent.change(notice, { target: { value: "Sin más para ese día: {{opciones}}" } });
    await user.click(screen.getByRole("button", { name: "Guardar respuestas del flujo" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/reply-texts", expect.objectContaining({
      body: JSON.stringify({ texts: { booking_offer: "Horarios: {{opciones}}", manage_kept: "Quedó igual.", booking_no_more_today: "Sin más para ese día: {{opciones}}" } }),
    })));
  });

  describe("derivaciones (S4)", () => {
    const derivations = {
      handoff_cobertura: "Sin cobertura en {{comuna}}.",
      handoff_persona: "Te paso con una persona del equipo.",
      handoff_unknown_intent_thrice: "Te dejo con una persona del equipo.",
      handoff_campo_sin_respuesta: "Un asesor te contacta para coordinar.",
      handoff_booking_unavailable: "No hay horarios: un asesor te contacta.",
    };
    const withDerivations = () => settings({
      reply_texts: { texts: derivations, slots: { handoff_cobertura: ["comuna"] }, customized: false },
    });

    it("renders the five cases the customer reads a text for", async () => {
      const user = userEvent.setup();
      render(<Settings data={withDerivations()} state="ready" capabilities={capabilities} />);
      await user.click(screen.getByRole("tab", { name: "Conducta" }));

      expect(screen.getByRole("heading", { name: "Derivaciones" })).toBeInTheDocument();
      expect(screen.getByLabelText("Comuna sin cobertura")).toHaveValue("Sin cobertura en {{comuna}}.");
      expect(screen.getByLabelText("Pide hablar con una persona")).toHaveValue("Te paso con una persona del equipo.");
      expect(screen.getByLabelText("Tres mensajes sin entender")).toHaveValue("Te dejo con una persona del equipo.");
      expect(screen.getByLabelText("Un dato no se logró tomar")).toHaveValue("Un asesor te contacta para coordinar.");
      expect(screen.getByLabelText("No hay horarios para agendar")).toHaveValue("No hay horarios: un asesor te contacta.");
      // the only slot of the group is named next to its case
      expect(screen.getByText("{{comuna}}")).toBeInTheDocument();
    });

    it("saves an edited derivation text with the whole reply map", async () => {
      const user = userEvent.setup();
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
      render(<Settings data={withDerivations()} state="ready" capabilities={capabilities} />);
      await user.click(screen.getByRole("tab", { name: "Conducta" }));

      fireEvent.change(screen.getByLabelText("Pide hablar con una persona"), { target: { value: "Ahora te escribe alguien del equipo." } });
      await user.click(screen.getByRole("button", { name: "Guardar derivaciones" }));

      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/reply-texts", expect.objectContaining({
        body: JSON.stringify({ texts: { ...derivations, handoff_persona: "Ahora te escribe alguien del equipo." } }),
      })));
    });

    it("renders only the derivation rule that has a reader", async () => {
      const user = userEvent.setup();
      render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
      await user.click(screen.getByRole("tab", { name: "Conducta" }));

      const rules = screen.getByRole("group", { name: "Derivar a una persona cuando" });

      expect(within(rules).getAllByRole("checkbox")).toHaveLength(1);
      expect(within(rules).getByRole("checkbox", { name: "Comuna fuera de cobertura" })).toBeChecked();
    });
  });

  it("opens Horarios y avisos from the Agenda shortcut fragment", async () => {
    const previousUrl = window.location.href;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ technicians: [] }), { status: 200 }));
    window.history.replaceState({}, "", "/panel/app/settings#schedule");
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getByRole("tab", { name: "Horarios y avisos" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("No hay técnicos disponibles.")).toBeInTheDocument();
    window.history.replaceState({}, "", previousUrl);
  });

  it("saves the minimum booking lead time in hours using the panel contract", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Horarios y avisos" }));
    const leadHours = screen.getByLabelText("Anticipación mínima");
    expect(leadHours).toHaveValue(2);
    await user.clear(leadHours);
    await user.type(leadHours, "6");
    await user.click(screen.getByRole("button", { name: "Guardar anticipación" }));
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
    await user.click(screen.getByRole("tab", { name: "Horarios y avisos" }));
    expect(await screen.findByText("Luis Pérez")).toBeInTheDocument();
    expect(await screen.findByLabelText("Días y horarios de atención")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith("/panel/api/technicians", expect.objectContaining({ credentials: "include" }));
  });

  it("retries a technician lookup and shows an empty state when none are available", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("{}", { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ technicians: [] }), { status: 200 }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Horarios y avisos" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar los técnicos");
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("No hay técnicos disponibles.")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("adds a service duration and saves the map", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Horarios y avisos" }));

    await user.click(screen.getByRole("button", { name: "Agregar servicio" }));
    fireEvent.change(screen.getByLabelText("Servicio 1"), { target: { value: "Calefont" } });
    fireEvent.change(screen.getByLabelText("Minutos 1"), { target: { value: "90" } });
    await user.click(screen.getByRole("button", { name: "Guardar duraciones" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/durations", expect.objectContaining({
      body: JSON.stringify({ service_durations: { Calefont: 90 } }),
    })));
  });
});
