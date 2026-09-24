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

/** CSS specificity as [ids, classes, types]; higher wins, compared left to right. */
function specificity(selector: string): [number, number, number] {
  return [
    selector.match(/#[\w-]+/g)?.length ?? 0,
    selector.match(/\.[\w-]+|\[[^\]]+\]|::?[a-z-]+/g)?.length ?? 0,
    selector.match(/(?:^|[\s>+~])[a-z][\w-]*/gi)?.length ?? 0,
  ];
}

/** True when `candidate` outranks `rival` in the cascade. */
function outranks(candidate: string, rival: string): boolean {
  const left = specificity(candidate);
  const right = specificity(rival);
  for (let i = 0; i < left.length; i += 1) {
    if (left[i] !== right[i]) return left[i] > right[i];
  }
  return false;
}

describe("Icon", () => {
  it("sizes through the token classes, not through the Lucide attributes", () => {
    const { container } = render(<Icon icon={Search} size="sm" />);

    const glyph = container.querySelector("svg")!;
    expect(glyph).toHaveAttribute("aria-hidden", "true");
    expect(glyph).toHaveClass("icon", "icon--sm");
    // Lucide emits width/height="24" as presentational attributes; the stylesheet
    // overrides them, so the .icon rule is what actually pins the size.
    expect(glyph).toHaveAttribute("width", "24");
    expect(primitivesCss).toMatch(
      /\.icon\s*\{[^}]*width:\s*var\(--icon-md\);[^}]*height:\s*var\(--icon-md\);/s,
    );
    expect(primitivesCss).toMatch(
      /\.icon\.icon--sm\s*\{[^}]*width:\s*var\(--icon-sm\);[^}]*height:\s*var\(--icon-sm\);/s,
    );
  });

  it("lets the size modifiers outrank the button and dialog svg pinning rules", () => {
    // Those two rules pin every svg child to --icon-md. The size modifiers must be
    // written as compound selectors so they win instead of being silently beaten.
    const sizeModifiers = [
      ...primitivesCss.matchAll(/^\s*(\.icon\.icon--(?:sm|lg))\s*\{/gm),
    ].map((match) => match[1]);

    expect(sizeModifiers).toEqual([".icon.icon--sm", ".icon.icon--lg"]);
    for (const modifier of sizeModifiers) {
      expect(outranks(modifier, ".btn > svg")).toBe(true);
      expect(outranks(modifier, ".dialog__close > svg")).toBe(true);
    }
  });

  it("keeps the Lucide stroke so the glyph follows the inherited text color", () => {
    const { container } = render(<Icon icon={Search} />);

    expect(container.querySelector("svg")).toHaveAttribute("stroke", "currentColor");
  });

  it("accepts a custom class alongside the size modifier", () => {
    const { container } = render(<Icon icon={Search} className="icon--custom" />);

    expect(container.querySelector("svg")).toHaveClass(
      "icon",
      "icon--md",
      "icon--custom",
    );
  });
});
