import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    fireEvent.click(screen.getByText("Sintaxis avanzada · categoría=mode"));
    expect(screen.getByText(/una regla por línea con categoría=mode, donde mode es bot_resolve o always_escalate/)).toBeInTheDocument();
    const rules = screen.getByLabelText("Reglas de alcance");
    expect(rules).toHaveValue("general=bot_resolve");
    expect(rules).toBeEnabled();
  });

  it("switches sections and keeps the mobile select on the same active state", async () => {
    const user = userEvent.setup();
    render(<Settings data={settings()} state="ready" capabilities={capabilities} />);
    await user.click(screen.getByRole("tab", { name: "Mensajes" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Mensajes del asistente" })).toBeInTheDocument());
    const sectionSelect = screen.getByLabelText("Sección");
    expect(sectionSelect).toHaveValue("messages");
    fireEvent.change(sectionSelect, { target: { value: "costs" } });
    expect(screen.getByRole("tab", { name: "Costos" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Gasto actual" })).toBeInTheDocument();
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
    const tone = screen.getByLabelText("Tono");
    fireEvent.change(tone, { target: { value: "" } });
    expect(screen.getByRole("button", { name: "Guardar tono" })).toBeDisabled();
    fireEvent.change(tone, { target: { value: "formal" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar tono" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Guardar tono" })).toBeDisabled());
  });
});
