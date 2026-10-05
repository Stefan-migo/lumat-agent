import { CalendarDays, Check, CircleCheck, UserRoundX } from "lucide-react";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { StateMessage } from "./StateMessage";

export type AppointmentClosureOutcome = "completed" | "no_show";

export interface AppointmentClosureDialogProps {
  open: boolean;
  customerName: string;
  appointmentDateTime: string;
  dateTimeLabel: string;
  outcome: AppointmentClosureOutcome;
  mutating: boolean;
  feedback?: { title: string; detail?: string } | null;
  onClose: () => void;
  onOutcomeChange: (outcome: AppointmentClosureOutcome) => void;
  onSubmit: () => void;
}

export function AppointmentClosureDialog({
  open,
  customerName,
  appointmentDateTime,
  dateTimeLabel,
  outcome,
  mutating,
  feedback,
  onClose,
  onOutcomeChange,
  onSubmit,
}: AppointmentClosureDialogProps) {
  return (
    <Dialog open={open} onClose={() => { if (!mutating) onClose(); }} title="Cerrar visita" icon={CircleCheck} description="Selecciona el resultado de la visita.">
      <div className="appointment-detail__selected-visit"><Icon icon={CalendarDays} /><div><strong>{customerName}</strong><time dateTime={appointmentDateTime}>{dateTimeLabel}</time><span>Visita seleccionada</span></div></div>
      <fieldset className="appointment-detail__outcomes" disabled={mutating}>
        <legend>Resultado</legend>
        <label className={outcome === "completed" ? "appointment-detail__outcome appointment-detail__outcome--selected" : "appointment-detail__outcome"}>
          <Icon icon={Check} />
          <span><strong>Completada</strong><small>La visita se realizó.</small></span>
          <input type="radio" name="appointment-outcome" value="completed" checked={outcome === "completed"} onChange={() => onOutcomeChange("completed")} />
        </label>
        <label className={outcome === "no_show" ? "appointment-detail__outcome appointment-detail__outcome--selected" : "appointment-detail__outcome"}>
          <Icon icon={UserRoundX} />
          <span><strong>No completada</strong><small>La visita no se completó.</small></span>
          <input type="radio" name="appointment-outcome" value="no_show" checked={outcome === "no_show"} onChange={() => onOutcomeChange("no_show")} />
        </label>
      </fieldset>
      <p className="appointment-detail__closure-warning">Este cierre no se puede revertir desde la agenda.</p>
      {feedback ? <StateMessage tone="danger" role="alert" title={feedback.title} detail={feedback.detail} /> : null}
      <div className="appointment-detail__dialog-footer">
        <Button variant="secondary" disabled={mutating} onClick={onClose}>Cancelar</Button>
        <Button disabled={mutating} onClick={onSubmit}>{mutating ? "Guardando…" : "Confirmar cierre"}</Button>
      </div>
    </Dialog>
  );
}
