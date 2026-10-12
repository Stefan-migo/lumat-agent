import { useCallback, useMemo, useState } from "react";
import { ApiError, getPlanningSession, getProject, listPlanningSessions, reopenPlanningSession } from "../../api";
import type { PlanningSessionDetailResponse, PlanningSessionsResponse } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { EmptyState } from "../shared/EmptyState";
import { DataTable, tabularNum } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { SearchInput } from "../primitives/SearchInput";
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

export function PlanningSessions({ sessionSlug, projectSlug, onOpenSession, onOpenThread, onBack, data, state }: { sessionSlug?: string; projectSlug?: string; onOpenSession?: (slug: string) => void; onOpenThread?: (id: number) => void; onBack?: (projectSlug?: string) => void; data?: PlanningSessionsResponse; state?: AsyncDataState }) {
  const list = useAsyncData(useCallback(() => listPlanningSessions(projectSlug), [projectSlug]), data === undefined);
  const project = useAsyncData(useCallback(() => getProject(projectSlug!), [projectSlug]), projectSlug !== undefined);
  const detail = useAsyncData(useCallback(() => getPlanningSession(sessionSlug!), [sessionSlug]), sessionSlug !== undefined);
  // Declared before the detail early-return so the hook order stays stable.
  const [reopening, setReopening] = useState(false);
  const [reopenError, setReopenError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const result = data ?? list.data;
  const sessions = result?.sessions ?? [];
  const visibleSessions = useMemo(() => sessions.filter((session) => session.topic.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())), [sessions, search]);
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
    return <PageFrame title={session?.topic ?? "Sesión de planificación"} meta={session ? `Hilo ${session.thread_id} · ${sessionStatusLabel(session.status)}${opened ? ` · Apertura: ${opened}` : ""}${closed ? ` · Cierre: ${closed}` : ""}` : "Detalle de la sesión"} actions={<><Button variant="secondary" onClick={() => onBack ? onBack(session?.proyecto) : window.history.back()}>Volver a las sesiones de planificación</Button>{session?.status === "closed" ? <Button disabled={reopening} onClick={() => void reopen()}>Reabrir sesión</Button> : null}</>} state={<><ReadState state={detail.state} detail />{reopenError ? <StateMessage tone="danger" role="alert" title="No pudimos reabrir la sesión de planificación" detail={reopenError} /> : null}</>}>
      {body ? <>
         <Card title="Informe de cierre"><p>{body.report ? <><Badge tone={memoryStatusTone(body.report.status)}>{memoryStatusLabel(body.report.status)}</Badge> {body.report.contenido}</> : "No hay un informe de cierre disponible."}</p></Card>
      </> : null}
    </PageFrame>;
  }
  const currentState = state ?? (data ? "ready" : list.state);
  const projectName = project.data?.project?.name ?? projectSlug;
  return <PageFrame title="Sesiones de planificación" meta={<span>{projectName ? `${projectName} · ` : ""}Trabajo de planificación durable de Cortex</span>} state={<ReadState state={currentState} detail={false} />}>
    {currentState === "ready" && sessions.length === 0 ? <EmptyState title="No hay sesiones de planificación" description="Las sesiones de planificación aparecerán aquí cuando un administrador abra una." /> : null}
    {sessions.length > 0 ? <><SearchInput aria-label="Buscar sesiones de planificación" placeholder="Buscar sesión" onSearch={setSearch} />{visibleSessions.length ? <DataTable rows={visibleSessions} rowKey={(item) => item.slug} columns={[{ key: "topic", header: "Tema", render: (item) => <Button variant="tertiary" onClick={() => onOpenSession?.(item.slug)}>{item.topic}</Button> }, { key: "thread", header: "Hilo", align: "right", render: (item) => tabularNum(item.thread_id) }, { key: "status", header: "Estado", render: (item) => <Badge tone={sessionStatusTone(item.status)}>{sessionStatusLabel(item.status)}</Badge> }]} actionsHeader="Acciones" actions={(item) => <Button variant="secondary" onClick={() => onOpenThread?.(item.thread_id)}>Abrir hilo</Button>} /> : <EmptyState title="No encontramos sesiones" description="Prueba con otro tema." />}</> : null}
  </PageFrame>;
}
