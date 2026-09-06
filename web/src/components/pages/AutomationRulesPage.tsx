import { useCallback } from "react";
import { listAutomationRules } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Rule } from "../../types";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { pathForRoute } from "../domain/panelRoutes";

export interface AutomationRulesPageProps {
  data?: Rule[] | null;
  state?: AsyncDataState;
  onRetry?: () => void;
  onOpenRule?: (id: number) => void;
}

function columnsFor(onOpenRule?: (id: number) => void): Column<Rule>[] {
  return [
  { key: "id", header: "ID", render: (rule) => rule.id },
  { key: "name", header: "Nombre", render: (rule) => <a href={pathForRoute({ view: "automation-rules", automationRuleId: rule.id })} onClick={onOpenRule ? (event) => { event.preventDefault(); onOpenRule(rule.id); } : undefined}>{rule.name}</a> },
  { key: "event", header: "Evento", render: (rule) => rule.event_type },
  { key: "content", header: "Contenido de notificación", render: (rule) => rule.template_event },
  { key: "conditions", header: "Condiciones", render: (rule) => JSON.stringify(rule.conditions) },
  { key: "channel", header: "Canal", render: (rule) => rule.channel },
  { key: "cooldown", header: "Cooldown", render: (rule) => `${rule.cooldown_seconds} s` },
  { key: "enabled", header: "Estado", render: (rule) => rule.enabled ? "Habilitada" : "Deshabilitada" },
  { key: "created-by", header: "Creada por", render: (rule) => rule.created_by },
  ];
}

export function AutomationRulesPage({ data: controlledData, state: controlledState, onRetry, onOpenRule }: AutomationRulesPageProps) {
  const fetchRules = useCallback(() => listAutomationRules().then((response) => response.rules), []);
  const fetched = useAsyncData(fetchRules, controlledData === undefined);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const stateMessage = state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando reglas" />
    : state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver las reglas" />
    : state === "error" ? <div><StateMessage tone="danger" role="alert" title="No pudimos cargar las reglas" detail="Reintenta para recuperar las automatizaciones." /><button type="button" onClick={retry}>Reintentar</button></div>
    : null;

  return <PageFrame title="Reglas de automatización" meta={data ? `${data.length} reglas` : undefined} state={stateMessage}>
    {state === "loading" || state === "error" || state === "denied" ? null : data?.length === 0 || state === "empty" ? <EmptyState title="No hay reglas de automatización" description="No hay reglas configuradas para mostrar." /> : <DataTable columns={columnsFor(onOpenRule)} rows={data ?? []} rowKey={(rule) => String(rule.id)} />}
  </PageFrame>;
}
