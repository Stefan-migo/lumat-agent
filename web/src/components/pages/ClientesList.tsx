import { useCallback, useState } from "react";
import { Archive, ArchiveRestore, ArrowRightLeft, CalendarDays, Check, CircleCheck, CircleMinus, ChevronDown, Download, FileText, Home, Mail, MapPin, Phone, Plus, RotateCw, Sparkles, UserRound, UserRoundPlus, MessageCircle, Clock3, ClipboardCheck, XCircle, Headphones } from "lucide-react";
import { ApiError, archiveCustomer, changeClientState, createCustomer, fetchClients as listClients, getClientFicha, unarchiveCustomer } from "../../api";
import type { Customer, CustomerState } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Avatar } from "../primitives/Avatar";
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
import { Menu } from "../primitives/Menu";
import { Tabs } from "../primitives/Tabs";
import "./ClientesList.css";

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

const columns = (onOpenClient?: (id: number) => void, selected: Set<number> = new Set(), toggle: (id: number) => void = () => {}, sort: "created_desc" | "created_asc" = "created_desc", toggleSort: () => void = () => {}): Column<Customer>[] => [
  { key: "select", header: "", render: (customer) => <input type="checkbox" aria-label={`Seleccionar ${customer.name ?? customer.phone_e164 ?? "cliente"}`} checked={selected.has(customer.id)} onChange={() => toggle(customer.id)} /> },
  {
    key: "name",
    header: "Cliente",
    render: (customer) => (
      <div className="table__resource">
        <Avatar name={customer.name ?? customer.phone_e164 ?? "Cliente"} className="table__resource-avatar" />
        <div className="table__resource-body">
          <a className="clientes-list__name" href={pathForRoute({ view: "clients", clientId: customer.id })} onClick={onOpenClient ? (event) => { event.preventDefault(); onOpenClient(customer.id); } : undefined}>
            {customer.name ?? "—"}
          </a>
        </div>
      </div>
    ),
  },
  { key: "archived", header: "Registro", render: (customer) => customer.archived_at ? <Badge tone="warning">Archivado</Badge> : "—" },
  { key: "phone", header: "Teléfono", render: (customer) => customer.phone_e164 ?? "—" },
  {
    key: "state",
    header: "Estado",
    render: (customer) => <Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge>,
  },
  { key: "consent", header: "Consentimiento", render: (customer) => <span className="clientes-list__consent"><span aria-hidden="true">{customer.consent_status ? <Check /> : <CircleMinus />}</span>{customer.consent_status ? "Sí" : "No"}</span> },
  { key: "created", header: (<button className="clientes-list__sort" type="button" aria-label={`Creado ${sort === "created_desc" ? "descendente" : "ascendente"}`} onClick={toggleSort}>Creado {sort === "created_desc" ? "↓" : "↑"}</button>) as unknown as string, render: (customer) => customer.created_at ? new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(customer.created_at)).replace(".", "") : "—" },
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
  const [consent, setConsent] = useState<"" | "true" | "false">("");
  const [sort, setSort] = useState<"created_desc" | "created_asc">("created_desc");
  const [tab, setTab] = useState<"all" | "scheduled" | "finished">("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [dialog, setDialog] = useState<"create" | "archive" | "state" | null>(null);
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [comuna, setComuna] = useState("");
  const [address, setAddress] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [existingCustomerId, setExistingCustomerId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState<Customer | null>(null);
  const [stateTarget, setStateTarget] = useState<Customer | null>(null);
  const [selectedState, setSelectedState] = useState<CustomerState | null>(null);
  const [archiveCounts, setArchiveCounts] = useState<{ cases: number; appointments: number } | null>(null);
  const fetchClients = useCallback(
    () => listClients({ includeArchived, query, consent: consent === "" ? undefined : consent === "true", sort }).then((response) => response.clients),
    [includeArchived, query, consent, sort],
  );
  const fetched = useAsyncData(fetchClients, controlledData === undefined, queryVersion);
  const data = controlledData === undefined ? fetched.data : controlledData;
  const state = controlledState ?? fetched.state;
  const allRows = data ?? [];
  const counts = { all: allRows.length, scheduled: allRows.filter((row) => row.state === "agendado").length, finished: allRows.filter((row) => row.state === "finalizado").length };
  const filteredRows = tab === "scheduled" ? allRows.filter((row) => row.state === "agendado") : tab === "finished" ? allRows.filter((row) => row.state === "finalizado") : allRows;
  const pageSize = 10;
  const rows = filteredRows.slice((page - 1) * pageSize, page * pageSize);
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const toggleSelected = (id: number) => setSelected((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; });
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
      const result = await createCustomer({ phone: phone.trim(), name: name.trim() || undefined, email: email.trim() || undefined, comuna: comuna.trim() || undefined, address: address.trim() || undefined });
      setDialog(null);
      setPhone("");
      setName(""); setEmail(""); setComuna(""); setAddress("");
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
  const openState = (customer: Customer) => {
    setStateTarget(customer);
    const allowed = customer.allowed_transitions ?? [];
    setSelectedState(allowed[0] ?? null);
    setDialogError("");
    setDialog("state");
  };
  const saveState = async () => {
    if (!stateTarget || !selectedState || busy) return;
    setBusy(true);
    setDialogError("");
    try {
      await changeClientState(stateTarget.id, selectedState);
      setDialog(null);
      refresh();
    } catch {
      setDialogError("No pudimos cambiar el estado del cliente. Inténtalo nuevamente.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageFrame
      title="Clientes"
      titleAdornment={<Badge>{allRows.length}</Badge>}
      subtitle="Gestiona tus clientes y su historial de atención."
      actions={<><span className="clientes-list__export"><Download aria-hidden="true" /><Menu label="Exportar" items={[{ value: "clients", label: "Exportar clientes CSV", icon: Download }, { value: "cases", label: "Exportar casos CSV", icon: Download }]} onSelect={(value) => { window.location.href = value === "clients" ? "/panel/export/clients.csv" : "/panel/export/cases.csv"; }} /><ChevronDown aria-hidden="true" /></span><Button onClick={() => { setDialogError(""); setExistingCustomerId(null); setDialog("create"); }}><Plus />Nuevo cliente</Button></>}
      meta={!data ? "Clientes del negocio" : undefined}
      state={stateMessage(state, retry)}
    >
      <section aria-label="Listado de clientes">
        <Tabs ariaLabel="Estado de clientes" activeTab={tab} onTabChange={(value) => { setTab(value as typeof tab); setPage(1); setSelected(new Set()); }} tabs={[{ id: "all", label: <>Todos <Badge>{counts.all}</Badge></> }, { id: "scheduled", label: <>Agendados <Badge>{counts.scheduled}</Badge></> }, { id: "finished", label: <>Finalizados <Badge>{counts.finished}</Badge></> }]}>
        {() => <div className="table-card clientes-list__card">
        <div className="table-toolbar clientes-list__toolbar">
          <SearchInput key={searchResetKey} aria-label="Buscar clientes" placeholder="Buscar por nombre o teléfono..." onSearch={(next) => { setSearchTerm(next); setPage(1); setQueryVersion((current) => current + 1); }} />
          <label className="clientes-list__filter"><span>Consentimiento</span><select aria-label="Consentimiento" value={consent} onChange={(event) => { setConsent(event.target.value as typeof consent); setPage(1); setSelected(new Set()); refresh(); }}><option value="">Consentimiento</option><option value="true">Sí</option><option value="false">No</option></select></label>
          <label className="clientes-list__switch"><input type="checkbox" role="switch" aria-label="Mostrar archivados" checked={includeArchived} onChange={(event) => { setIncludeArchived(event.target.checked); refresh(); }} /><span>Mostrar archivados</span></label>
        </div>
        {dialog === null && dialogError ? <p role="alert">{dialogError}</p> : null}
        {state === "loading" ? null : data && data.length > 0 ? (
          <div className="data-region">
              <div className="clientes-list__selection"><label><input type="checkbox" aria-label="Seleccionar todos" checked={rows.length > 0 && rows.every((row) => selected.has(row.id))} onChange={(event) => setSelected((current) => { const next = new Set(current); rows.forEach((row) => event.target.checked ? next.add(row.id) : next.delete(row.id)); return next; })} /> Seleccionar todos</label>{selected.size ? <span>{selected.size} seleccionados</span> : null}</div>
               <DataTable columns={columns(onOpenClient, selected, toggleSelected, sort, () => { setSort((value) => value === "created_desc" ? "created_asc" : "created_desc"); refresh(); })} rows={rows} rowKey={(customer) => String(customer.id)} actions={(customer) => {
              // The row's identity lives in the trigger's accessible name, not in every
              // action label: two pills repeating the customer name dominated the cell
              // (DESIGN_SYSTEM.md:475). `Archivar` is the only destructive action and
              // carries tone plus an icon, never colour alone (DESIGN_SYSTEM.md:509-510).
              const rowLabel = `Acciones para ${customer.name ?? customer.phone_e164 ?? "cliente"}`;
              const items = customer.archived_at
                ? [
                    { value: "state", label: "Cambiar estado", icon: ArrowRightLeft },
                    { value: "restore", label: "Restaurar", icon: ArchiveRestore },
                  ]
                : [
                    { value: "state", label: "Cambiar estado", icon: ArrowRightLeft },
                    { value: "archive", label: "Archivar", icon: Archive, tone: "danger" as const },
                  ];
              return (
                  <div className="table__actions">
                  <Menu
                    trigger="icon"
                    label={rowLabel}
                    items={items}
                    onSelect={(value) => {
                      if (value === "state") void openState(customer);
                      else if (value === "archive") void openArchive(customer);
                      else void restore(customer);
                    }}
                  />
                </div>
              );
            }} />
              <footer className="table-footer"><span className="table-footer__count">Mostrando {rows.length} de {filteredRows.length} clientes</span><div className="table-footer__pagination"><Button variant="secondary" disabled={page <= 1} aria-label="Página anterior" onClick={() => setPage((value) => value - 1)}>‹</Button><span className="table-footer__page" aria-current="page">{page}</span><Button variant="secondary" disabled={page >= pageCount} aria-label="Página siguiente" onClick={() => setPage((value) => value + 1)}>›</Button></div></footer>
          </div>
        ) : filtered ? (
          <div>
            <EmptyState title="Sin resultados" description="Ajusta tu búsqueda o límpiala para ver todo el listado." />
            <Button variant="secondary" onClick={clearSearch}>Limpiar búsqueda</Button>
          </div>
        ) : state === "empty" || (state === "ready" && data?.length === 0) ? (
          <EmptyState title="No hay registros" description="Ajusta tu búsqueda o agrega nuevos clientes." />
        ) : null}
        </div>}
        </Tabs>
      </section>
      <Dialog open={dialog === "create"} onClose={() => setDialog(null)} title="Nuevo cliente" icon={UserRoundPlus} description="Registra sus datos de contacto y ubicación." size="wide">
        <form className="clientes-list__create-form" onSubmit={(event) => void submitCreate(event)}>
          <section><h3>Datos de contacto</h3><div className="clientes-list__contact-grid"><Input label="Teléfono" type="tel" required icon={Phone} helper="Incluye el código de país." placeholder="+56 9 1234 5678" value={phone} onChange={(event) => setPhone(event.target.value)} /><Input label="Nombre (opcional)" icon={UserRound} placeholder="Ej. Carla Núñez" value={name} onChange={(event) => setName(event.target.value)} /></div><Input label="Correo (opcional)" type="email" icon={Mail} placeholder="correo@ejemplo.com" value={email} onChange={(event) => setEmail(event.target.value)} /></section>
          <section><h3>Ubicación</h3><Input label="Comuna (opcional)" icon={MapPin} placeholder="Ej. Providencia" value={comuna} onChange={(event) => setComuna(event.target.value)} /><Input label="Dirección (opcional)" icon={Home} placeholder="Calle, número y departamento" helper="Estos datos facilitan la coordinación de visitas." value={address} onChange={(event) => setAddress(event.target.value)} /></section>
          <footer><span><strong>*</strong> Campo obligatorio</span><Button type="button" variant="secondary" onClick={() => setDialog(null)}>Cancelar</Button>
          {dialogError ? <p role="alert">{dialogError}</p> : null}
          {existingCustomerId !== null ? <Button type="button" onClick={() => { setDialog(null); onOpenClient?.(existingCustomerId); }}>Abrir la ficha existente</Button> : null}
          <Button type="submit" disabled={busy}><UserRoundPlus />Crear cliente</Button></footer>
        </form>
      </Dialog>
      <Dialog open={dialog === "archive"} onClose={() => setDialog(null)} title="Archivar cliente" icon={Archive} description="El cliente dejará de aparecer en la lista habitual.">
        {archiveTarget ? <div className="clientes-list__confirm">
          <div className="clientes-list__client-context"><Avatar name={archiveTarget.name ?? archiveTarget.phone_e164 ?? "Cliente"} /><div><strong>{archiveTarget.name ?? archiveTarget.phone_e164 ?? "Cliente"}</strong><span>Cliente desde el {archiveTarget.created_at ? new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(archiveTarget.created_at)).replace(".", "") : "—"}</span></div></div>
          <h3>Información del cliente</h3><div className="clientes-list__archive-stats"><div><FileText /><strong>{archiveCounts?.cases ?? "—"}</strong><span>casos abiertos</span></div><div><CalendarDays /><strong>{archiveCounts?.appointments ?? "—"}</strong><span>visitas futuras</span></div></div>
          <p className="clientes-list__warning"><CircleMinus />Estos trabajos seguirán registrados.</p>
          {dialogError ? <p role="alert">{dialogError}</p> : null}
          <footer><Button variant="secondary" onClick={() => setDialog(null)}>Cancelar</Button><Button variant="danger" onClick={() => void confirmArchive()} disabled={busy || !archiveCounts}><Archive />Archivar cliente</Button></footer>
        </div> : null}
      </Dialog>
      <Dialog open={dialog === "state"} onClose={() => setDialog(null)} title="Cambiar estado del cliente" icon={RotateCw} description="Selecciona el nuevo estado de atención.">
        {stateTarget ? <div className="clientes-list__confirm">
          <div className="clientes-list__client-context"><Avatar name={stateTarget.name ?? stateTarget.phone_e164 ?? "Cliente"} /><div><strong>{stateTarget.name ?? stateTarget.phone_e164 ?? "Cliente"}</strong><span>{stateTarget.phone_e164 ?? "—"}</span></div><div className="clientes-list__current-state"><span>Estado actual</span><Badge tone={customerStateTone(stateTarget.state)}>{customerStateLabel(stateTarget.state)}</Badge></div></div>
          <h3>Nuevo estado</h3>{(stateTarget.allowed_transitions ?? []).length ? <div className="clientes-list__state-options" role="radiogroup" aria-label="Nuevo estado">{(stateTarget.allowed_transitions ?? []).map((value) => { const stateIcons = { nuevo: Sparkles, contactado: MessageCircle, pendiente: Clock3, agendado: CalendarDays, en_evaluacion: ClipboardCheck, finalizado: CircleCheck, cancelado: XCircle, postventa: Headphones }; const StateIcon = stateIcons[value]; return <button key={value} type="button" role="radio" aria-checked={selectedState === value} disabled={busy} className={selectedState === value ? "clientes-list__state-option is-selected" : "clientes-list__state-option"} onClick={() => setSelectedState(value)}><StateIcon /><span>{customerStateLabel(value)}</span><span className="clientes-list__radio" /></button>; })}</div> : <p role="status">Este cliente no tiene transiciones de estado disponibles.</p>}
          {(stateTarget.allowed_transitions ?? []).length ? <div className="clientes-list__transition"><span>Cambio:</span><Badge tone={customerStateTone(stateTarget.state)}>{customerStateLabel(stateTarget.state)}</Badge><span aria-hidden="true">→</span><Badge tone={customerStateTone(selectedState ?? stateTarget.state)}>{customerStateLabel(selectedState ?? stateTarget.state)}</Badge></div> : null}
          {dialogError ? <p role="alert">{dialogError}</p> : null}
          <footer><Button variant="secondary" onClick={() => setDialog(null)}>Cancelar</Button>{(stateTarget.allowed_transitions ?? []).length ? <Button onClick={() => void saveState()} disabled={busy || !selectedState}><Check />{busy ? "Guardando…" : "Guardar estado"}</Button> : null}</footer>
        </div> : null}
      </Dialog>
    </PageFrame>
  );
}
