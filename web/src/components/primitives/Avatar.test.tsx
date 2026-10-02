import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { Avatar } from "./Avatar";

const primitives = readFileSync(join(process.cwd(), "src/components/primitives/primitives.css"), "utf8");

describe("Avatar (T8.5)", () => {
  it("uses initials when no image source is provided", () => {
    render(<Avatar name="Camila Soto" />);
    expect(screen.getByText("CS")).toBeInTheDocument();
  });

  it("renders the named image when a source is provided", () => {
    render(<Avatar name="Camila Soto" src="/camila.png" />);
    expect(screen.getByRole("img", { name: "Camila Soto" })).toHaveAttribute(
      "src",
      "/camila.png",
    );
  });

  it("uses semantic non-white avatar roles", () => {
    const avatar = primitives.match(/\.avatar\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(avatar).toMatch(/background:\s*var\(--border\)/);
    expect(avatar).toMatch(/color:\s*var\(--text\)/);
  });
});
