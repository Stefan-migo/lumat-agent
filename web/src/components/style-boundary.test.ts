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
});
