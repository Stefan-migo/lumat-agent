import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { settings } from "./_shared/mockData/settings";
import { Settings } from "../../components/pages/Settings";
import { SettingsView } from "./Settings.stories";
import * as settingsStories from "./Settings.stories";
import type { AssistantCapabilities } from "../../types";

const capabilities: AssistantCapabilities = {
  tools: [
    { name: "agenda.consultar", description: "Consulta horarios", read_only: true, write: false },
    { name: "agenda.crear_visita", description: "Agenda una visita", read_only: false, write: true },
  ],
  personas: ["Cercana", "Técnica"],
  prompts: ["Atención inicial", "Emergencias"],
  kb_available: true,
  memory_available: false,
};

const groupForSection: Record<string, string> = {
  Agente: "Chatbot", Persona: "Chatbot", Conducta: "Chatbot", Mensajes: "Chatbot",
  "Horarios y avisos": "Operación", Cobertura: "Operación", Tarifas: "Operación",
  Capacidades: "Integraciones", "API key de modelos": "Integraciones", Correo: "Integraciones", Costos: "Costos",
};
async function selectSection(label: string) {
  const user = userEvent.setup();
  await user.click(within(await screen.findByRole("tablist", { name: "Super-secciones de configuración" })).getByRole("tab", { name: groupForSection[label] }));
  await user.click(within(await screen.findByRole("tablist", { name: "Secciones de configuración" })).getByRole("tab", { name: label }));
}

