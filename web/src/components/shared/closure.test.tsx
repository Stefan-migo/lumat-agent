import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { PageFrame } from "./PageFrame";
import { StateMessage } from "./StateMessage";
import { caseStatusLabel, caseStatusTone } from "./toneMaps";
import { PageFrame as StoryPageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage as StoryStateMessage } from "../../stories/pages/_shared/StateMessage";
import * as storyToneMaps from "../../stories/pages/_shared/toneMaps";

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    return statSync(path).isDirectory() ? sourceFiles(path) : path.endsWith(".ts") || path.endsWith(".tsx") ? [path] : [];
  });
}

describe("production shared closure", () => {
  it("keeps PageFrame, StateMessage, and tone maps out of stories", () => {
    const source = ["pages", "domain", "primitives"].flatMap((directory) =>
      sourceFiles(join(process.cwd(), "src/components", directory)).flatMap((path) => readFileSync(path, "utf8").split("\n")),
    );

    expect(source.some((line) => line.includes("stories/pages/_shared"))).toBe(false);
  });

  it("renders promoted page and state contracts", () => {
    render(
      <PageFrame title="Clients" meta="Window" state={<StateMessage tone="warning" role="status" title="Stale data" />}>
        <p>Content</p>
      </PageFrame>,
    );

    expect(screen.getByRole("heading", { name: "Clients" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Stale data");
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("keeps story wrappers compatible with promoted contracts", () => {
    render(<StoryPageFrame title="Story clients"><StoryStateMessage tone="info" role="status" title="Ready" /></StoryPageFrame>);

    expect(screen.getByRole("heading", { name: "Story clients" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Ready");
    expect(storyToneMaps.caseStatusLabel("cerrado")).toBe(caseStatusLabel("cerrado"));
    expect(storyToneMaps.caseStatusTone("escalado")).toBe(caseStatusTone("escalado"));
  });
});
