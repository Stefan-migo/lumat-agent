import { useCallback, useState } from "react";
import { ApiError, archiveCustomer, createCustomer, fetchClients as listClients, getClientFicha, unarchiveCustomer } from "../../api";
import type { Customer } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { SearchInput } from "../primitives/SearchInput";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { customerStateLabel, customerStateTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";
import { Dialog } from "../primitives/Dialog";
import { Input } from "../primitives/Input";

export type ClientesListState = AsyncDataState | "stale" | "partial-error" | "fatal-error";

export interface ClientesListProps {
  data?: Customer[] | null;
  state?: ClientesListState;
  onRetry?: () => void;
  onOpenClient?: (id: number) => void;
  /** Controlled applied search term. Needed to render the filtered-empty state, which depends
   *  on the query round-trip and cannot be expressed with `data`/`state` alone. */
  query?: string;
}

const columns = (onOpenClient?: (id: number) => void): Column<Customer>[] => [
  {
    key: "name",
    header: "Cliente",
    render: (customer) => (
      <a className="table__link" href={pathForRoute({ view: "clients", clientId: customer.id })} onClick={onOpenClient ? (event) => { event.preventDefault(); onOpenClient(customer.id); } : undefined}>
        {customer.name ?? "—"}
      </a>
    ),
  },
  { key: "archived", header: "Registro", render: (customer) => customer.archived_at ? <Badge tone="warning">Archivado</Badge> : "—" },
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
        <Button variant="secondary" onClick={retry}>Reintentar</Button>
      </div>
    );
  }
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  return null;
}

