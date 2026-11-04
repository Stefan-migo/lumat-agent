import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Structural guard for `web/DESIGN_SYSTEM.md`.
 *
 * Tests do not read CSS, so before this file a section could ship to production
 * as bare `<ul>`/`<li>` markup with no classes and every suite stayed green. That
 * is exactly how the "Visitas vencidas" band reached production undesigned: the
 * markup existed, the styles never did, and no check asked whether the surface
 * had a grammar.
 *
 * The rule this pins is the normative sentence in `web/DESIGN_SYSTEM.md`
 * ("Agenda · visitas vencidas"): a section that presents a list of entities
 * follows the grammar of the page it sits in and declares its own block classes.
 * A list container with no `className` is an unfinished surface.
 *
 * The baseline records the debt that already existed when the check was written.
 * It fails in both directions on purpose: a new bare list fails, and an entry
 * whose surface has been styled fails until the entry is deleted — so the file
 * can only shrink, never quietly stay stale. Same pattern as
 * `docs/kb/drift-baseline.json`.
 */

const SURFACES = ["pages", "shared"];

function componentFiles(dir: string): string[] {
  const root = join(process.cwd(), "src/components", dir);
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const path = join(root, entry.name);
    if (entry.isDirectory()) return componentFiles(join("..", dir, entry.name));
    if (!entry.name.endsWith(".tsx")) return [];
    if (entry.name.includes(".test.") || entry.name.includes(".stories.")) return [];
    return [path];
  }).sort();
}

/** Every `<ul>`, `<ol>` and `<table>` open tag in the file, matched across lines. */
function listContainers(source: string): string[] {
  return source.match(/<(ul|ol|table)(\s[^>]*)?>/g) ?? [];
}

function violations(): string[] {
  const found: string[] = [];
  for (const file of SURFACES.flatMap(componentFiles)) {
    const source = readFileSync(file, "utf8");
    for (const tag of listContainers(source)) {
      if (tag.includes("className")) continue;
      const relative = file.replace(join(process.cwd(), "src/components") + "/", "");
      found.push(`${relative}: ${tag.replace(/\s+/g, " ")}`);
    }
  }
  return found.sort();
}

describe("panel surfaces declare their list grammar (DESIGN_SYSTEM.md)", () => {
  const baseline: { entries: { entry: string }[] } = JSON.parse(
    readFileSync(join(process.cwd(), "src/components/panelSurfaces.baseline.json"), "utf8"),
  );
  const known = baseline.entries.map((item) => item.entry);
  const found = violations();

  it("scans the surface directories, so an empty scan cannot pass silently", () => {
    expect(SURFACES.flatMap(componentFiles).length).toBeGreaterThan(30);
  });

  it("has no list container without a className outside the recorded debt", () => {
    const added = found.filter((entry) => !known.includes(entry));
    expect(added, `new list containers with no classes:\n${added.join("\n")}`).toEqual([]);
  });

  it("has no stale baseline entry, so styled surfaces leave the list", () => {
    const stale = known.filter((entry) => !found.includes(entry));
    expect(stale, `baseline entries whose surface is styled now — delete them:\n${stale.join("\n")}`).toEqual([]);
  });
});
