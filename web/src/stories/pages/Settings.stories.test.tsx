import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { settings } from "./_shared/mockData/settings";
import { SettingsView } from "./Settings.stories";

describe("Settings page story (T5.3, R-PRD-PG-6)", () => {
  it("renders the 'Settings' page title via PageHeader", () => {
    render(<SettingsView />);
    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
  });

  it("renders a FlashMessage", () => {
    render(<SettingsView />);
    expect(document.querySelector(".flash-message")).toBeInTheDocument();
  });

  it("renders the 6 form cards (SS-1..SS-5)", () => {
    render(<SettingsView />);
    expect(screen.getByRole("heading", { name: "Scope rules" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Emergency keywords" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tone" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spend limits" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Meta pricing" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Current spend" })).toBeInTheDocument();
  });

  it("renders the scope-rules textarea with category=mode lines", () => {
    render(<SettingsView />);
    const rulesTextarea = screen.getByLabelText(/scope rules/i) as HTMLTextAreaElement;
    const lines = rulesTextarea.value.split("\n").filter((l) => l.length > 0);
    expect(lines.length).toBeGreaterThan(0);
    const modePattern = /^([a-z_]+)=(bot_resolve|always_escalate)$/;
    for (const line of lines) {
      expect(line).toMatch(modePattern);
    }
  });

  it("renders the emergency keywords textarea with one keyword per line", () => {
    render(<SettingsView />);
    const keywordsTextarea = screen.getByLabelText(/keywords/i) as HTMLTextAreaElement;
    const lines = keywordsTextarea.value.split("\n").filter((l) => l.length > 0);
    expect(lines.length).toBe(settings.keywords.length);
    for (const kw of settings.keywords) {
      expect(lines).toContain(kw);
    }
  });

  it("renders the tone input with the current tone value", () => {
    render(<SettingsView />);
    const toneInput = screen.getByLabelText(/tone/i) as HTMLInputElement;
    expect(toneInput.value).toBe(settings.tone);
  });

  it("renders spend-limit inputs (conversation + daily) with current values", () => {
    render(<SettingsView />);
    const conv = screen.getByLabelText(/conversation limit/i) as HTMLInputElement;
    const daily = screen.getByLabelText(/daily limit/i) as HTMLInputElement;
    expect(Number(conv.value)).toBe(settings.conversation_limit);
    expect(Number(daily.value)).toBe(settings.daily_limit);
  });

  it("renders the meta pricing input with service-message cost", () => {
    render(<SettingsView />);
    const cost = screen.getByLabelText(/service-message cost/i) as HTMLInputElement;
    expect(Number(cost.value)).toBe(settings.meta_cost);
  });

  it("renders the current spend table with date, daily spend, limit, % and muted mode line", () => {
    render(<SettingsView />);
    const table = screen.getByRole("table");
    const snap = settings.snapshot;
    expect(table).toBeInTheDocument();
    expect(screen.getAllByText(snap.date).length).toBeGreaterThan(0);
    expect(screen.getAllByText(`$${snap.daily_spend.toFixed(4)}`).length).toBeGreaterThan(0);
    expect(screen.getAllByText(`$${snap.daily_limit.toFixed(2)}`).length).toBeGreaterThan(0);
    expect(screen.getAllByText(`${snap.daily_percent.toFixed(1)}%`).length).toBeGreaterThan(0);
    expect(screen.getAllByText(snap.mode).length).toBeGreaterThan(0);
  });
});
