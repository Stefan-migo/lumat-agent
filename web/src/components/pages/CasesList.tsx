import { useCallback } from "react";
import { apiFetch, postJson } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Case, CasesResponse, UserRef } from "../../types";
import { Badge } from "../primitives/Badge";
import { DataTable, type Column } from "../shared/DataTable";
import { CaseActions } from "../shared/CaseActions";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { caseStatusLabel, caseStatusTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";

export type CasesListState = AsyncDataState | "stale" | "partial-error" | "fatal-error";

export interface CasesListProps {
  data?: CasesResponse | null;
  state?: CasesListState;
  onRetry?: () => void;
  onOpenClient?: (id: number) => void;
}

const responsibleLabel = (id: number | null, users: UserRef[]): string => {
  const user = users.find((candidate) => candidate.id === id);
  return user ? user.username : "—";
};

function EmergencyCell({ c }: { c: Case }) {
  if (!c.emergency) return <span>—</span>;
  return (
    <StateMessage
      tone={c.ack_by ? "warning" : "danger"}
      role="status"
      title="Emergencia"
      detail={c.ack_by ? `Reconocida por ${c.ack_by}` : "Sin reconocer"}
    />
  );
}

const columns: Column<Case>[] = [
  { key: "id", header: "#", render: (c) => `#${c.id}` },
  { key: "customer", header: "Cliente", render: (c) => <a className="table__link" href={pathForRoute({ view: "clients", clientId: c.customer.id })}>{c.customer.name ?? "—"}</a> },
  { key: "service", header: "Servicio", render: (c) => c.service ?? "—" },
  { key: "status", header: "Estado", render: (c) => <Badge tone={caseStatusTone(c.status)}>{caseStatusLabel(c.status)}</Badge> },
  { key: "summary", header: "Resumen", render: (c) => c.summary ?? "—" },
  { key: "emergency", header: "Emergencia", render: (c) => <EmergencyCell c={c} /> },
  { key: "responsible", header: "Responsable", render: (c) => responsibleLabel(c.responsible_id, []) },
];

function stateMessage(state: CasesListState, unanswered: number) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando casos" detail="Reuniendo los casos pendientes y escalados." />;
  if (state === "fatal-error" || state === "error") return <StateMessage tone="danger" role="alert" title="No pudimos cargar los casos" detail="Reintenta para recuperar el listado." />;
  if (state === "stale") return <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />;
  if (state === "partial-error") return <StateMessage tone="danger" role="status" title="No pudimos actualizar parte de los casos" detail="El listado está vigente, pero un origen no respondió. Reintenta en unos minutos." />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (unanswered > 0) return <StateMessage tone="danger" role="alert" title="Emergencias sin reconocer" detail={`${unanswered} casos requieren atención inmediata.`} />;
  return null;
}

export function CasesList({ data: controlledData, state: controlledState, onRetry, onOpenClient }: CasesListProps) {
  const fetchCases = useCallback(() => apiFetch<CasesResponse>("/panel/api/cases"), []);
  const fetched = useAsyncData(fetchCases, controlledData === undefined);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const cases = data?.cases ?? [];
  const users = data?.users ?? [];
  const unanswered = cases.filter((c) => c.emergency && c.ack_by === null).length;
  const updateCase = async (caseId: number, status: string, responsibleId: number | null) => {
    await postJson(`/panel/api/cases/${caseId}/update`, { status, responsible_id: responsibleId });
    retry();
  };
  const acknowledgeCase = async (caseId: number) => {
    await postJson(`/panel/api/cases/${caseId}/ack`);
    retry();
  };

  return (
    <PageFrame title="Casos" meta={data ? `${cases.length} casos abiertos · ${unanswered} emergencias sin reconocer` : "Casos abiertos y emergencias"} state={stateMessage(state, unanswered)}>
      {state === "loading" ? null : state === "empty" || (state === "ready" && data && cases.length === 0) ? (
        <EmptyState title="No hay registros" description="No existen casos abiertos pendientes o escalados." />
      ) : data ? (
        <DataTable
          columns={columns.map((column) => column.key === "responsible" ? { ...column, render: (c: Case) => responsibleLabel(c.responsible_id, users) } : column.key === "customer" && onOpenClient ? { ...column, render: (c: Case) => <a className="table__link" href={pathForRoute({ view: "clients", clientId: c.customer.id })} onClick={(event) => { event.preventDefault(); onOpenClient(c.customer.id); }}>{c.customer.name ?? "—"}</a> } : column)}
          rows={cases}
          rowKey={(c) => String(c.id)}
          actions={(c) => <CaseActions target={c} users={users} onUpdate={controlledData === undefined ? updateCase : undefined} onAcknowledge={controlledData === undefined ? acknowledgeCase : undefined} />}
        />
      ) : null}
    </PageFrame>
  );
}
