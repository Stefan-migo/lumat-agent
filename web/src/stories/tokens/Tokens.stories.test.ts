import { describe, it, expect } from "vitest";
import { groupToken } from "./Tokens.stories";

describe("Tokens page grouping (D8 ordered first-match rules)", () => {
  it("resolves the --text color vs --text-* scale collision (exact match first)", () => {
    expect(groupToken("--text")).toBe("Color (text)");
    expect(groupToken("--text-muted")).toBe("Color (text)");
    expect(groupToken("--text-xs")).toBe("Typography (scale)");
    expect(groupToken("--text-base")).toBe("Typography (scale)");
    expect(groupToken("--text-2xl")).toBe("Typography (scale)");
  });

  it("routes every documented group by its rule", () => {
    expect(groupToken("--primary-500")).toBe("Color");
    expect(groupToken("--brand-lime")).toBe("Color (brand)");
    expect(groupToken("--brand-cyan")).toBe("Color (brand)");
    expect(groupToken("--danger-border")).toBe("Color (semantic)");
    expect(groupToken("--danger")).toBe("Color (semantic)");
    expect(groupToken("--success")).toBe("Color (semantic)");
    expect(groupToken("--warning")).toBe("Color (semantic)");
    expect(groupToken("--info")).toBe("Color (semantic)");
    expect(groupToken("--surface")).toBe("Color (neutrals)");
    expect(groupToken("--border-strong")).toBe("Color (neutrals)");
    expect(groupToken("--font-sans")).toBe("Typography (font/leading/weight)");
    expect(groupToken("--leading-normal")).toBe("Typography (font/leading/weight)");
    expect(groupToken("--weight-bold")).toBe("Typography (font/leading/weight)");
    expect(groupToken("--space-4")).toBe("Spacing");
    expect(groupToken("--radius-md")).toBe("Radius");
    expect(groupToken("--shadow-3")).toBe("Shadow");
    expect(groupToken("--duration-fast")).toBe("Motion");
    expect(groupToken("--ease-out")).toBe("Motion");
    expect(groupToken("--focus-ring")).toBe("Focus");
    expect(groupToken("--bp-lg")).toBe("Breakpoints");
    expect(groupToken("--z-modal")).toBe("z-index");
    // Anchored families: lookalike tokens must NOT be swallowed by a prefix.
    expect(groupToken("--dangerous")).toBe("Other");
    expect(groupToken("--successor")).toBe("Other");
    expect(groupToken("--border-radius")).toBe("Other");
  });

  it("never silently drops unknown tokens (Other fallback)", () => {
    expect(groupToken("--some-future-token")).toBe("Other");
  });
});
