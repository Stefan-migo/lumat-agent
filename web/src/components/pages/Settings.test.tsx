import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Settings as SettingsData } from "../../types";
import { Settings } from "./Settings";

const settings = (overrides: Partial<SettingsData> = {}): SettingsData => ({
  model_api_key: { configured: false, source: "none", masked: "" },
  email: { host: "localhost", port: 25, from_address: "notificaciones@lumat.cl", user: "", tls: "none", password: { configured: false, masked: "" } },
  scope_rules: { general: "bot_resolve" }, keywords: ["gas"], tone: "cercano",
  messages: { greeting: "Hola", greeting_short: "Hola, ¿qué necesitas?", cannot_answer: "No sé", clarification: "¿Cuál?", farewell: "Chao", out_of_hours: "Cerrado" },
  templates: [],
  hours: { timezone: "America/Santiago", schedule: [{ days: [1], open: "09:00", close: "18:00" }] },
  tarifa: { visita_tecnica: [{ desde_mes: 1, hasta_mes: 12, valor: 30000 }], mantencion_calefont: [{ desde_mes: 1, hasta_mes: 12, valor: 50000 }], mantencion_caldera: [{ desde_mes: 1, hasta_mes: 12, valor: 80000 }], lavado_red: [{ desde_mes: 1, hasta_mes: 12, valor: 140000 }] },
  coverage: ["Las Condes"], service_durations: {},
  conversation_limit: 4, daily_limit: 20, meta_cost: 0.05,
  snapshot: { date: "2026-10-08", conversation_spend: 1, conversation_limit: 4, conversation_percent: 25, daily_spend: 2, daily_limit: 20, daily_percent: 10, mode: "normal" },
  ...overrides,
});
const capabilities = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };

describe("Settings", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders every section and selects Agente by default", () => {
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Agente", "Mensajes", "Horarios y avisos", "Tarifas", "Cobertura", "Costos", "Capacidades", "API key de modelos", "Correo"]);
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

  it("edits the short greeting and saves all six messages", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("tab", { name: "Saludo corto" }));

    const panel = screen.getAllByRole("tabpanel").find((each) => each.getAttribute("aria-labelledby")?.includes("trigger-greeting_short"));
    const textarea = within(panel!).getByLabelText("Texto del mensaje");
    expect(textarea).toHaveValue("Hola, ¿qué necesitas?");
    await user.clear(textarea);
    await user.type(textarea, "Hola, cuéntame");
    await user.click(screen.getByRole("button", { name: "Guardar mensajes" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/messages", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ greeting: "Hola", greeting_short: "Hola, cuéntame", cannot_answer: "No sé", clarification: "¿Cuál?", farewell: "Chao", out_of_hours: "Cerrado" }),
    })));
  });

  it("switches the selected template from the mobile selector", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    const selector = screen.getByRole("button", { name: "Plantilla" });
    expect(selector).toHaveTextContent("Saludo");
    expect(screen.getByText("Inicio de conversación", { selector: ".settings-messages__mobile-selector p" })).toBeInTheDocument();
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

  it("adds a preset answer row and saves its templates", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await user.click(screen.getByRole("button", { name: "Agregar respuesta" }));
    await user.type(screen.getByLabelText("ID de respuesta 1"), "saludo_personalizado");
    fireEvent.change(screen.getByLabelText("Texto de respuesta 1"), { target: { value: "Hola {{nombre}}" } });
    await user.click(screen.getByRole("button", { name: "Guardar respuestas" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/panel/api/settings/message-templates", expect.objectContaining({ method: "POST", body: JSON.stringify({ templates: [{ id: "saludo_personalizado", text: "Hola {{nombre}}" }] }) })));
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
});
