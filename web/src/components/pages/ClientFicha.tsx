import { useCallback, useState } from "react";
import { addClientNote, ApiError, apiFetch, changeClientState, postJson, resolveMemoryRelation } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Appointment, ClientFichaResponse, CustomerState, Memory, MemoryRelation, MemoryRelationKind, MemoriesResponse, PendingMemoryRelationsResponse } from "../../types";
import { ClientMemories } from "../domain/ClientMemories";
import { pathForRoute } from "../domain/panelRoutes";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { DataTable, type Column } from "../shared/DataTable";
import { CaseActions } from "../shared/CaseActions";
import { CollapsibleMessages } from "../shared/CollapsibleMessages";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import {
  appointmentStatusLabel,
  appointmentStatusTone,
  caseStatusLabel,
  caseStatusTone,
  conversationLabel,
  customerStateLabel,
  customerStateTone,
  directionLabel,
} from "../shared/toneMaps";

const DATE_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "short" });
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" });
const MESSAGE_PREVIEW = 10;

const formatDate = (value: string | null | undefined) => (value ? DATE_FORMAT.format(new Date(value)) : "—");
const formatDateTime = (value: string | null | undefined) => (value ? DATE_TIME_FORMAT.format(new Date(value)) : "—");

export interface ClientFichaProps {
  customerId?: number;
  data?: ClientFichaResponse;
  memories?: Memory[];
  isSaving?: boolean;
  onRetryCalendar?: (appointmentId: number) => void;
  /** Controlled read state, so the state matrix is renderable in stories and tests
   *  without a request. A controlled state also disables the fetch. */
  state?: FichaState;
}

type FichaState = AsyncDataState | "fatal-error";
type Feedback = { tone: "success" | "danger"; title: string; detail?: string };

function stateMessage(state: FichaState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando ficha" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error" || state === "fatal-error") {
    return <StateMessage tone="danger" role="alert" title="No pudimos cargar la ficha" detail="Reintenta para recuperar los datos." />;
  }
  return null;
}

/** Feedback belongs beside the control that caused it, not in the page banner. */
function LocalFeedback({ feedback }: { feedback: Feedback | null }) {
  if (!feedback) return null;
  return <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.title} detail={feedback.detail} />;
}

/** A data surface only when there is data: an empty DataTable already renders its own
 *  `.empty-state` surface, and nesting the two would be card-on-card. */
function surfaceClass(rowCount: number) {
  return rowCount > 0 ? "data-region" : undefined;
}

