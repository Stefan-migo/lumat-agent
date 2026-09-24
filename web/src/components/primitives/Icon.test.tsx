import { render } from "@testing-library/react";
import { Search } from "lucide-react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Icon } from "./Icon";

const primitivesCss = readFileSync(
  join(process.cwd(), "src", "components", "primitives", "primitives.css"),
  "utf8",
);

describe("Icon", () => {
  it("renders a decorative Lucide glyph on the declared size scale", () => {
    const { container } = render(<Icon icon={Search} size="sm" />);

    const glyph = container.querySelector("svg")!;
    expect(glyph).toHaveAttribute("aria-hidden", "true");
    expect(glyph).toHaveClass("icon", "icon--sm");
    expect(glyph).toHaveAttribute("width", "24");
    expect(glyph).toHaveAttribute("height", "24");
    expect(primitivesCss).toMatch(
      /\.icon\.icon--sm\s*\{[^}]*width:\s*var\(--icon-sm\);[^}]*height:\s*var\(--icon-sm\);/s,
    );
  });

  it("keeps the small size when nested in a button", () => {
    render(
      <button className="btn" type="button">
        <Icon icon={Search} size="sm" />
      </button>,
    );

    expect(primitivesCss).toMatch(
      /\.icon\.icon--sm\s*\{[^}]*width:\s*var\(--icon-sm\);[^}]*height:\s*var\(--icon-sm\);/s,
    );
  });

  it("inherits the current text color and accepts a custom class", () => {
    const { container } = render(<Icon icon={Search} className="icon--custom" />);

    expect(container.querySelector("svg")).toHaveClass(
      "icon",
      "icon--md",
      "icon--custom",
    );
    expect(primitivesCss).toMatch(
      /\.icon\s*\{[^}]*color:\s*currentColor;/s,
    );
  });
});
