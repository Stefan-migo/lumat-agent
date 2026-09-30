import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("PageFrame CSS contract", () => {
  it("keeps a directly nested page action from stretching across the content grid", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.page-frame__content\s*>\s*\.btn\s*\{[^}]*justify-self:\s*start/s);
  });

  it("keeps the page frame on the semantic canvas and the heading accent decorative", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.page-frame\s*\{[^}]*font-family:\s*var\(--font-ui\)/s);
    expect(css).toMatch(/\.page-header::before\s*\{[^}]*background:\s*var\(--lime-700\)/s);
  });
});