export function ClientesList({ data: controlledData, state: controlledState, onRetry, onOpenClient, query: controlledQuery }: ClientesListProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const query = controlledQuery ?? searchTerm;
  // The query drives the fetch through the hook's own refresh key, so an emptied search
  // refetches the unfiltered list instead of keeping the previous filtered result.
  const [queryVersion, setQueryVersion] = useState(0);
  // Remounting the debounced input is the only way to clear it: the primitive owns its own
  // text, so resetting our query state alone would leave the stale term on screen.
  const [searchResetKey, setSearchResetKey] = useState(0);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [dialog, setDialog] = useState<"create" | "archive" | null>(null);
  const [phone, setPhone] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [existingCustomerId, setExistingCustomerId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState<Customer | null>(null);
  const [archiveCounts, setArchiveCounts] = useState<{ cases: number; appointments: number } | null>(null);
  const fetchClients = useCallback(
    () => listClients({ includeArchived, query }).then((response) => response.clients),
    [includeArchived, query],
  );
  const fetched = useAsyncData(fetchClients, controlledData === undefined, queryVersion);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? fetched.state;
  const retry = onRetry ?? fetched.retry;
  const filtered = query.trim().length > 0;
  const clearSearch = () => {
    setSearchTerm("");
    setQueryVersion((current) => current + 1);
    setSearchResetKey((current) => current + 1);
  };
  const refresh = () => setQueryVersion((current) => current + 1);
  const openArchive = async (customer: Customer) => {
    setArchiveTarget(customer);
    setArchiveCounts(null);
    setDialogError("");
    setDialog("archive");
    try {
      const ficha = await getClientFicha(customer.id);
      const now = Date.now();
      setArchiveCounts({
        cases: ficha.history.cases.filter((item) => item.is_open).length,
        appointments: (ficha.history.appointments ?? []).filter((item) => item.starts_at && Date.parse(item.starts_at) > now && item.status !== "cancelled").length,
      });
    } catch {
      setDialogError("No pudimos cargar los antecedentes para confirmar el archivo. Reintenta.");
    }
  };
  const submitCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setDialogError("");
    setExistingCustomerId(null);
    try {
      const result = await createCustomer({ phone: phone.trim() });
      setDialog(null);
      setPhone("");
      refresh();
      onOpenClient?.(result.customer.id);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409 && error.structuredDetail?.code === "phone_exists" && typeof error.structuredDetail.customer_id === "number") {
        setExistingCustomerId(error.structuredDetail.customer_id);
      } else {
        setDialogError("No pudimos crear el cliente. Revisa el teléfono e inténtalo nuevamente.");
      }
    } finally {
      setBusy(false);
    }
  };
  const confirmArchive = async () => {
    if (!archiveTarget) return;
    setBusy(true);
    setDialogError("");
    try {
      await archiveCustomer(archiveTarget.id);
      setDialog(null);
      refresh();
    } catch {
      setDialogError("No pudimos archivar el cliente. Inténtalo nuevamente.");
    } finally {
      setBusy(false);
    }
  };
  const restore = async (customer: Customer) => {
    setDialogError("");
    try {
      await unarchiveCustomer(customer.id);
      refresh();
    } catch {
      setDialogError("No pudimos restaurar el cliente. Inténtalo nuevamente.");
    }
  };

  return (
    <PageFrame
      title="Clientes"
      meta={data ? `${data.length} ${data.length === 1 ? "cliente" : "clientes"}` : "Clientes del negocio"}
      state={stateMessage(state, retry)}
    >
      <section aria-label="Listado de clientes">
        <div className="toolbar">
          <SearchInput key={searchResetKey} aria-label="Buscar clientes" onSearch={(next) => { setSearchTerm(next); setQueryVersion((current) => current + 1); }} />
          <Button onClick={() => { setDialogError(""); setExistingCustomerId(null); setDialog("create"); }}>Nuevo cliente</Button>
          <label><input type="checkbox" aria-label="Mostrar archivados" checked={includeArchived} onChange={(event) => { setIncludeArchived(event.target.checked); refresh(); }} /> Mostrar archivados</label>
          <Button variant="secondary" href="/panel/export/clients.csv">Exportar clientes CSV</Button>
          <Button variant="secondary" href="/panel/export/cases.csv">Exportar casos CSV</Button>
        </div>
        {dialog === null && dialogError ? <p role="alert">{dialogError}</p> : null}
        {state === "loading" ? null : data && data.length > 0 ? (
          <div className="data-region">
            <DataTable columns={columns(onOpenClient)} rows={data} rowKey={(customer) => String(customer.id)} actions={(customer) => customer.archived_at ? <Button variant="secondary" onClick={() => void restore(customer)}>Restaurar {customer.name ?? "cliente"}</Button> : <Button variant="secondary" onClick={() => void openArchive(customer)}>Archivar {customer.name ?? "cliente"}</Button>} />
          </div>
        ) : filtered ? (
          <div>
            <EmptyState title="Sin resultados" description="Ajusta tu búsqueda o límpiala para ver todo el listado." />
            <Button variant="secondary" onClick={clearSearch}>Limpiar búsqueda</Button>
          </div>
        ) : state === "empty" || (state === "ready" && data?.length === 0) ? (
          <EmptyState title="No hay registros" description="Ajusta tu búsqueda o agrega nuevos clientes." />
        ) : null}
      </section>
      <Dialog open={dialog === "create"} onClose={() => setDialog(null)} title="Nuevo cliente">
        <form onSubmit={(event) => void submitCreate(event)}>
          <Input label="Teléfono" type="tel" required value={phone} onChange={(event) => setPhone(event.target.value)} />
          {dialogError ? <p role="alert">{dialogError}</p> : null}
          {existingCustomerId !== null ? <Button type="button" onClick={() => { setDialog(null); onOpenClient?.(existingCustomerId); }}>Abrir la ficha existente</Button> : null}
          <Button type="submit" disabled={busy}>Crear cliente</Button>
        </form>
      </Dialog>
      <Dialog open={dialog === "archive"} onClose={() => setDialog(null)} title="Archivar cliente">
        <p>{archiveTarget?.name ?? "Este cliente"}: {archiveCounts ? `${archiveCounts.cases} ${archiveCounts.cases === 1 ? "caso abierto" : "casos abiertos"} y ${archiveCounts.appointments} ${archiveCounts.appointments === 1 ? "visita futura" : "visitas futuras"}.` : "Cargando antecedentes…"}</p>
        {dialogError ? <p role="alert">{dialogError}</p> : null}
        <Button onClick={() => void confirmArchive()} disabled={busy || !archiveCounts}>Confirmar archivo</Button>
      </Dialog>
    </PageFrame>
  );
}
