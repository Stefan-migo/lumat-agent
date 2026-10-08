import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Settings as SettingsData } from "../../types";
import { Settings } from "./Settings";

const settings = (overrides: Partial<SettingsData> = {}): SettingsData => ({
  scope_rules: { general: "bot_resolve" }, keywords: ["gas"], tone: "cercano",
  messages: { greeting: "Hola", cannot_answer: "No sé", clarification: "¿Cuál?", farewell: "Chao", out_of_hours: "Cerrado" },
  hours: { timezone: "America/Santiago", schedule: [{ days: [1], open: "09:00", close: "18:00" }] },
  conversation_limit: 4, daily_limit: 20, meta_cost: 0.05,
  snapshot: { date: "2026-10-08", conversation_spend: 1, conversation_limit: 4, conversation_percent: 25, daily_spend: 2, daily_limit: 20, daily_percent: 10, mode: "normal" },
  ...overrides,
});
const capabilities = { tools: [], personas: [], prompts: [], kb_available: true, memory_available: true };

describe("Settings", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders five sections and selects Agente by default", () => {
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Agente", "Mensajes", "Horarios y avisos", "Costos", "Capacidades"]);
    expect(screen.getByRole("tab", { name: "Agente" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
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

  it("groups, searches, and filters capability tools from the available payload fields", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={{
      tools: [
        { name: "kb.retrieve", description: "Busca documentos", read_only: true, write: false },
        { name: "kb.index", description: "Indexa documentos", read_only: false, write: true },
        { name: "plain_tool", description: "Herramienta general", read_only: true, write: false },
      ], personas: ["Cercana"], prompts: ["Atención inicial"], kb_available: true, memory_available: false,
    }} />);
    await user.click(screen.getByRole("tab", { name: "Capacidades" }));
    expect(screen.getByRole("heading", { name: "Herramientas del asistente" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /Conocimiento y memoria/ })).toBeVisible();
    expect(screen.getByText("retrieve")).toBeInTheDocument();
    expect(screen.getByText("kb.retrieve").tagName).toBe("CODE");
    expect(screen.getAllByText("Solo lectura")).toHaveLength(3);
    await user.selectOptions(screen.getByLabelText("Acceso"), "write");
    expect(screen.getByText("index")).toBeInTheDocument();
    expect(screen.queryByText("retrieve")).toBeNull();
    fireEvent.change(screen.getByLabelText("Buscar herramientas"), { target: { value: "no existe" } });
    await waitFor(() => expect(screen.getByText("No hay herramientas que coincidan con la búsqueda.")).toBeInTheDocument());
    expect(screen.getByText("Disponible")).toBeInTheDocument();
    expect(screen.getByText("No disponible")).toBeInTheDocument();
  });
});
