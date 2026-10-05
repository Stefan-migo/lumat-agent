import { CalendarClock, CalendarDays, Clock3, Timer, UserRound } from "lucide-react";
import type { UserRef } from "../../types";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { StateMessage } from "./StateMessage";

export interface AppointmentRescheduleForm {
  local_date: string;
  local_time: string;
  duration_minutes: string;
  technician_id: string;
}

type AppointmentSchedule = {
  local_start: string;
  timezone: string;
  duration_minutes?: number;
};

interface AppointmentRescheduleDialogProps {
  open: boolean;
  appointment: AppointmentSchedule;
  technicianLabel: string;
  technicians: UserRef[];
  form: AppointmentRescheduleForm;
  mutating: boolean;
  feedback?: { title: string; detail?: string } | null;
  onClose: () => void;
  onChange: (field: keyof AppointmentRescheduleForm, value: string) => void;
  onSubmit: () => void;
}

const DATE_LONG_FORMAT = new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
const TIME_FORMAT = new Intl.DateTimeFormat("es-CL", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" });

export function AppointmentRescheduleDialog({
  open,
  appointment,
  technicianLabel,
  technicians,
  form,
  mutating,
  feedback,
  onClose,
  onChange,
  onSubmit,
}: AppointmentRescheduleDialogProps) {
  const localStart = new Date(`${appointment.local_start.slice(0, 16)}:00Z`);

  return (
    <Dialog open={open} onClose={() => { if (!mutating) onClose(); }} title="Reprogramar visita" icon={CalendarClock} description="Actualiza la fecha, el horario y el técnico asignado.">
      <section className="appointment-detail__current-schedule" aria-labelledby="appointment-current-schedule">
        <h3 id="appointment-current-schedule">Programación actual</h3>
        <strong>{DATE_LONG_FORMAT.format(localStart)} · {localStart.getFullYear()} · {TIME_FORMAT.format(localStart)}</strong>
        <span>{appointment.duration_minutes ?? 60} min · {technicianLabel}</span>
      </section>
      <section className="appointment-detail__new-schedule" aria-labelledby="appointment-new-schedule">
        <h3 id="appointment-new-schedule">Nueva programación</h3>
        <div className="appointment-detail__reschedule-fields">
          <Input label="Fecha" icon={CalendarDays} type="date" value={form.local_date} onChange={(event) => onChange("local_date", event.target.value)} />
          <Input label="Hora local" icon={Clock3} type="time" value={form.local_time} onChange={(event) => onChange("local_time", event.target.value)} />
          <Input label="Duración" icon={Timer} type="number" min="1" value={form.duration_minutes} onChange={(event) => onChange("duration_minutes", event.target.value)} />
          <div className="appointment-detail__reschedule-technician"><Icon icon={UserRound} size="sm" /><Select label="Técnico" value={form.technician_id} onChange={(event) => onChange("technician_id", event.target.value)} options={[{ value: "", label: "Selecciona un técnico" }, ...technicians.map((technician) => ({ value: String(technician.id), label: technician.username }))]} /></div>
        </div>
        <p>La fecha y la hora corresponden al horario local de la agenda.</p>
      </section>
      {feedback ? <StateMessage tone="danger" role="alert" title={feedback.title} detail={feedback.detail} /> : null}
      <div className="appointment-detail__dialog-footer">
        <Button variant="secondary" disabled={mutating} onClick={onClose}>Cancelar</Button>
        <Button disabled={mutating} onClick={onSubmit}><Icon icon={CalendarDays} size="sm" />{mutating ? "Reprogramando…" : "Confirmar reprogramación"}</Button>
      </div>
    </Dialog>
  );
}
