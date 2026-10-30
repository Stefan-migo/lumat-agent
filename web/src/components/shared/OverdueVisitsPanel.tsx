import { useState } from "react";
import { CalendarDays, Check, UserRoundX } from "lucide-react";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { AppointmentClosureDialog, type AppointmentClosureOutcome } from "./AppointmentClosureDialog";
import { StateMessage } from "./StateMessage";
import { agendaPeriodLabel, formatAgendaSlot } from "./agendaTime";
import type { AgendaAppointment, BulkAppointmentCloseResponse } from "../../types";

export interface OverdueVisitsPanelProps {
  appointments: AgendaAppointment[];
  onCloseAppointment: (id: number, outcome: AppointmentClosureOutcome) => void | Promise<void>;
  onBulkClose: (ids: number[], outcome: AppointmentClosureOutcome) => Promise<BulkAppointmentCloseResponse>;
}

type DisplayedResult = { id: number; customerName: string; ok: boolean; error: string | null };

function customerName(appointment: AgendaAppointment) {
  return appointment.customer_name ?? `Cliente ${appointment.customer_id}`;
}

export function OverdueVisitsPanel({ appointments, onCloseAppointment, onBulkClose }: OverdueVisitsPanelProps) {
  const [closeTarget, setCloseTarget] = useState<AgendaAppointment | null>(null);
  const [singleOutcome, setSingleOutcome] = useState<AppointmentClosureOutcome>("completed");
  const [singleBusy, setSingleBusy] = useState(false);
  const [singleError, setSingleError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkOutcome, setBulkOutcome] = useState<AppointmentClosureOutcome | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [displayedResults, setDisplayedResults] = useState<DisplayedResult[]>([]);

  const selectedAppointments = appointments.filter((appointment) => selectedIds.includes(appointment.id));
  const selectedCustomers = selectedAppointments.map(customerName);
  const shown = appointments.length > 0 || displayedResults.length > 0;
  if (!shown) return null;

  const closeSingle = async (outcome: AppointmentClosureOutcome) => {
    if (!closeTarget || singleBusy) return;
    setSingleBusy(true);
    setSingleError(null);
    try {
      await onCloseAppointment(closeTarget.id, outcome);
      setCloseTarget(null);
    } catch (error) {
      setSingleError(error instanceof Error ? error.message : "No se pudo registrar el resultado");
    } finally {
      setSingleBusy(false);
    }
  };

  const submitBulkClose = async () => {
    // Send exactly what the confirmation dialog showed. A refetch while the dialog
    // is open can drop a row from `appointments`; sending `selectedIds` would close
    // a visit the operator no longer sees in the preview.
    const ids = selectedAppointments.map((appointment) => appointment.id);
    if (!bulkOutcome || ids.length === 0 || ids.length > 100 || bulkBusy) return;
    setBulkBusy(true);
    setBulkError(null);
    try {
      const response = await onBulkClose(ids, bulkOutcome);
      const namesById = new Map(selectedAppointments.map((appointment) => [appointment.id, customerName(appointment)]));
      setDisplayedResults(response.results.map((result) => ({
        id: result.id,
        customerName: namesById.get(result.id) ?? `Visita ${result.id}`,
        ok: result.ok,
        error: result.error,
      })));
      setSelectedIds([]);
      setBulkOpen(false);
    } catch (error) {
      setBulkError(error instanceof Error ? error.message : "No se pudo cerrar el grupo de visitas");
    } finally {
      setBulkBusy(false);
    }
  };

  const toggleSelection = (id: number, checked: boolean) => {
    setSelectedIds((current) => checked
      ? current.length < 100 && !current.includes(id) ? [...current, id] : current
      : current.filter((selectedId) => selectedId !== id));
  };

  return (
    <section aria-labelledby="overdue-visits-heading" aria-label="Visitas vencidas">
      <h2 id="overdue-visits-heading">Visitas vencidas</h2>
      {selectedIds.length > 0 ? (
        <Button onClick={() => { setBulkOutcome(null); setBulkError(null); setBulkOpen(true); }}>Cerrar visitas seleccionadas</Button>
      ) : null}
      <ul>
        {appointments.map((appointment) => {
          const name = customerName(appointment);
          const dateLabel = `${agendaPeriodLabel(appointment.local_start.slice(0, 10), appointment.timezone)} · ${formatAgendaSlot(appointment.starts_at, appointment.timezone)}`;
          return (
            <li key={appointment.id}>
              <label>
                <input
                  type="checkbox"
                  aria-label={`Seleccionar visita de ${name}`}
                  checked={selectedIds.includes(appointment.id)}
                  disabled={!selectedIds.includes(appointment.id) && selectedIds.length >= 100}
                  onChange={(event) => toggleSelection(appointment.id, event.target.checked)}
                />
                <span>{name}</span>
              </label>
              <span>{appointment.service}</span>
              <time dateTime={appointment.local_start}>{dateLabel}</time>
              <Button variant="secondary" onClick={() => { setCloseTarget(appointment); setSingleOutcome("completed"); setSingleError(null); }}>
                Cerrar visita de {name}
              </Button>
            </li>
          );
        })}
      </ul>
      {displayedResults.length > 0 ? (
        <ul aria-label="Resultados del cierre">
          {displayedResults.map((result) => (
            <li key={result.id} role={result.ok ? "status" : "alert"}>
              <span>{result.customerName}</span>
              <span>{result.ok ? "Cierre registrado" : result.error}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {closeTarget ? (
        <AppointmentClosureDialog
          open
          onClose={() => setCloseTarget(null)}
          customerName={customerName(closeTarget)}
          appointmentDateTime={closeTarget.local_start}
          dateTimeLabel={`${agendaPeriodLabel(closeTarget.local_start.slice(0, 10), closeTarget.timezone)} · ${formatAgendaSlot(closeTarget.starts_at, closeTarget.timezone)}`}
          outcome={singleOutcome}
          onOutcomeChange={setSingleOutcome}
          onSubmit={() => void closeSingle(singleOutcome)}
          mutating={singleBusy}
          feedback={singleError ? { title: "No se pudo registrar el resultado", detail: singleError } : null}
        />
      ) : null}
      <Dialog
        open={bulkOpen}
        onClose={() => { if (!bulkBusy) setBulkOpen(false); }}
        title={`Cerrar ${selectedAppointments.length} ${selectedAppointments.length === 1 ? "visita" : "visitas"}`}
        icon={CalendarDays}
      >
        <ul>
          {selectedCustomers.map((name, index) => <li key={`${selectedAppointments[index]?.id ?? index}-${name}`}>{name}</li>)}
        </ul>
        <fieldset className="appointment-detail__outcomes" disabled={bulkBusy}>
          <legend>Resultado</legend>
          <label className={bulkOutcome === "completed" ? "appointment-detail__outcome appointment-detail__outcome--selected" : "appointment-detail__outcome"}>
            <Check aria-hidden="true" />
            <span><strong>Completada</strong><small>La visita se realizó.</small></span>
            <input type="radio" name="bulk-appointment-outcome" value="completed" checked={bulkOutcome === "completed"} onChange={() => setBulkOutcome("completed")} />
          </label>
          <label className={bulkOutcome === "no_show" ? "appointment-detail__outcome appointment-detail__outcome--selected" : "appointment-detail__outcome"}>
            <UserRoundX aria-hidden="true" />
            <span><strong>No completada</strong><small>La visita no se completó.</small></span>
            <input type="radio" name="bulk-appointment-outcome" value="no_show" checked={bulkOutcome === "no_show"} onChange={() => setBulkOutcome("no_show")} />
          </label>
        </fieldset>
        {bulkError ? <StateMessage tone="danger" role="alert" title={bulkError} /> : null}
        <div className="appointment-detail__dialog-footer">
          <Button variant="secondary" disabled={bulkBusy} onClick={() => setBulkOpen(false)}>Cancelar</Button>
          <Button disabled={!bulkOutcome || selectedAppointments.length === 0 || selectedAppointments.length > 100 || bulkBusy} onClick={() => void submitBulkClose()}>
            {bulkBusy ? "Guardando…" : "Confirmar cierre"}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
