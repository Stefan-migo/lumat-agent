import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { settings } from "./_shared/mockData/settings";
import { SettingsView } from "./Settings.stories";

describe("Settings page story (SS-1..SS-5 / S6 DS-UI-COPY/STATES/TABLES)", () => {
  it("renders the Spanish page title 'Configuración'", () => {
    render(<SettingsView />);
    expect(screen.getByRole("heading", { name: "Configuración" })).toBeInTheDocument();
  });

  it("renders groups by business consequence with approved Spanish card titles", () => {
    render(<SettingsView />);
    expect(screen.getByRole("heading", { name: "Alcance del agente" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Detección de emergencias" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tono" })).toBeInTheDocument();
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

  it("renders one save action per independently persisted group", () => {
    render(<SettingsView />);
    const agentCard = screen.getByRole("heading", { name: "Alcance del agente" }).closest(".card") as HTMLElement;
    const emergencyCard = screen.getByRole("heading", { name: "Detección de emergencias" }).closest(".card") as HTMLElement;
    const toneCard = screen.getByRole("heading", { name: "Tono" }).closest(".card") as HTMLElement;
    const limitsCard = screen.getByRole("heading", { name: "Límites de gasto" }).closest(".card") as HTMLElement;
    const pricingCard = screen.getByRole("heading", { name: "Precio Meta" }).closest(".card") as HTMLElement;
    expect(within(agentCard).getByRole("button", { name: "Guardar alcance" })).toBeInTheDocument();
    expect(within(emergencyCard).getByRole("button", { name: "Guardar palabras clave" })).toBeInTheDocument();
    expect(within(toneCard).getByRole("button", { name: "Guardar tono" })).toBeInTheDocument();
    expect(within(limitsCard).getByRole("button", { name: "Guardar límites" })).toBeInTheDocument();
    expect(within(pricingCard).getByRole("button", { name: "Guardar precio" })).toBeInTheDocument();
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

  it("renders the tone input with the current tone value and plain-Spanish effect", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Tono" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/respuestas del agente/i)).toBeInTheDocument();
    const toneInput = within(card).getByLabelText(/tono/i) as HTMLInputElement;
    expect(toneInput.value).toBe(settings.tone);
  });

  it("renders spend-limit inputs (conversation + daily) with plain-Spanish effect before them", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Límites de gasto" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/al 80% el agente se vuelve más conservador/i)).toBeInTheDocument();
    expect(within(card).getByText(/al 100% se detienen las llamadas/i)).toBeInTheDocument();
    const conv = within(card).getByLabelText(/límite por conversación/i) as HTMLInputElement;
    const daily = within(card).getByLabelText(/límite diario/i) as HTMLInputElement;
    expect(Number(conv.value)).toBe(settings.conversation_limit);
    expect(Number(daily.value)).toBe(settings.daily_limit);
  });

  it("renders the Meta pricing input with service-message cost and plain-Spanish effect", () => {
    render(<SettingsView />);
    const card = screen.getByRole("heading", { name: "Precio Meta" }).closest(".card") as HTMLElement;
    expect(within(card).getByText(/costo por mensaje de servicio/i)).toBeInTheDocument();
    const cost = within(card).getByLabelText(/costo por mensaje/i) as HTMLInputElement;
    expect(Number(cost.value)).toBe(settings.meta_cost);
  });

  it("renders current spend via a numeric DataTable with tabular/right-aligned comparable numbers (DS-UI-TABLES)", () => {
    render(<SettingsView />);
    const table = screen.getByRole("table");
    const snap = settings.snapshot;
    expect(table).toBeInTheDocument();
    // Headers in Spanish
    expect(within(table).getByText(/fecha/i)).toBeInTheDocument();
    expect(within(table).getByText(/gasto diario/i)).toBeInTheDocument();
    expect(within(table).getByText(/límite diario/i)).toBeInTheDocument();
    expect(within(table).getByText(/% del límite/i)).toBeInTheDocument();
    // The numeric cells carry tabular numerals (font-style numeric) so they align.
    const spendCell = within(table).getByText(`$${snap.daily_spend.toFixed(4)}`);
    expect(spendCell.style.fontVariantNumeric).toBe("tabular-nums");
    const limitCell = within(table).getByText(`$${snap.daily_limit.toFixed(2)}`);
    expect(limitCell.style.fontVariantNumeric).toBe("tabular-nums");
    const pctCell = within(table).getByText(`${snap.daily_percent.toFixed(1)}%`);
    expect(pctCell.style.fontVariantNumeric).toBe("tabular-nums");
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
});
