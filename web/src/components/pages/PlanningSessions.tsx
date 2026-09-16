import { useCallback, type ReactNode } from "react";
import { getPlanningSession, listPlanningSessions, reopenPlanningSession } from "../../api";
import type { PlanningSession, PlanningSessionDetailResponse, PlanningSessionsResponse } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

function ReadState({ state, detail }: { state: AsyncDataState; detail: boolean }) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title={detail ? "Loading planning session" : "Loading planning sessions"} />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="Planning sessions require administrator access" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={detail ? "We could not load the planning session" : "We could not load the planning sessions"} detail="Check your access and try again." />;
  return null;
}

export function PlanningSessions({ sessionSlug, onOpenSession, onOpenThread, data, state, sectionTabs }: { sessionSlug?: string; onOpenSession?: (slug: string) => void; onOpenThread?: (id: number) => void; data?: PlanningSessionsResponse; state?: AsyncDataState; sectionTabs?: ReactNode }) {
  const list = useAsyncData(useCallback(() => listPlanningSessions(), []), data === undefined);
  const detail = useAsyncData(useCallback(() => getPlanningSession(sessionSlug!), [sessionSlug]), sessionSlug !== undefined);
  if (sessionSlug) {
    const body = detail.data as PlanningSessionDetailResponse | null;
    const session = body?.session;
    const reopen = async () => {
      if (!session) return;
      await reopenPlanningSession(session.slug);
      onOpenThread?.(session.thread_id);
    };
    return <PageFrame title={session?.topic ?? "Planning session"} meta={session ? <span>Thread {session.thread_id} · {session.status}</span> : undefined} state={<ReadState state={detail.state} detail />}>
      {sectionTabs}
      <Button variant="secondary" onClick={() => window.history.back()}>Back to planning sessions</Button>
      {session?.status === "closed" ? <Button onClick={() => void reopen()}>Reopen session</Button> : null}
      {body ? <>
        <section aria-labelledby="planning-decisions"><h2 id="planning-decisions">Decisions</h2>{body.decisions.length ? <ul>{body.decisions.map((decision) => <li key={decision.id}>{decision.contenido}</li>)}</ul> : <p>No decisions recorded.</p>}</section>
        <section aria-labelledby="planning-report"><h2 id="planning-report">Closing report</h2><p>{body.report?.contenido ?? "No closing report is available."}</p></section>
      </> : null}
    </PageFrame>;
  }
  const result = data ?? list.data;
  const currentState = state ?? (data ? "ready" : list.state);
  const sessions = result?.sessions ?? [];
  return <PageFrame title="Planning sessions" meta={<span>Durable Cortex planning work</span>} state={<ReadState state={currentState} detail={false} />}>
    {sectionTabs}
    {currentState === "ready" && sessions.length === 0 ? <EmptyState title="No planning sessions" description="Planning sessions will appear here after an administrator opens one." /> : null}
    {sessions.length > 0 ? <div className="ai-agent-grammar__thread-area" aria-label="Planning session list"><div className="ai-agent-grammar__bubbles">{sessions.map((item: PlanningSession) => <button type="button" className="ai-agent-grammar__bubble" key={item.slug} onClick={() => onOpenSession?.(item.slug)}><strong>{item.topic}</strong><span>Thread {item.thread_id}</span><small>{item.status}</small></button>)}</div></div> : null}
  </PageFrame>;
}