export function ClientFicha({ customerId, data: controlledData, memories: controlledMemories, isSaving = false, onRetryCalendar, state: controlledState }: ClientFichaProps) {
  const [retryingCalendarId, setRetryingCalendarId] = useState<number | null>(null);
  const [messagesExpanded, setMessagesExpanded] = useState(false);
  const [refreshed, setRefreshed] = useState<{ ficha: ClientFichaResponse; memories: Memory[]; pendingRelations: MemoryRelation[] } | null>(null);
  const [selectedState, setSelectedState] = useState<CustomerState | null>(null);
  const [note, setNote] = useState("");
  const [mutation, setMutation] = useState<"state" | "note" | null>(null);
  const [stateFeedback, setStateFeedback] = useState<Feedback | null>(null);
  const [noteFeedback, setNoteFeedback] = useState<Feedback | null>(null);
  const [caseFeedback, setCaseFeedback] = useState<Feedback | null>(null);
  const fetchFicha = useCallback(async () => {
    if (customerId === undefined) throw new Error("customer id is required");
    const [ficha, memoryResponse, pendingResponse] = await Promise.all([
      apiFetch<ClientFichaResponse>(`/panel/api/clients/${customerId}${messagesExpanded ? "" : `?messages_limit=${MESSAGE_PREVIEW}`}`),
      apiFetch<MemoriesResponse>(`/panel/api/clients/${customerId}/memories`),
      apiFetch<PendingMemoryRelationsResponse>(`/panel/api/clients/${customerId}/memory-relations/pending`),
    ]);
    return { ficha, memories: memoryResponse.memories, pendingRelations: pendingResponse.relations };
  }, [customerId, messagesExpanded]);
  const fetched = useAsyncData(fetchFicha, controlledData === undefined && controlledState === undefined);
  const data = refreshed?.ficha ?? controlledData ?? fetched.data?.ficha;
  const memories = refreshed?.memories ?? controlledMemories ?? fetched.data?.memories ?? [];
  const pendingRelations = refreshed?.pendingRelations ?? fetched.data?.pendingRelations ?? [];
  const state: FichaState = controlledState ?? (controlledData ? "ready" : fetched.state);

  if (!data) {
    return <PageFrame title="Ficha de cliente" meta="Datos del cliente" state={stateMessage(state)}><EmptyState title="Cargando ficha" /></PageFrame>;
  }

  const { customer, history } = data;
  const activeCase = history.cases.filter((row) => row.is_open).at(-1) ?? null;
  const archivedCases = history.cases.filter((row) => row.id !== activeCase?.id);
  const appointments = history.appointments ?? [];
  const retryCalendar = async (appointmentId: number) => {
    setRetryingCalendarId(appointmentId);
    try {
      await apiFetch(`/panel/api/appointments/${appointmentId}/calendar/sync`, { method: "POST" });
      onRetryCalendar?.(appointmentId);
    } finally {
      setRetryingCalendarId(null);
    }
  };
  const refresh = async () => {
    if (customerId === undefined) return;
    const next = await fetchFicha();
    setRefreshed(next);
  };
  const safeError = (error: unknown, action: "estado" | "nota" | "caso") => {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return { title: `No tienes permiso para guardar ${action}` };
    if (error instanceof ApiError && (error.status === 400 || error.status === 422)) return { title: `Revisa el ${action} e inténtalo de nuevo` };
    return { title: `No pudimos guardar ${action}`, detail: "Inténtalo nuevamente." };
  };
  const updateCase = async (caseId: number, status: string, responsibleId: number | null) => {
    setCaseFeedback(null);
    try { await postJson(`/panel/api/cases/${caseId}/update`, { status, responsible_id: responsibleId }); await refresh(); }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
  };
  const acknowledgeCase = async (caseId: number) => {
    setCaseFeedback(null);
    try { await postJson(`/panel/api/cases/${caseId}/ack`); await refresh(); }
    catch (error) { setCaseFeedback({ tone: "danger", ...safeError(error, "caso") }); }
  };
  const saveState = async () => {
    if (customerId === undefined || !selectedState || mutation) return;
    setMutation("state"); setStateFeedback(null);
    try { await changeClientState(customerId, selectedState); await refresh(); setStateFeedback({ tone: "success", title: "Estado guardado" }); }
    catch (error) { setStateFeedback({ tone: "danger", ...safeError(error, "estado") }); }
    finally { setMutation(null); }
  };
  const saveNote = async () => {
    if (customerId === undefined || !note.trim() || mutation) {
      if (!note.trim()) setNoteFeedback({ tone: "danger", title: "La nota no puede estar vacía" });
      return;
    }
    setMutation("note"); setNoteFeedback(null);
    try { await addClientNote(customerId, note.trim()); await refresh(); setNote(""); setNoteFeedback({ tone: "success", title: "Nota agregada" }); }
    catch (error) { setNoteFeedback({ tone: "danger", ...safeError(error, "nota") }); }
    finally { setMutation(null); }
  };
  const resolveRelation = async (relationId: number, relation: MemoryRelationKind) => {
    if (customerId === undefined) return;
    await resolveMemoryRelation(customerId, relationId, relation);
    await refresh();
  };
  const toggleMessages = () => { setRefreshed(null); setMessagesExpanded((value) => !value); fetched.retry(); };
  const conversationColumns: Column<(typeof history.conversations)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "state", header: "Estado", render: (row) => conversationLabel(row.state) },
    { key: "summary", header: "Resumen", render: (row) => row.summary ?? "—" },
    { key: "created", header: "Creada", render: (row) => formatDate(row.created_at) },
  ];
  const caseColumns: Column<(typeof history.cases)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "service", header: "Servicio", render: (row) => row.service },
    { key: "priority", header: "Prioridad", render: (row) => row.priority },
    { key: "status", header: "Estado", render: (row) => <Badge tone={caseStatusTone(row.status)}>{caseStatusLabel(row.status)}</Badge> },
    { key: "summary", header: "Resumen", render: (row) => row.summary ?? "—" },
  ];
  const messageColumns: Column<(typeof history.messages)[number]>[] = [
    { key: "conversation", header: "Conversación", render: (row) => <a className="table__link" href={pathForRoute({ view: "conversations", conversationId: row.conversation_id })}>#{row.conversation_id}</a> },
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "direction", header: "Dirección", render: (row) => directionLabel(row.direction) },
    { key: "msg_type", header: "Tipo", render: (row) => row.msg_type },
    { key: "text", header: "Mensaje", render: (row) => `${row.text ?? "—"}${row.media_url ? " 📎" : ""}` },
    { key: "created", header: "Fecha", render: (row) => formatDate(row.created_at) },
  ];

  return (
    <PageFrame
      title={`Ficha: ${customer.name ?? customer.phone_e164 ?? "—"}`}
      meta={`${customer.phone_e164 ?? "—"} · Estado: ${customerStateLabel(customer.state)}`}
      actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a clientes</Button>}
      state={stateMessage(state)}
    >
      <div className="detail-region">
        <section className="detail-region__rail" aria-label="Resumen del cliente">
          <Card title="Identidad">
            <dl className="detail-region__facts">
              <div><dt>Teléfono</dt><dd>{customer.phone_e164 ?? "—"}</dd></div>
              <div><dt>Correo</dt><dd>{customer.email ?? "—"}</dd></div>
              <div><dt>Comuna</dt><dd>{customer.comuna ?? "—"}</dd></div>
              <div><dt>Dirección</dt><dd>{customer.address ?? "—"}</dd></div>
              <div><dt>Consentimiento</dt><dd>{customer.consent_status ? "Sí" : "No"}</dd></div>
              <div><dt>Cliente desde</dt><dd>{formatDate(customer.created_at)}</dd></div>
            </dl>
            <div><Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge></div>
          </Card>

          <Card title="Estado">
            <div className="client-ficha__state-control">
              <Select
                id="client-state"
                label="Estado del cliente"
                value={selectedState ?? customer.state}
                options={(data.states ?? []).map((option) => ({ value: option, label: customerStateLabel(option) }))}
                disabled={mutation !== null || customerId === undefined}
                onChange={(event) => setSelectedState(event.target.value as CustomerState)}
              />
              <Button
                disabled={mutation !== null || customerId === undefined || !selectedState || selectedState === customer.state}
                onClick={() => void saveState()}
              >
                {mutation === "state" ? "Guardando…" : "Guardar estado"}
              </Button>
              <LocalFeedback feedback={stateFeedback} />
              {isSaving ? <p role="status">Guardando estado…</p> : null}
            </div>
          </Card>
        </section>

        <div className="detail-region__main">
          <Card title="Caso activo">
            {activeCase ? <>
              <dl className="detail-region__facts">
                <div><dt>#</dt><dd>#{activeCase.id}</dd></div>
                <div><dt>Servicio</dt><dd>{activeCase.service}</dd></div>
                <div><dt>Prioridad</dt><dd>{activeCase.priority}</dd></div>
                <div><dt>Estado</dt><dd><Badge tone={caseStatusTone(activeCase.status)}>{caseStatusLabel(activeCase.status)}</Badge></dd></div>
                <div><dt>Responsable</dt><dd>{data.users.find((user) => user.id === activeCase.responsible_id)?.username ?? "Sin asignar"}</dd></div>
                <div><dt>Resumen</dt><dd>{activeCase.summary ?? "—"}</dd></div>
              </dl>
              {activeCase.emergency ? <Badge tone={activeCase.ack_by === null ? "danger" : "warning"}>{activeCase.ack_by === null ? "Emergencia sin reconocer" : `Emergencia reconocida por ${activeCase.ack_by}`}</Badge> : null}
              <CaseActions target={activeCase} users={data.users} onUpdate={updateCase} onAcknowledge={acknowledgeCase} />
              <LocalFeedback feedback={caseFeedback} />
            </> : <EmptyState title="Sin caso activo" />}
          </Card>
          <Card title="Memo del cliente">
            <p>{data.memo || "Todavía no hay memo para este cliente."}</p>
          </Card>

          <ClientMemories memories={memories} pendingRelations={pendingRelations} onResolveRelation={resolveRelation} />

          <Card title="Notas">
            {data.notes.length ? data.notes.map((entry) => <p key={entry.id}>{entry.author ?? "—"} · {entry.note}</p>) : <EmptyState title="No hay notas" />}
            <Textarea
              id="new-note"
              label="Nueva nota"
              value={note}
              disabled={mutation !== null || customerId === undefined}
              onChange={(event) => setNote(event.target.value)}
            />
            <Button disabled={mutation !== null || customerId === undefined} onClick={() => void saveNote()}>
              {mutation === "note" ? "Guardando…" : "Agregar nota"}
            </Button>
            <LocalFeedback feedback={noteFeedback} />
          </Card>

          <section aria-label="Historial">
            <h2>Historial</h2>
            <section aria-labelledby="ficha-visits-heading" className="client-ficha__history-block">
              <h3 id="ficha-visits-heading">Visitas</h3>
              <p>Historial de visitas ordenado cronológicamente</p>
              {appointments.length ? (
                <ul className="client-ficha__visits data-region">
                  {appointments.map((appointment: Appointment) => (
                    <li key={appointment.id}>
                      <a className="table__link" href={pathForRoute({ view: "agenda", appointmentId: appointment.id })}>
                        <span>{appointment.service}</span>
                        <span>{formatDateTime(appointment.starts_at)}</span>
                        <Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge>
                      </a>
                      {appointment.calendar_error ? (
                        <>
                          <StateMessage tone="danger" role="alert" title="No se pudo sincronizar el calendario" detail={`${appointment.calendar_error} Reintenta la sincronización.`} />
                          <Button variant="secondary" disabled={retryingCalendarId === appointment.id} onClick={() => void retryCalendar(appointment.id)}>
                            Reintentar calendario
                          </Button>
                        </>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : <EmptyState title="No hay visitas" />}
            </section>

            <section aria-labelledby="ficha-conversations-heading" className="client-ficha__history-block">
              <h3 id="ficha-conversations-heading">Conversaciones</h3>
              <div className={surfaceClass(history.conversations.length)}>
                <DataTable columns={conversationColumns} rows={history.conversations} rowKey={(row) => String(row.id)} />
              </div>
            </section>

            <section aria-labelledby="ficha-cases-heading" className="client-ficha__history-block">
              <h3 id="ficha-cases-heading">Casos anteriores</h3>
              <div className={surfaceClass(archivedCases.length)}>
                <DataTable columns={caseColumns} rows={archivedCases} rowKey={(row) => String(row.id)} />
              </div>
            </section>

            <section aria-labelledby="ficha-messages-heading" className="client-ficha__history-block">
              <h3 id="ficha-messages-heading">Mensajes</h3>
              <div className={surfaceClass(history.messages.length)}>
                <CollapsibleMessages total={history.messages_total} expanded={messagesExpanded} onToggle={toggleMessages}>
                  <DataTable columns={messageColumns} rows={history.messages} rowKey={(row) => String(row.id)} />
                </CollapsibleMessages>
              </div>
            </section>
          </section>
        </div>
      </div>
    </PageFrame>
  );
}
