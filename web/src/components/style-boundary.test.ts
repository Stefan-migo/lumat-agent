import { readdirSync, readFileSync } from "node:fs";
import { extname, join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const sourceRoot = resolve(process.cwd(), "src");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    if (path.includes(".test.")) return [];
    return [path].filter((file) => [".ts", ".tsx"].includes(extname(file)));
  });
}

describe("stylesheet boundary", () => {
  it("rejects JSX style elements in source files", () => {
    const offenders = sourceFiles(sourceRoot)
      .filter((file) => /<style[\s>]/.test(readFileSync(file, "utf8")))
      .map((file) => relative(process.cwd(), file));

    expect(offenders).toEqual([]);
  });

  it("keeps fully migrated components free of static inline styles", () => {
    const componentFiles = [
      "src/components/domain/ClientMemories.tsx",
    ];
    const offenders = componentFiles.filter((file) =>
      /style=\{\{/.test(readFileSync(join(process.cwd(), file), "utf8")),
    );

    expect(offenders).toEqual([]);
  });

  it("keeps the migrated icon surfaces free of inline svg literals", () => {
    const iconFiles = [
      "src/components/domain/PanelShell.tsx",
      "src/components/pages/Dashboard.tsx",
      "src/components/pages/AgentChat.tsx",
      "src/components/primitives/SearchInput.tsx",
      "src/components/primitives/Dialog.tsx",
    ];
    const offenders = iconFiles.filter((file) =>
      /<svg[\s>]/.test(readFileSync(join(process.cwd(), file), "utf8")),
    );

    expect(offenders).toEqual([]);
  });
});
