import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../api";
import type { Customer } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { SearchInput } from "../primitives/SearchInput";
import { DataTable, type Column } from "../../stories/pages/_shared/DataTable";
import { EmptyState } from "../../stories/pages/_shared/EmptyState";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage } from "../../stories/pages/_shared/StateMessage";
import { customerStateLabel, customerStateTone } from "../../stories/pages/_shared/toneMaps";

export type ClientesListState = AsyncDataState | "stale" | "partial-error" | "fatal-error";

export interface ClientesListProps {
  data?: Customer[] | null;
  state?: ClientesListState;
  onRetry?: () => void;
}

const columns: Column<Customer>[] = [
  {
    key: "name",
    header: "Cliente",
    render: (customer) => (
      <a href={`#/clientes/${customer.id}`} style={{ color: "var(--primary-700)" }}>
        {customer.name ?? "—"}
      </a>
    ),
  },
  { key: "phone", header: "Teléfono", render: (customer) => customer.phone_e164 ?? "—" },
  {
    key: "state",
    header: "Estado",
    render: (customer) => <Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge>,
  },
  { key: "consent", header: "Consentimiento", render: (customer) => (customer.consent_status ? "Sí" : "No") },
  { key: "created", header: "Creado", render: (customer) => customer.created_at?.slice(0, 10) ?? "—" },
];

function stateMessage(state: ClientesListState, retry: () => void) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando clientes" />;
  if (state === "empty") return null;
  if (state === "stale") return <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" />;
  if (state === "partial-error") return <StateMessage tone="danger" role="status" title="No pudimos actualizar parte del listado" />;
  if (state === "fatal-error" || state === "error") {
    return (
      <div>
        <StateMessage tone="danger" role="alert" title="No pudimos cargar los clientes" detail="Reintenta para recuperar el listado." />
        <button type="button" onClick={retry}>Reintentar</button>
      </div>
    );
  }
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  return null;
}

export function ClientesList({ data: controlledData, state: controlledState, onRetry }: ClientesListProps) {
  const [query, setQuery] = useState("");
  const fetchClients = useCallback(
    () => apiFetch<{ clients: Customer[] }>(`/panel/api/clients${query ? `?q=${encodeURIComponent(query)}` : ""}`).then((response) => response.clients),
    [query],
  );
  const fetched = useAsyncData(fetchClients, controlledData === undefined);
  useEffect(() => {
    if (controlledData === undefined && query) fetched.retry();
  }, [controlledData, query]);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;

  return (
    <PageFrame
      title="Clientes"
      meta={data ? `${data.length} clientes` : undefined}
      actions={
        <>
          <SearchInput aria-label="Buscar clientes" onSearch={setQuery} />
          <Button variant="secondary" href="data:text/csv;base64,">Exportar CSV</Button>
        </>
      }
      state={stateMessage(state, retry)}
    >
      {state === "loading" ? null : data && data.length > 0 ? (
        <DataTable columns={columns} rows={data} rowKey={(customer) => String(customer.id)} />
      ) : state === "empty" || (state === "ready" && data?.length === 0) ? (
        <EmptyState title="No hay registros" description="Ajusta tu búsqueda o agrega nuevos clientes." />
      ) : null}
    </PageFrame>
  );
}
