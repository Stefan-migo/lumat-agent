import { useCallback, useState } from "react";
import { addClientNote, ApiError, apiFetch, changeClientState, resolveMemoryRelation } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Appointment, ClientFichaResponse, CustomerState, Memory, MemoryRelation, MemoryRelationKind, MemoriesResponse, PendingMemoryRelationsResponse, VisitHistoryEvent } from "../../types";
import { ClientMemories } from "../domain/ClientMemories";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import {
  caseStatusLabel,
  caseStatusTone,
  conversationLabel,
  customerStateLabel,
  customerStateTone,
  directionLabel,
} from "../shared/toneMaps";

export interface ClientFichaProps {
  customerId?: number;
  data?: ClientFichaResponse;
  memories?: Memory[];
  isSaving?: boolean;
  onRetryCalendar?: (appointmentId: number) => void;
}

type FichaState = AsyncDataState | "fatal-error";

function stateMessage(state: FichaState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando ficha" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error" || state === "fatal-error") {
    return <StateMessage tone="danger" role="alert" title="No pudimos cargar la ficha" detail="Reintenta para recuperar los datos." />;
  }
  return null;
}

export function ClientFicha({ customerId, data: controlledData, memories: controlledMemories, isSaving = false, onRetryCalendar }: ClientFichaProps) {
  const [retryingCalendarId, setRetryingCalendarId] = useState<number | null>(null);
  const [refreshed, setRefreshed] = useState<{ ficha: ClientFichaResponse; memories: Memory[]; pendingRelations: MemoryRelation[] } | null>(null);
  const [selectedState, setSelectedState] = useState<CustomerState | null>(null);
  const [note, setNote] = useState("");
  const [mutation, setMutation] = useState<"state" | "note" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "danger"; title: string; detail?: string } | null>(null);
  const fetchFicha = useCallback(async () => {
    if (customerId === undefined) throw new Error("customer id is required");
    const [ficha, memoryResponse, pendingResponse] = await Promise.all([
      apiFetch<ClientFichaResponse>(`/panel/api/clients/${customerId}`),
      apiFetch<MemoriesResponse>(`/panel/api/clients/${customerId}/memories`),
      apiFetch<PendingMemoryRelationsResponse>(`/panel/api/clients/${customerId}/memory-relations/pending`),
    ]);
    return { ficha, memories: memoryResponse.memories, pendingRelations: pendingResponse.relations };
  }, [customerId]);
  const fetched = useAsyncData(fetchFicha, controlledData === undefined);
  const data = refreshed?.ficha ?? controlledData ?? fetched.data?.ficha;
  const memories = refreshed?.memories ?? controlledMemories ?? fetched.data?.memories ?? [];
  const pendingRelations = refreshed?.pendingRelations ?? fetched.data?.pendingRelations ?? [];
  const state: FichaState = controlledData ? "ready" : fetched.state;

  if (!data) {
    return <PageFrame title="Ficha de cliente" state={stateMessage(state)}><EmptyState title="Cargando ficha" /></PageFrame>;
  }

  const { customer, history } = data;
  const appointments = history.appointments ?? [];
  const visitHistory = history.visit_history ?? [];
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
  const safeError = (error: unknown, action: "estado" | "nota") => {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return { title: `No tienes permiso para guardar ${action}` };
    if (error instanceof ApiError && (error.status === 400 || error.status === 422)) return { title: `Revisa el ${action} e inténtalo de nuevo` };
    return { title: `No pudimos guardar ${action}`, detail: "Inténtalo nuevamente." };
  };
  const saveState = async () => {
    if (customerId === undefined || !selectedState || mutation) return;
    setMutation("state"); setFeedback(null);
    try { await changeClientState(customerId, selectedState); await refresh(); setFeedback({ tone: "success", title: "Estado guardado" }); }
    catch (error) { setFeedback({ tone: "danger", ...safeError(error, "estado") }); }
    finally { setMutation(null); }
  };
  const saveNote = async () => {
    if (customerId === undefined || !note.trim() || mutation) {
      if (!note.trim()) setFeedback({ tone: "danger", title: "La nota no puede estar vacía" });
      return;
    }
    setMutation("note"); setFeedback(null);
    try { await addClientNote(customerId, note.trim()); await refresh(); setNote(""); setFeedback({ tone: "success", title: "Nota agregada" }); }
    catch (error) { setFeedback({ tone: "danger", ...safeError(error, "nota") }); }
    finally { setMutation(null); }
  };
  const resolveRelation = async (relationId: number, relation: MemoryRelationKind) => {
    if (customerId === undefined) return;
    await resolveMemoryRelation(customerId, relationId, relation);
    await refresh();
  };
  const conversationColumns: Column<(typeof history.conversations)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "state", header: "Estado", render: (row) => conversationLabel(row.state) },
    { key: "summary", header: "Resumen", render: (row) => row.summary ?? "—" },
    { key: "created", header: "Creada", render: (row) => row.created_at?.slice(0, 10) ?? "—" },
  ];
  const caseColumns: Column<(typeof history.cases)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "service", header: "Servicio", render: (row) => row.service },
    { key: "priority", header: "Prioridad", render: (row) => row.priority },
    { key: "status", header: "Estado", render: (row) => <Badge tone={caseStatusTone(row.status)}>{caseStatusLabel(row.status)}</Badge> },
    { key: "summary", header: "Resumen", render: (row) => row.summary ?? "—" },
  ];
  const messageColumns: Column<(typeof history.messages)[number]>[] = [
    { key: "id", header: "#", render: (row) => `#${row.id}` },
    { key: "direction", header: "Dirección", render: (row) => directionLabel(row.direction) },
    { key: "msg_type", header: "Tipo", render: (row) => row.msg_type },
    { key: "text", header: "Mensaje", render: (row) => `${row.text ?? "—"}${row.media_url ? " 📎" : ""}` },
    { key: "created", header: "Fecha", render: (row) => row.created_at?.slice(0, 10) ?? "—" },
  ];

  return (
    <PageFrame
      title={`Ficha: ${customer.name ?? customer.phone_e164 ?? "—"}`}
      meta={`${customer.phone_e164 ?? "—"} · Estado: ${customerStateLabel(customer.state)}`}
      state={<>{stateMessage(state)}{feedback ? <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.title} detail={feedback.detail} /> : null}</>}
    >
      <section aria-label="Resumen del cliente">
        <Card>
          <p>{customer.phone_e164 ?? "—"}</p>
          <Badge tone={customerStateTone(customer.state)}>{customerStateLabel(customer.state)}</Badge>
          <label htmlFor="client-state">Estado del cliente</label>
          <select id="client-state" value={selectedState ?? customer.state} disabled={mutation !== null || customerId === undefined} onChange={(event) => setSelectedState(event.target.value as CustomerState)}>
            {(data.states ?? []).map((option) => <option key={option} value={option}>{customerStateLabel(option)}</option>)}
          </select>
          <button type="button" disabled={mutation !== null || customerId === undefined || !selectedState || selectedState === customer.state} onClick={() => void saveState()}>{mutation === "state" ? "Guardando…" : "Guardar estado"}</button>
          <p>Consentimiento: {customer.consent_status ? "Sí" : "No"}</p>
          {customer.email ? <p>{customer.email}</p> : null}
          {customer.comuna ? <p>{customer.comuna}</p> : null}
          {customer.address ? <p>{customer.address}</p> : null}
          <p>Creado: {customer.created_at?.slice(0, 10) ?? "—"}</p>
        </Card>
      </section>

      <Card title="Memo del cliente">
        <p>{data.memo || "Todavía no hay memo para este cliente."}</p>
        <Badge tone="neutral">customer_memo</Badge>
      </Card>

      <ClientMemories memories={memories} customerName={customer.name} pendingRelations={pendingRelations} onResolveRelation={resolveRelation} />

      <Card title="Notas">
        {data.notes.length ? data.notes.map((note) => <p key={note.id}>{note.author ?? "—"} · {note.note}</p>) : <EmptyState title="No hay notas" />}
        <label htmlFor="new-note">Nueva nota</label>
        <textarea id="new-note" value={note} disabled={mutation !== null || customerId === undefined} onChange={(event) => setNote(event.target.value)} />
        <button type="button" disabled={mutation !== null || customerId === undefined} onClick={() => void saveNote()}>{mutation === "note" ? "Guardando…" : "Agregar nota"}</button>
      </Card>

      <Card title="Historial">
        <h3>Visitas</h3>
        <p>Historial de visitas ordenado cronológicamente</p>
        {appointments.length ? appointments.map((appointment: Appointment) => (
          <div key={appointment.id}>
            <p>{appointment.service} · {appointment.starts_at.slice(0, 16)} · {appointment.status === "cancelled" ? "Cancelada" : "Agendada"}</p>
            {appointment.calendar_error ? (
              <StateMessage tone="danger" role="alert" title="No se pudo sincronizar el calendario" detail={`${appointment.calendar_error} Reintenta la sincronización.`} />
            ) : null}
            {appointment.calendar_error ? <button type="button" disabled={retryingCalendarId === appointment.id} onClick={() => void retryCalendar(appointment.id)}>Reintentar calendario</button> : null}
          </div>
        )) : <EmptyState title="No hay visitas" />}
        {visitHistory.length ? <ol aria-label="Ciclo de vida de visitas">{visitHistory.map((event: VisitHistoryEvent) => <li key={event.id}>{event.created_at?.slice(0, 16) ?? "—"} · {event.action === "cancelled" ? "Cancelada" : "Agendada"} · {event.actor}</li>)}</ol> : null}
        <h3>Conversaciones</h3>
        <DataTable columns={conversationColumns} rows={history.conversations} rowKey={(row) => String(row.id)} />
        <h3>Casos</h3>
        <DataTable columns={caseColumns} rows={history.cases} rowKey={(row) => String(row.id)} />
        <h3>Mensajes</h3>
        <DataTable columns={messageColumns} rows={history.messages} rowKey={(row) => String(row.id)} />
      </Card>

      {isSaving ? <p role="status">Guardando estado…</p> : null}
    </PageFrame>
  );
}
