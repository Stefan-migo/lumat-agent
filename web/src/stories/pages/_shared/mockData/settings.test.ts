import { describe, expect, it } from "vitest";
import { settings } from "./settings";

/** Settings serializer keys from GET /settings in app/panel/api/routes/settings.py
 *  (R-PRD-PG-3): {scope_rules, keywords, tone, messages, hours, conversation_limit,
 *  daily_limit, meta_cost, snapshot}. */
const SETTINGS_KEYS = [
  "conversation_limit",
  "daily_limit",
  "hours",
  "keywords",
  "meta_cost",
  "messages",
  "scope_rules",
  "snapshot",
  "tone",
  "templates",
].sort();

/** SpendSnapshot keys from spend_snapshot() in app/services/costs.py (SS-4). */
const SNAPSHOT_KEYS = [
  "conversation_limit",
  "conversation_percent",
  "conversation_spend",
  "daily_limit",
  "daily_percent",
  "daily_spend",
  "date",
  "mode",
].sort();

describe("Settings mock (settings.ts)", () => {
  it("exports a Settings object with all serializer keys (R-PRD-PG-3)", () => {
    expect(Object.keys(settings).sort()).toEqual(SETTINGS_KEYS);
  });

  it("keeps snapshot shape fidelity: spend_snapshot keys", () => {
    expect(Object.keys(settings.snapshot).sort()).toEqual(SNAPSHOT_KEYS);
  });

  it("holds a scope_rules map of {category: mode} with valid modes", () => {
    const modes = ["bot_resolve", "always_escalate"];
    expect(Object.keys(settings.scope_rules).length).toBeGreaterThan(0);
    for (const mode of Object.values(settings.scope_rules)) {
      expect(modes).toContain(mode);
    }
  });

  it("lists emergency keywords as strings", () => {
    expect(settings.keywords.length).toBeGreaterThan(0);
    for (const kw of settings.keywords) {
      expect(typeof kw).toBe("string");
    }
  });

  it("holds tone, conversation_limit, daily_limit, meta_cost as numbers/strings", () => {
    expect(typeof settings.tone).toBe("string");
    expect(settings.conversation_limit).toBeGreaterThan(0);
    expect(settings.daily_limit).toBeGreaterThan(0);
    expect(settings.meta_cost).toBeGreaterThan(0);
  });

  it("pins the standard message keys", () => {
    expect(Object.keys(settings.messages).sort()).toEqual([
      "cannot_answer", "clarification", "farewell", "greeting", "out_of_hours",
    ]);
  });

  it("records a valid ISO date in snapshot.date", () => {
    expect(new Date(settings.snapshot.date).toString()).not.toBe("Invalid Date");
  });

  it("covers a snapshot with a real % and mode (normal/conservative/blocked)", () => {
    expect(["normal", "conservative", "blocked"]).toContain(settings.snapshot.mode);
    expect(settings.snapshot.daily_percent).toBeGreaterThan(0);
  });
});
