import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const componentsRoot = resolve(process.cwd(), "src", "components");
const storiesRoot = resolve(process.cwd(), "src", "stories");
const allowedImporters = new Set([
  "src/components/shared/closure.test.tsx",
  "src/components/shared/helpers.test.tsx",
]);

function componentFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return componentFiles(path);
    return [path].filter((file) => [".ts", ".tsx"].includes(extname(file)));
  });
}

function resolveSourceImport(importer: string, specifier: string): string | undefined {
  if (!specifier.startsWith(".")) return undefined;

  const base = resolve(join(importer, ".."), specifier);
  const candidates = [base, `${base}.ts`, `${base}.tsx`, join(base, "index.ts"), join(base, "index.tsx")];
  return candidates.find((candidate) => {
    try {
      return statSync(candidate).isFile();
    } catch {
      return false;
    }
  });
}

function storyImporters(): string[] {
  const importPattern = /\bimport\s+(?:(?:type\s+)?[\s\S]*?\s+from\s+)?["']([^"']+)["']|\bimport\s*\(\s*["']([^"']+)["']\s*\)/g;
  return componentFiles(componentsRoot).flatMap((file) => {
    const source = readFileSync(file, "utf8");
    const importers = new Set<string>();
    for (const match of source.matchAll(importPattern)) {
      const imported = match[1] ?? match[2];
      const resolved = imported && resolveSourceImport(file, imported);
      if (resolved?.startsWith(`${storiesRoot}/`)) {
        importers.add(relative(process.cwd(), file));
      }
    }
    return [...importers];
  });
}

describe("component ownership boundary", () => {
  it("rejects component imports resolving under stories except the two compatibility tests", () => {
    const violations = storyImporters().filter((importer) => !allowedImporters.has(importer));
    expect(violations).toEqual([]);
  });
});
