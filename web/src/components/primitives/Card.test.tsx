import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

const primitives = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");

describe("Card (T8.2)", () => {
  it("renders an optional title and its content", () => {
    render(<Card title="Client">Camila Soto</Card>);
    expect(screen.getByRole("heading", { name: "Client" })).toBeInTheDocument();
    expect(screen.getByText("Camila Soto")).toBeInTheDocument();
  });

  it("uses a flat non-white surface and hairline separation", () => {
    const card = primitives.match(/\.card\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(card).toMatch(/background:\s*var\(--surface\)/);
    expect(card).toMatch(/border:\s*1px solid var\(--border\)/);
    expect(card).toMatch(/border-radius:\s*var\(--radius-lg\)/);
    expect(card).not.toMatch(/box-shadow:/);
  });
});
