import type { ActiveRun } from "../../types";
import type { ToastTone } from "../primitives/Toast";

export type AssistantRunOutcome = "completed" | "failed" | "cancelled" | "unknown";

export interface AssistantRunAlertDecision {
  run: ActiveRun;
  action: "notify" | "skip";
  tone?: ToastTone;
}

export const assistantRunKey = (run: Pick<ActiveRun, "thread_id" | "run_id">) =>
  `${run.thread_id}:${run.run_id}`;

export function disappearedAssistantRuns(previous: ActiveRun[], current: ActiveRun[]) {
  const currentKeys = new Set(current.map(assistantRunKey));
  return previous.filter((run) => !currentKeys.has(assistantRunKey(run)));
}

export function decideAssistantRunAlerts(
  disappeared: ActiveRun[],
  visibleThreadId: number | null,
  outcomes: ReadonlyMap<string, AssistantRunOutcome>,
): AssistantRunAlertDecision[] {
  return disappeared.map((run) => {
    if (run.thread_id === visibleThreadId) return { run, action: "skip" };
    const outcome = outcomes.get(assistantRunKey(run));
    if (outcome === "completed") return { run, action: "notify", tone: "success" };
    if (outcome === "failed") return { run, action: "notify", tone: "danger" };
    return { run, action: "skip" };
  });
}