describe("Settings page story (SS-1..SS-5 / S6 DS-UI-COPY/STATES/TABLES)", () => {
  it("publishes the composed push support and fallback states", () => {
    expect(settingsStories.PushPermission).toBeDefined();
    expect(settingsStories.PushFallback).toBeDefined();
    expect(settingsStories.PushFallback).toBeDefined();
  });

  it("renders the Spanish page title 'Configuración'", () => {
    render(<SettingsView />);
    expect(screen.getByRole("heading", { name: "Configuración" })).toBeInTheDocument();
  });

  it("renders groups by business consequence with approved Spanish card titles", async () => {
    render(<SettingsView />);
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detección de emergencias" })).toBeInTheDocument();
    await selectSection("Mensajes");
    expect(screen.getByRole("heading", { name: "Tono del asistente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument();
    await selectSection("Costos");
    expect(screen.getByRole("heading", { name: "Límites de gasto" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Precio Meta" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Gasto actual" })).toBeInTheDocument();
  });

  it("explains the agent-scope effect in plain Spanish before the input", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Alcance del agente" }).closest(".card") as HTMLElement;
    // The explanation precedes the textarea and is readable, not raw English.
    expect(card.querySelector(".card__description")).toHaveTextContent(/el agente responde de forma automática/i);
    expect(within(card).queryByText(/one rule per line: category=mode/i)).toBeNull();
  });

  it("separates and explains the advanced category=mode syntax, keeping the editable lines", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Alcance del agente" }).closest(".card") as HTMLElement;
    const advanced = within(card).getByText(/sintaxis avanzada/i);
    expect(advanced).toBeInTheDocument();
    // The raw category=mode lines still live in the textarea (editable technical value),
    // but they are visually separated behind an 'advanced' disclosure.
    const rulesTextarea = within(card).getByLabelText(/reglas de alcance/i) as HTMLTextAreaElement;
    const lines = rulesTextarea.value.split("\n").filter((l) => l.length > 0);
    expect(lines.length).toBeGreaterThan(0);
    const modePattern = /^([a-z_]+)=(bot_resolve|always_escalate)$/;
    for (const line of lines) {
      expect(line).toMatch(modePattern);
    }
  });

  it("shows validation for invalid category=mode lines before saving (DS-UI-STATES)", () => {
    render(<SettingsView state="validation" />);
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(/sintaxis no válida/i)).toBeInTheDocument();
    expect(within(alert).getByText(/cada línea debe tener categoría=mode/i)).toBeInTheDocument();
  });

  it("renders one save action per independently persisted group", async () => {
    render(<SettingsView />);
    await selectSection("Mensajes");
    const toneCard = screen.getByRole("heading", { name: "Tono del asistente" }).closest(".card") as HTMLElement;
    expect(within(toneCard).queryByRole("button", { name: "Guardar tono" })).not.toBeInTheDocument();
    const toneMessageCard = screen.getByRole("heading", { name: "Mensajes del asistente" }).closest(".card") as HTMLElement;
    expect(within(toneMessageCard).queryByRole("button", { name: "Guardar mensajes" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeInTheDocument();
    await selectSection("Costos");
    const limitsCard = screen.getByRole("heading", { name: "Límites de gasto" }).closest(".card") as HTMLElement;
    const pricingCard = screen.getByRole("heading", { name: "Precio Meta" }).closest(".card") as HTMLElement;
    expect(within(limitsCard).getByRole("button", { name: "Guardar límites" })).toBeInTheDocument();
    expect(within(pricingCard).getByRole("button", { name: "Guardar precio" })).toBeInTheDocument();
    await selectSection("Agente");
    const agentCard = screen.getByRole("heading", { name: "Alcance del agente" }).closest(".card") as HTMLElement;
    const emergencyCard = screen.getByRole("heading", { name: "Detección de emergencias" }).closest(".card") as HTMLElement;
    expect(within(agentCard).queryByRole("button", { name: /^Guardar/ })).not.toBeInTheDocument();
    expect(within(emergencyCard).queryByRole("button", { name: /^Guardar/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar cambios" })).toBeInTheDocument();
  });

  it("renders the emergency keywords as chips with the plain-Spanish effect", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Detección de emergencias" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/próximo mensaje entrante/i)).toBeInTheDocument();
    const chips = within(card).getByRole("list", { name: "Palabras y frases de activación" });
    expect(within(chips).getAllByRole("listitem")).toHaveLength(settings.keywords.length);
    for (const keyword of settings.keywords) {
      expect(within(chips).getByText(keyword)).toBeInTheDocument();
    }
  });

  it("renders the tone selector with the current tone value and plain-Spanish effect", async () => {
    render(<SettingsView />);
    await selectSection("Mensajes");
    const card = screen.getByRole("heading", { name: "Tono del asistente" }).closest(".card") as HTMLElement;
    expect(within(card).getByText("Define el estilo de las respuestas generadas. Los mensajes fijos se envían tal como los escribes.")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Tono" })).toHaveTextContent("Cercano");
  });

  it("renders the editable standard messages with their configured text", async () => {
    render(<SettingsView />);
    await selectSection("Mensajes");
    const card = screen.getByRole("heading", { name: "Mensajes del asistente" }).closest(".card") as HTMLElement;
    expect(within(card).getByText("Menú de categorías automático")).toBeInTheDocument();
    const templates = [
      ["greeting", "Saludo cuando falta el nombre", settings.messages.greeting],
      ["greeting_name", "Saludo con nombre", settings.messages.greeting_name],
      ["greeting_short", "Saludo corto cuando falta el nombre", settings.messages.greeting_short],
      ["greeting_short_name", "Saludo corto con nombre", settings.messages.greeting_short_name],
      ["smalltalk", "Cortesía", settings.messages.smalltalk],
      ["cannot_answer", "Cuando no puede responder", settings.messages.cannot_answer],
      ["clarification", "Aclaración", settings.messages.clarification],
      ["farewell", "Despedida", settings.messages.farewell],
      ["out_of_hours", "Fuera de horario", settings.messages.out_of_hours],
    ] as const;
    for (const [id, label, value] of templates) {
      const tab = within(card).getByRole("tab", { name: new RegExp(`^${label}`) });
      expect(tab).toBeInTheDocument();
      await userEvent.click(tab);
      const panel = screen.getAllByRole("tabpanel").find((item) => item.getAttribute("aria-labelledby")?.includes(`trigger-${id}`));
      expect(within(panel!).getByLabelText("Texto del mensaje")).toHaveValue(value);
    }
  });

  it("renders the configured timezone and weekly table without an always-open new editor", async () => {
    render(<SettingsView />);
    await selectSection("Horarios y avisos");
    const card = screen.getByRole("heading", { name: "Horarios de atención" }).closest(".card") as HTMLElement;
    expect(within(card.querySelector(".card__header")!).getByLabelText("Zona horaria")).toHaveValue(settings.hours.timezone);
    expect(within(card).getByRole("table")).toBeInTheDocument();
    expect(within(card).getByLabelText("Inicio horario 1")).toHaveValue("09:00");
    expect(within(card).getByLabelText("Fin horario 1")).toHaveValue("18:00");
    expect(within(card).queryByRole("group", { name: "Días de atención" })).not.toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Agregar horario" })).toBeEnabled();
  });

  it("keeps the occupied-day rule in the schedule editor", async () => {
    render(<SettingsView />);
    await selectSection("Horarios y avisos");
    const card = screen.getByRole("heading", { name: "Horarios de atención" }).closest(".card") as HTMLElement;
    fireEvent.click(within(card).getByRole("button", { name: "Agregar horario" }));
    const days = within(card).getByRole("group", { name: "Días de atención" });
    fireEvent.click(within(days).getByRole("button", { name: "Lun" }));
    expect(within(days).getByRole("button", { name: "Lun" })).toHaveAttribute("aria-pressed", "false");
  });

  it("renders the paired USD spend-limit inputs", async () => {
    render(<SettingsView />);
    await selectSection("Costos");
    const card = screen.getByRole("heading", { name: "Límites de gasto" }).closest(".card") as HTMLElement;
    const conv = within(card).getByLabelText(/límite por conversación/i) as HTMLInputElement;
    const daily = within(card).getByLabelText(/límite diario/i) as HTMLInputElement;
    expect(Number(conv.value)).toBe(settings.conversation_limit);
    expect(Number(daily.value)).toBe(settings.daily_limit);
    expect(within(card).getAllByText("USD")).toHaveLength(2);
  });

  it("renders the Meta pricing input and effective-date chip", async () => {
    render(<SettingsView />);
    await selectSection("Costos");
    const card = screen.getByRole("heading", { name: "Precio Meta" }).closest(".card") as HTMLElement;
    expect(within(card).getByText("Vigente desde el 1 oct 2026")).toBeInTheDocument();
    const cost = within(card).getByLabelText(/costo por mensaje/i) as HTMLInputElement;
    expect(Number(cost.value)).toBe(settings.meta_cost);
    expect(within(card).getByText("USD")).toBeInTheDocument();
  });

  it("renders current spend as a three-metric row with its date and conversation context", async () => {
    render(<SettingsView />);
    await selectSection("Costos");
    const card = screen.getByRole("heading", { name: "Gasto actual" }).closest(".card") as HTMLElement;
    const snap = settings.snapshot;
    expect(within(card).getByText("19 ago 2026")).toBeInTheDocument();
    expect(within(card).getByText("Gasto diario")).toBeInTheDocument();
    expect(within(card).getByText("Límite diario")).toBeInTheDocument();
    expect(within(card).getByText("Del límite utilizado")).toBeInTheDocument();
    expect(within(card).getByText(`USD ${snap.daily_spend.toFixed(4)}`)).toBeInTheDocument();
    expect(within(card).getByText(`USD ${snap.daily_limit.toFixed(2)}`)).toBeInTheDocument();
    expect(within(card).getByText(`${snap.daily_percent.toFixed(1)}%`)).toBeInTheDocument();
    if (snap.conversation_percent !== null) {
      expect(within(card).getByText(`Conversación: ${snap.conversation_percent}% de USD ${snap.conversation_limit.toFixed(2)}`)).toBeInTheDocument();
    }
  });

  it("explains the 80% and 100% threshold actions", async () => {
    render(<SettingsView />);
    await selectSection("Costos");
    expect(screen.getByRole("heading", { name: "Qué ocurre al alcanzar los límites" })).toBeInTheDocument();
    expect(screen.getByText(/Respuestas más conservadoras/)).toBeInTheDocument();
    expect(screen.getByText(/Derivación a una persona/)).toBeInTheDocument();
  });

  it("renders saving state (DS-UI-STATES)", () => {
    render(<SettingsView state="saving" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Guardando cambios")).toBeInTheDocument();
  });

  it("renders saved state (DS-UI-STATES)", () => {
    render(<SettingsView state="saved" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText("Configuración guardada")).toBeInTheDocument();
  });

  it("renders server-error state (DS-UI-STATES)", () => {
    render(<SettingsView state="server-error" />);
    const banner = screen.getByRole("alert");
    expect(within(banner).getByText("No pudimos guardar los cambios")).toBeInTheDocument();
  });

  it("renders stale-state note above the data (DS-UI-STATES)", () => {
    render(<SettingsView state="stale" />);
    const banner = screen.getByRole("status");
    expect(within(banner).getByText(/datos posiblemente desactualizados/i)).toBeInTheDocument();
  });

  it("points the schedule section at the single push settings page", async () => {
    render(<SettingsView />);
    await selectSection("Horarios y avisos");
    const push = screen.getByRole("heading", { name: "Notificaciones del navegador" }).closest(".card") as HTMLElement;
    expect(push).toBeInTheDocument();
    // One mounting only: the card links to the standalone page instead of composing it.
    expect(within(push).getByRole("link", { name: /configurar notificaciones/i })).toHaveAttribute("href", "/panel/app/push");
  });

  it("renders grouped capability tools and translated configuration availability", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (input === "/panel/api/settings") return new Response(JSON.stringify(settings), { status: 200 });
      if (input === "/panel/api/assistant/capabilities") return new Response(JSON.stringify(capabilities), { status: 200 });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    render(<Settings />);
    await selectSection("Capacidades");

    const card = await screen.findByRole("heading", { name: "Herramientas del asistente" });
    const toolsCard = card.closest(".card") as HTMLElement;
    const user = userEvent.setup();
    await user.click(within(toolsCard).getByRole("button", { name: /Operación/ }));
    expect(within(toolsCard).getByText("Consultar")).toBeInTheDocument();
    expect(within(toolsCard).getByText("Crear visita")).toBeInTheDocument();
    expect(within(toolsCard).getByText("agenda.crear_visita").tagName).toBe("CODE");
    expect(within(toolsCard).getAllByText("Solo lectura")).toHaveLength(2);
    expect(within(toolsCard).getAllByText("Puede escribir")).toHaveLength(2);
    expect(within(toolsCard).getByRole("button", { name: /Operación/ })).toHaveTextContent("2");
    expect(screen.getByText("Cercana")).toBeInTheDocument();
    expect(screen.getByText("Técnica")).toBeInTheDocument();
    expect(screen.getByText("Atención inicial")).toBeInTheDocument();
    expect(screen.getByText("Emergencias")).toBeInTheDocument();
    expect(screen.getByText("Disponible")).toBeInTheDocument();
    expect(screen.getByText("No disponible")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Consultar" })).toHaveAttribute("href", "/panel/app/kb");
    expect(screen.queryByText(/read_only|kb_available|memory_available/)).toBeNull();
    fetchMock.mockRestore();
  });

  it("shows a capability loading state without hiding ready settings", async () => {
    let resolveCapabilities!: (response: Response) => void;
    const capabilitiesRequest = new Promise<Response>((resolve) => { resolveCapabilities = resolve; });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (input === "/panel/api/settings") return new Response(JSON.stringify(settings), { status: 200 });
      if (input === "/panel/api/assistant/capabilities") return capabilitiesRequest;
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    render(<Settings />);
    await selectSection("Capacidades");

    expect(await screen.findByText("Cargando capacidades del asistente")).toBeInTheDocument();
    resolveCapabilities(new Response(JSON.stringify(capabilities), { status: 200 }));
    fetchMock.mockRestore();
  });

  it("shows a Spanish capability error while preserving settings", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (input === "/panel/api/settings") return new Response(JSON.stringify(settings), { status: 200 });
      if (input === "/panel/api/assistant/capabilities") return new Response("unavailable", { status: 503 });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    render(<Settings />);
    await selectSection("Capacidades");

    expect(await screen.findByText("No pudimos cargar las capacidades del asistente")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Configuración" })).toBeInTheDocument();
    fetchMock.mockRestore();
  });

  it("keeps the push entry point when this browser cannot subscribe", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ public_key: null }), { status: 200 }));
    render(<Settings data={settings} state="ready" />);
    await selectSection("Horarios y avisos");
    const push = screen.getByRole("heading", { name: "Notificaciones del navegador" }).closest(".card") as HTMLElement;
    // The unsupported-browser explanation belongs to the page now; the section must still lead there.
    expect(within(push).getByRole("link", { name: /configurar notificaciones/i })).toHaveAttribute("href", "/panel/app/push");
    fetchMock.mockRestore();
  });
});

describe("Settings API page", () => {
  it("saves a changed tone through the admin settings endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (input === "/panel/api/settings" && !init?.method) {
        return new Response(JSON.stringify(settings), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    render(<Settings />);
    await selectSection("Mensajes");
    const tone = await screen.findByRole("button", { name: "Tono" });
    await waitFor(() => expect(tone).toHaveTextContent("Cercano"));
    await userEvent.setup().click(tone);
    await userEvent.setup().click(screen.getByRole("menuitem", { name: "Directo" }));
    await userEvent.setup().click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/settings/tone",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ tone: "directo" }) }),
    ));
    expect(await screen.findByRole("status")).toHaveTextContent("Configuración guardada");
    fetchMock.mockRestore();
  });

  it("saves edited standard messages through the messages endpoint", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (input === "/panel/api/settings" && !init?.method) return new Response(JSON.stringify(settings), { status: 200 });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    render(<Settings />);
    await selectSection("Mensajes");
    const templates = screen.getByRole("tablist", { name: "Plantillas de mensajes" });
    const greetingTab = within(templates).getByRole("tab", { name: /^Saludo cuando falta el nombre/ });
    const getEditor = (id: string) => {
      const panel = screen.getAllByRole("tabpanel").find((item) => item.getAttribute("aria-labelledby")?.includes(`trigger-${id}`));
      return within(panel!).getByLabelText("Texto del mensaje");
    };
    const greeting = getEditor("greeting");
    fireEvent.change(greeting, { target: { value: "Hola nuevo" } });
    await user.click(within(templates).getByRole("tab", { name: /^Despedida/ }));
    const farewell = getEditor("farewell");
    fireEvent.change(farewell, { target: { value: "Hasta luego nuevo" } });
    await user.click(within(templates).getByRole("tab", { name: /^Fuera de horario/ }));
    const outOfHours = getEditor("out_of_hours");
    fireEvent.change(outOfHours, { target: { value: "Estamos cerrados" } });
    expect(greetingTab).toHaveAttribute("aria-selected", "false");
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/settings/messages",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ ...settings.messages, greeting: "Hola nuevo", farewell: "Hasta luego nuevo", out_of_hours: "Estamos cerrados" }) }),
    ));
    fetchMock.mockRestore();
  });

  it("saves a valid hours change through the hours endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (input === "/panel/api/settings" && !init?.method) return new Response(JSON.stringify(settings), { status: 200 });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    render(<Settings />);
    await selectSection("Horarios y avisos");
    const timezone = await screen.findByLabelText("Zona horaria");
    const card = timezone.closest(".card") as HTMLElement;
    fireEvent.change(within(card).getByLabelText("Zona horaria"), { target: { value: "America/New_York" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/settings/hours",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ timezone: "America/New_York", schedule: settings.hours.schedule }) }),
    ));
    fetchMock.mockRestore();
  });

  it("surfaces the API detail when saving an invalid schedule", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (input === "/panel/api/settings" && !init?.method) return new Response(JSON.stringify(settings), { status: 200 });
      return new Response(JSON.stringify({ detail: "weekday repeated across entries" }), { status: 400 });
    });
    render(<Settings />);
    await selectSection("Horarios y avisos");
    fireEvent.change(await screen.findByLabelText("Zona horaria"), { target: { value: "America/New_York" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(await screen.findByText("weekday repeated across entries")).toBeInTheDocument();
    fetchMock.mockRestore();
  });

  it("saves both spend limits through the limits endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (input === "/panel/api/settings" && !init?.method) {
        return new Response(JSON.stringify(settings), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    render(<Settings />);
    await selectSection("Costos");
    const dailyLimit = await screen.findByLabelText("Límite diario");
    await waitFor(() => expect(dailyLimit).toHaveValue(5));
    fireEvent.change(dailyLimit, { target: { value: "7.5" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar límites" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/settings/limits",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ conversation_limit: 1.5, daily_limit: 7.5 }) }),
    ));
    fetchMock.mockRestore();
  });

  it("renders the cost metrics, effective date, and threshold actions", async () => {
    render(<SettingsView />);
    await selectSection("Costos");

    expect(await screen.findByText("Gasto diario")).toBeInTheDocument();
    expect(screen.getByText("Límite diario", { selector: ".stat-card__label" })).toBeInTheDocument();
    expect(screen.getByText("Del límite utilizado")).toBeInTheDocument();
    expect(screen.getByText("19 ago 2026")).toBeInTheDocument();
    expect(screen.getByText("Vigente desde el 1 oct 2026")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Qué ocurre al alcanzar los límites" })).toBeInTheDocument();
    expect(screen.getByText(/Respuestas más conservadoras/)).toBeInTheDocument();
    expect(screen.getByText(/Derivación a una persona/)).toBeInTheDocument();
  });

  it("edits and saves the tariff with the agreed services", async () => {
    render(<SettingsView />);
    await selectSection("Tarifas");
    const card = screen.getByRole("heading", { name: "Tarifario" }).closest(".card") as HTMLElement;
    expect(within(card).getByLabelText(/Visita técnica/)).toHaveValue(30000);
    expect(within(card).getByLabelText(/Mantención de calefont .*marzo a octubre/i)).toHaveValue(50000);

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    fireEvent.change(within(card).getByLabelText(/Mantención de calefont .*marzo a octubre/i), { target: { value: "52000" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/settings/tarifa",
      expect.objectContaining({ method: "POST", body: expect.stringContaining("52000") }),
    ));
    fetchMock.mockRestore();
  });

  it("edits and saves the coverage communes", async () => {
    render(<SettingsView />);
    await selectSection("Cobertura");
    const card = screen.getByRole("heading", { name: "Cobertura" }).closest(".card") as HTMLElement;
    const field = within(card).getByLabelText("Comunas con cobertura");
    expect(field).toHaveValue(["Las Condes", "Ñuñoa", "Lo Barnechea", "La Reina", "Peñalolén", "Colina", "Huechuraba"].join("\n"));

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    fireEvent.change(field, { target: { value: "Las Condes\nColina" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/panel/api/settings/coverage",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ communes: ["Las Condes", "Colina"] }) }),
    ));
    fetchMock.mockRestore();
  });

  it("renders permission denied when an operador receives 403", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "admin role required" }), { status: 403 }),
    );

    render(<Settings />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No tienes permiso para ver este panel");
    expect(screen.queryByText("No pudimos cargar la configuración")).toBeNull();
    fetchMock.mockRestore();
  });
});
