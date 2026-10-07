import { useCallback, useState, type ReactNode } from "react";
import { ApiError, getPlanningSession, listPlanningSessions, reopenPlanningSession } from "../../api";
import type { PlanningSessionDetailResponse, PlanningSessionsResponse } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { EmptyState } from "../shared/EmptyState";
import { DataTable, tabularNum } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { memoryStatusLabel, memoryStatusTone, sessionStatusLabel, sessionStatusTone } from "../shared/toneMaps";

const TIMESTAMP_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" });

function formatTimestamp(value: string | null): string | null {
  return value ? TIMESTAMP_FORMAT.format(new Date(value)) : null;
}

function ReadState({ state, detail }: { state: AsyncDataState; detail: boolean }) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title={detail ? "Cargando la sesión de planificación" : "Cargando las sesiones de planificación"} />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="Las sesiones de planificación requieren acceso de administrador" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={detail ? "No pudimos cargar la sesión de planificación" : "No pudimos cargar las sesiones de planificación"} detail="Revisa tu acceso e inténtalo nuevamente." />;
  return null;
}

export function PlanningSessions({ sessionSlug, onOpenSession, onOpenThread, data, state, sectionTabs }: { sessionSlug?: string; onOpenSession?: (slug: string) => void; onOpenThread?: (id: number) => void; data?: PlanningSessionsResponse; state?: AsyncDataState; sectionTabs?: ReactNode }) {
  const list = useAsyncData(useCallback(() => listPlanningSessions(), []), data === undefined);
  const detail = useAsyncData(useCallback(() => getPlanningSession(sessionSlug!), [sessionSlug]), sessionSlug !== undefined);
  // Declared before the detail early-return so the hook order stays stable.
  const [reopening, setReopening] = useState(false);
  const [reopenError, setReopenError] = useState<string | null>(null);
  if (sessionSlug) {
    const body = detail.data as PlanningSessionDetailResponse | null;
    const session = body?.session;
    const reopen = async () => {
      if (!session) return;
      setReopening(true);
      setReopenError(null);
      try {
        await reopenPlanningSession(session.slug);
        onOpenThread?.(session.thread_id);
      } catch (error) {
        setReopenError(error instanceof ApiError ? error.detail : "No pudimos completar la acción.");
      } finally {
        setReopening(false);
      }
    };
    const opened = formatTimestamp(session?.opened_at ?? null);
    const closed = formatTimestamp(session?.closed_at ?? null);
    return <PageFrame title={session?.topic ?? "Sesión de planificación"} meta={session ? `Hilo ${session.thread_id} · ${sessionStatusLabel(session.status)}${opened ? ` · Apertura: ${opened}` : ""}${closed ? ` · Cierre: ${closed}` : ""}` : "Detalle de la sesión"} actions={<><Button variant="secondary" onClick={() => window.history.back()}>Volver a las sesiones de planificación</Button>{session?.status === "closed" ? <Button disabled={reopening} onClick={() => void reopen()}>Reabrir sesión</Button> : null}</>} state={<><ReadState state={detail.state} detail />{reopenError ? <StateMessage tone="danger" role="alert" title="No pudimos reabrir la sesión de planificación" detail={reopenError} /> : null}</>}>
      {sectionTabs}
      {body ? <>
         <Card title="Informe de cierre"><p>{body.report ? <><Badge tone={memoryStatusTone(body.report.status)}>{memoryStatusLabel(body.report.status)}</Badge> {body.report.contenido}</> : "No hay un informe de cierre disponible."}</p></Card>
      </> : null}
    </PageFrame>;
  }
  const result = data ?? list.data;
  const currentState = state ?? (data ? "ready" : list.state);
  const sessions = result?.sessions ?? [];
  return <PageFrame title="Sesiones de planificación" meta={<span>Trabajo de planificación durable de Cortex</span>} state={<ReadState state={currentState} detail={false} />}>
    {sectionTabs}
    {currentState === "ready" && sessions.length === 0 ? <EmptyState title="No hay sesiones de planificación" description="Las sesiones de planificación aparecerán aquí cuando un administrador abra una." /> : null}
    {sessions.length > 0 ? <DataTable rows={sessions} rowKey={(item) => item.slug} columns={[{ key: "topic", header: "Tema", render: (item) => <Button variant="tertiary" onClick={() => onOpenSession?.(item.slug)}>{item.topic}</Button> }, { key: "thread", header: "Hilo", align: "right", render: (item) => tabularNum(item.thread_id) }, { key: "status", header: "Estado", render: (item) => <Badge tone={sessionStatusTone(item.status)}>{sessionStatusLabel(item.status)}</Badge> }]} actionsHeader="Acciones" actions={(item) => <Button variant="secondary" onClick={() => onOpenThread?.(item.thread_id)}>Abrir hilo</Button>} /> : null}
  </PageFrame>;
}
