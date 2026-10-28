import { describe, expect, it } from "vitest";
import type { ActiveRun } from "../../types";
import { decideAssistantRunAlerts, disappearedAssistantRuns, assistantRunKey } from "./assistantRunAlerts";

const run = (thread_id: number, run_id: string): ActiveRun => ({
  thread_id,
  run_id,
  title: `Hilo ${thread_id}`,
  proyecto: "default",
  agent: "assistant",
  stage: "streaming",
  updated_at: null,
});

describe("assistant run alerts", () => {
  it("notifies for a disappeared run outside the visible thread", () => {
    const previous = [run(4, "run-4")];
    const disappeared = disappearedAssistantRuns(previous, []);
    expect(disappeared).toEqual(previous);
    expect(decideAssistantRunAlerts(disappeared, null, new Map([[assistantRunKey(previous[0]), "completed"]]))).toEqual([
      { run: previous[0], action: "notify", tone: "success" },
    ]);
  });

  it("skips a disappeared run whose thread is currently visible", () => {
    const currentRun = run(4, "run-4");
    const disappeared = disappearedAssistantRuns([currentRun], []);
    expect(decideAssistantRunAlerts(disappeared, 4, new Map([[assistantRunKey(currentRun), "failed"]]))).toEqual([
      { run: currentRun, action: "skip" },
    ]);
  });

  it("does not notify when a run first appears", () => {
    expect(disappearedAssistantRuns([], [run(4, "run-4")])).toEqual([]);
  });

  it("does not notify for an empty-to-empty transition", () => {
    expect(disappearedAssistantRuns([], [])).toEqual([]);
  });

  it("uses danger for failure and success for completion", () => {
    const completed = run(4, "run-complete");
    const failed = run(5, "run-fail");
    const disappeared = disappearedAssistantRuns([completed, failed], []);
    expect(decideAssistantRunAlerts(disappeared, null, new Map([
      [assistantRunKey(completed), "completed"],
      [assistantRunKey(failed), "failed"],
    ]))).toEqual([
      { run: completed, action: "notify", tone: "success" },
      { run: failed, action: "notify", tone: "danger" },
    ]);
  });
});
