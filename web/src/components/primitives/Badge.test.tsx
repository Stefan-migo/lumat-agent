import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Badge } from "./Badge";

describe("Badge (T8.3)", () => {
  it("exposes its label and semantic tone", () => {
    render(<Badge tone="danger">Escalated</Badge>);
    expect(screen.getByText("Escalated")).toHaveAttribute(
      "data-tone",
      "danger",
    );
  });

  it("uses semantic foregrounds and tints while status borders remain decorative", () => {
    const css = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");
    expect(css).toMatch(/\.badge--neutral\s*\{[^}]*color:\s*var\(--text-muted\)[^}]*background:\s*var\(--surface-subtle\)/s);
    expect(css).toMatch(/\.badge--success\s*\{[^}]*color:\s*var\(--success\)[^}]*background:\s*var\(--success-bg\)[^}]*border-color:\s*var\(--success-border\)/s);
    expect(css).toMatch(/\.badge--warning\s*\{[^}]*color:\s*var\(--warning\)[^}]*background:\s*var\(--warning-bg\)[^}]*border-color:\s*var\(--warning-border\)/s);
    expect(css).toMatch(/\.badge--danger\s*\{[^}]*color:\s*var\(--danger\)[^}]*background:\s*var\(--danger-bg\)[^}]*border-color:\s*var\(--danger-border\)/s);
  });
});
