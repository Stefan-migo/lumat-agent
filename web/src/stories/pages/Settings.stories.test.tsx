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

async function selectSection(label: string) {
  await userEvent.setup().click(await screen.findByRole("tab", { name: label }));
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
    expect(within(card).getByText(/el agente responde de forma automática/i)).toBeInTheDocument();
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
    expect(within(toneCard).getByRole("button", { name: "Guardar tono" })).toBeInTheDocument();
    const toneMessageCard = screen.getByRole("heading", { name: "Mensajes del asistente" }).closest(".card") as HTMLElement;
    expect(within(toneMessageCard).getByRole("button", { name: "Guardar mensajes" })).toBeInTheDocument();
    await selectSection("Costos");
    const limitsCard = screen.getByRole("heading", { name: "Límites de gasto" }).closest(".card") as HTMLElement;
    const pricingCard = screen.getByRole("heading", { name: "Precio Meta" }).closest(".card") as HTMLElement;
    expect(within(limitsCard).getByRole("button", { name: "Guardar límites" })).toBeInTheDocument();
    expect(within(pricingCard).getByRole("button", { name: "Guardar precio" })).toBeInTheDocument();
    await selectSection("Agente");
    const agentCard = screen.getByRole("heading", { name: "Alcance del agente" }).closest(".card") as HTMLElement;
    const emergencyCard = screen.getByRole("heading", { name: "Detección de emergencias" }).closest(".card") as HTMLElement;
    expect(within(agentCard).getByRole("button", { name: "Guardar alcance" })).toBeInTheDocument();
    expect(within(emergencyCard).getByRole("button", { name: "Guardar palabras clave" })).toBeInTheDocument();
  });

  it("renders the emergency-keywords textarea with one keyword per line and plain-Spanish effect", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Detección de emergencias" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/próximo mensaje entrante/i)).toBeInTheDocument();
    const keywordsTextarea = within(card).getByLabelText(/palabras clave/i) as HTMLTextAreaElement;
    const lines = keywordsTextarea.value.split("\n").filter((l) => l.length > 0);
    expect(lines.length).toBe(settings.keywords.length);
    for (const kw of settings.keywords) {
      expect(lines).toContain(kw);
    }
  });

  it("renders the tone selector with the current tone value and plain-Spanish effect", async () => {
    render(<SettingsView />);
    await selectSection("Mensajes");
    const card = screen.getByRole("heading", { name: "Tono del asistente" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/respuestas del agente/i)).toBeInTheDocument();
    const toneSelect = within(card).getByLabelText(/tono/i) as HTMLSelectElement;
    expect(toneSelect.value).toBe(settings.tone);
  });

  it("renders the five editable standard messages", async () => {
    render(<SettingsView />);
    await selectSection("Mensajes");
    const card = screen.getByRole("heading", { name: "Mensajes del asistente" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/menú de categorías se agrega automáticamente/i)).toBeInTheDocument();
    const templates = [
      ["greeting", "Saludo", settings.messages.greeting],
      ["cannot_answer", "Cuando no puede responder", settings.messages.cannot_answer],
      ["clarification", "Aclaración", settings.messages.clarification],
      ["farewell", "Despedida", settings.messages.farewell],
      ["out_of_hours", "Fuera de horario", settings.messages.out_of_hours],
    ] as const;
    for (const [id, label, value] of templates) {
      await userEvent.click(within(card).getByRole("tab", { name: label }));
      const panel = screen.getAllByRole("tabpanel").find((item) => item.getAttribute("aria-labelledby")?.includes(`trigger-${id}`));
      expect(within(panel!).getByLabelText(label)).toHaveValue(value);
    }
  });

  it("renders the configured timezone, weekly schedule, and new schedule editor", async () => {
    render(<SettingsView />);
    await selectSection("Horarios y avisos");
    const card = screen.getByRole("heading", { name: "Horarios de atención" }).closest(".card") as HTMLElement;
    expect(within(card).getByLabelText("Zona horaria")).toHaveValue(settings.hours.timezone);
    expect(within(card).getByText("Lun, Mar, Mié, Jue, Vie")).toBeInTheDocument();
    expect(within(card).getByText("09:00 – 18:00")).toBeInTheDocument();
    expect(within(card).getByLabelText("Días del nuevo horario")).toBeInTheDocument();
    expect(within(card).getByLabelText("Inicio")).toHaveValue("09:00");
    expect(within(card).getByLabelText("Fin")).toHaveValue("18:00");
    expect(within(card).getByRole("button", { name: "Agregar otro horario" })).toBeDisabled();
  });

  it("prevents duplicate weekdays when adding a schedule entry", async () => {
    render(<SettingsView />);
    await selectSection("Horarios y avisos");
    const card = screen.getByRole("heading", { name: "Horarios de atención" }).closest(".card") as HTMLElement;
    fireEvent.click(within(card).getByRole("button", { name: "Lun" }));
    expect(within(card).getByRole("button", { name: "Agregar otro horario" })).toBeDisabled();
    fireEvent.click(within(card).getByRole("button", { name: "Sáb" }));
    expect(within(card).getByRole("button", { name: "Agregar otro horario" })).toBeEnabled();
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
    expect(within(card).getByText("Vigente desde 2026-10-01")).toBeInTheDocument();
    const cost = within(card).getByLabelText(/costo por mensaje/i) as HTMLInputElement;
    expect(Number(cost.value)).toBe(settings.meta_cost);
    expect(within(card).getByText("USD")).toBeInTheDocument();
  });

  it("renders current spend as a three-metric row with its date and conversation context", async () => {
    render(<SettingsView />);
    await selectSection("Costos");
    const card = screen.getByRole("heading", { name: "Gasto actual" }).closest(".card") as HTMLElement;
    const snap = settings.snapshot;
    expect(within(card).getByText(snap.date)).toBeInTheDocument();
    expect(within(card).getByText("Gasto diario")).toBeInTheDocument();
    expect(within(card).getByText("Límite diario")).toBeInTheDocument();
    expect(within(card).getByText("Del límite utilizado")).toBeInTheDocument();
    expect(within(card).getByText(`$${snap.daily_spend.toFixed(4)}`)).toBeInTheDocument();
    expect(within(card).getByText(`$${snap.daily_limit.toFixed(2)}`)).toBeInTheDocument();
    expect(within(card).getByText(`${snap.daily_percent.toFixed(1)}%`)).toBeInTheDocument();
    if (snap.conversation_percent !== null) {
      expect(within(card).getByText(`Conversación: ${snap.conversation_percent}% de $${snap.conversation_limit.toFixed(2)}`)).toBeInTheDocument();
    }
  });

  it("explains the 80% and 100% threshold actions", async () => {
    render(<SettingsView />);
    await selectSection("Costos");
    expect(screen.getByRole("heading", { name: "Qué ocurre al alcanzar los límites" })).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("Respuestas más conservadoras")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("Derivación a una persona")).toBeInTheDocument();
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

  it("composes push settings inside Configuración", async () => {
    render(<SettingsView />);
    await selectSection("Horarios y avisos");
    const push = screen.getByRole("heading", { name: "Notificaciones push" }).closest(".card") as HTMLElement;
    expect(push).toBeInTheDocument();
    expect(within(push).getByText(/correo o whatsapp|activa avisos/i)).toBeInTheDocument();
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
    expect(within(toolsCard).getByText("consultar")).toBeInTheDocument();
    expect(within(toolsCard).getByText("crear visita")).toBeInTheDocument();
    expect(within(toolsCard).getByText("agenda.crear_visita").tagName).toBe("CODE");
    expect(within(toolsCard).getAllByText("Solo lectura")).toHaveLength(2);
    expect(within(toolsCard).getAllByText("Puede escribir")).toHaveLength(2);
    expect(within(toolsCard).getByRole("button", { name: /Operación/ })).toHaveTextContent("2");
    expect(screen.getByText("Cercana, Técnica")).toBeInTheDocument();
    expect(screen.getByText("Atención inicial, Emergencias")).toBeInTheDocument();
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

  it("preserves push permission and fallback states in the composed section", async () => {
    const requestPermission = vi.fn().mockResolvedValue("denied");
    vi.stubGlobal("Notification", { requestPermission });
    vi.stubGlobal("PushManager", function PushManager() {});
    render(<Settings data={settings} state="ready" />);
    await selectSection("Horarios y avisos");
    const push = screen.getByRole("heading", { name: "Notificaciones push" }).closest(".card") as HTMLElement;
    fireEvent.click(within(push).getByRole("button", { name: /activar push/i }));
    await waitFor(() => expect(within(push).getByText(/denegaste/i)).toBeInTheDocument());
    vi.unstubAllGlobals();
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
    const tone = await screen.findByLabelText("Tono");
    await waitFor(() => expect(tone).toHaveValue(settings.tone));
    fireEvent.change(tone, { target: { value: "directo" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar tono" }));

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
    const greetingTab = within(templates).getByRole("tab", { name: "Saludo" });
    const getEditor = (id: string, label: string) => {
      const panel = screen.getAllByRole("tabpanel").find((item) => item.getAttribute("aria-labelledby")?.includes(`trigger-${id}`));
      return within(panel!).getByLabelText(label);
    };
    const greeting = getEditor("greeting", "Saludo");
    fireEvent.change(greeting, { target: { value: "Hola nuevo" } });
    await user.click(within(templates).getByRole("tab", { name: "Despedida" }));
    const farewell = getEditor("farewell", "Despedida");
    fireEvent.change(farewell, { target: { value: "Hasta luego nuevo" } });
    await user.click(within(templates).getByRole("tab", { name: "Fuera de horario" }));
    const outOfHours = getEditor("out_of_hours", "Fuera de horario");
    fireEvent.change(outOfHours, { target: { value: "Estamos cerrados" } });
    expect(greetingTab).toHaveAttribute("aria-selected", "false");
    fireEvent.click(screen.getByRole("button", { name: "Guardar mensajes" }));
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
    fireEvent.click(within(card).getByRole("button", { name: "Guardar horarios" }));
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
    fireEvent.click(await screen.findByRole("button", { name: "Guardar horarios" }));
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
    expect(screen.getByText("2026-08-19")).toBeInTheDocument();
    expect(screen.getByText("Vigente desde 2026-10-01")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Qué ocurre al alcanzar los límites" })).toBeInTheDocument();
    expect(screen.getByText("Respuestas más conservadoras")).toBeInTheDocument();
    expect(screen.getByText("Derivación a una persona")).toBeInTheDocument();
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
