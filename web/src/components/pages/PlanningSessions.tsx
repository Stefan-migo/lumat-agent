import { useCallback, useState, type CSSProperties, type ReactNode } from "react";
import { getPlanningSession, listPlanningSessions, reopenPlanningSession } from "../../api";
import type { PlanningSessionDetailResponse, PlanningSessionsResponse } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { EmptyState } from "../shared/EmptyState";
import { DataTable, tabularNum } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { handoffStatusLabel, handoffStatusTone, memoryStatusLabel, memoryStatusTone, sessionStatusLabel, sessionStatusTone } from "../shared/toneMaps";

const TIMESTAMP_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" });

function formatTimestamp(value: string | null): string | null {
  return value ? TIMESTAMP_FORMAT.format(new Date(value)) : null;
}

/** Shared two-column layout for the detail definition lists. */
const FACTS_STYLE: CSSProperties = { display: "grid", gridTemplateColumns: "max-content minmax(0, 1fr)", gap: "var(--space-2) var(--space-4)", margin: 0, paddingBottom: "var(--space-4)", borderBottom: "1px solid var(--border)" };

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
  if (sessionSlug) {
    const body = detail.data as PlanningSessionDetailResponse | null;
    const session = body?.session;
    const reopen = async () => {
      if (!session) return;
      setReopening(true);
      try {
        await reopenPlanningSession(session.slug);
        onOpenThread?.(session.thread_id);
      } finally {
        setReopening(false);
      }
    };
    const opened = formatTimestamp(session?.opened_at ?? null);
    const closed = formatTimestamp(session?.closed_at ?? null);
    return <PageFrame title={session?.topic ?? "Sesión de planificación"} meta={session ? <span>Hilo {session.thread_id} · <Badge tone={sessionStatusTone(session.status)}>{sessionStatusLabel(session.status)}</Badge>{opened ? <> · Apertura: {opened}</> : null}{closed ? <> · Cierre: {closed}</> : null}</span> : undefined} actions={<><Button variant="secondary" onClick={() => window.history.back()}>Volver a las sesiones de planificación</Button>{session?.status === "closed" ? <Button disabled={reopening} onClick={() => void reopen()}>Reabrir sesión</Button> : null}</>} state={<ReadState state={detail.state} detail />}>
      {sectionTabs}
      {body ? <>
         <section aria-labelledby="session-facts-heading"><h2 id="session-facts-heading">Datos de la sesión</h2><dl style={FACTS_STYLE}>{body.session.turn_index !== null && body.session.turn_index !== undefined ? <><dt>Turno</dt><dd>{body.session.turn_index}</dd></> : null}{body.session.next_decision ? <><dt>Próxima decisión</dt><dd>{body.session.next_decision}</dd></> : null}{body.session.last_class ? <><dt>Última clasificación</dt><dd>{body.session.last_class}</dd></> : null}</dl></section>
         <section aria-labelledby="handoff-heading"><h2 id="handoff-heading">Derivación SDB</h2><dl style={FACTS_STYLE}><dt>Estado</dt><dd><Badge tone={handoffStatusTone(body.session.handoff.status)}>{handoffStatusLabel(body.session.handoff.status)}</Badge></dd>{body.session.handoff.sdb_phase ? <><dt>Fase SDB</dt><dd>{body.session.handoff.sdb_phase}</dd></> : null}{body.session.handoff.run_id ? <><dt>ID de ejecución</dt><dd>{body.session.handoff.run_id}</dd></> : null}</dl></section>
         <section aria-labelledby="decisions-heading"><h2 id="decisions-heading">Decisiones</h2><DataTable rows={body.decisions} rowKey={(decision) => String(decision.id)} emptyMessage="No hay decisiones registradas" columns={[{ key: "title", header: "Título", render: (decision) => decision.titulo }, { key: "content", header: "Contenido", render: (decision) => decision.contenido }, { key: "status", header: "Estado", render: (decision) => <Badge tone={memoryStatusTone(decision.status)}>{memoryStatusLabel(decision.status)}</Badge> }]} /></section>
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
