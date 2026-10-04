import { useCallback, useState } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, CalendarCheck, Check, ChevronDown, Clock3, FileText, UserRound } from 'lucide-react';
import { closeAppointment, fetchUsers, getAppointment, rescheduleAppointment } from '../../api';
import { useAsyncData, type AsyncDataState } from '../../hooks/useAsyncData';
import type { AppointmentDetail as AppointmentDetailData } from '../../types';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Dialog } from '../primitives/Dialog';
import { Input } from '../primitives/Input';
import { Select } from '../primitives/Select';
import { Card } from '../primitives/Card';
import { Avatar } from '../primitives/Avatar';
import { Icon } from '../primitives/Icon';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';
import { appointmentStatusLabel, appointmentStatusTone } from '../shared/toneMaps';
import { composeAgendaTime } from '../shared/agendaTime';
import { pathForRoute } from '../domain/panelRoutes';

export interface AppointmentDetailProps {
  appointmentId?: number;
  data?: AppointmentDetailData | null;
  state?: AsyncDataState;
  onRetry?: () => void;
}

const DATE_TIME_FORMAT = new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' });
const DATE_LONG_FORMAT = new Intl.DateTimeFormat('es-CL', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' });
const DATE_DAY_FORMAT = new Intl.DateTimeFormat('es-CL', { day: '2-digit', timeZone: 'UTC' });
const DATE_MONTH_FORMAT = new Intl.DateTimeFormat('es-CL', { month: 'short', timeZone: 'UTC' });
const TIME_FORMAT = new Intl.DateTimeFormat('es-CL', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC' });

function stateMessage(state: AsyncDataState) {
  if (state === 'loading') return <StateMessage tone="info" role="status" spinner title="Cargando visita" />;
  if (state === 'denied') return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver esta visita" />;
  if (state === 'error') return <StateMessage tone="danger" role="alert" title="No pudimos cargar la visita" detail="Reintenta para recuperar los datos." />;
  return null;
}

export function AppointmentDetail({ appointmentId, data: controlledData, state: controlledState, onRetry }: AppointmentDetailProps) {
  const [closeOpen, setCloseOpen] = useState(false);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [technicians, setTechnicians] = useState<{ id: number; username: string }[]>([]);
  const [rescheduleForm, setRescheduleForm] = useState({ local_date: '', local_time: '', duration_minutes: '60', technician_id: '' });
  const [mutating, setMutating] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; title: string; detail?: string } | null>(null);
  const fetchDetail = useCallback(() => {
    if (appointmentId === undefined) throw new Error('appointment id is required');
    return getAppointment(appointmentId);
  }, [appointmentId]);
  const fetched = useAsyncData(fetchDetail, appointmentId !== undefined && controlledData === undefined);
  const detail = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? 'ready' : fetched.state);
  const retry = onRetry ?? fetched.retry;
  const close = async (outcome: 'completed' | 'no_show') => {
    if (!detail || mutating) return;
    setMutating(true);
    setFeedback(null);
    try {
      await closeAppointment(detail.appointment.id, outcome);
      setCloseOpen(false);
      setFeedback({ tone: 'success', title: outcome === 'completed' ? 'Visita completada' : 'Visita marcada como no asistida' });
      await retry();
    } catch (error) {
      setFeedback({ tone: 'danger', title: 'No se pudo registrar el resultado', detail: error instanceof Error ? error.message : 'Intenta nuevamente.' });
    } finally {
      setMutating(false);
    }
  };
  const reschedule = async () => {
    if (!detail || mutating) return;
    if (!rescheduleForm.technician_id || !rescheduleForm.local_date || !rescheduleForm.local_time || Number(rescheduleForm.duration_minutes) <= 0) {
      setFeedback({ tone: 'danger', title: 'Completa todos los campos de la reprogramación' });
      return;
    }
    setMutating(true);
    setFeedback(null);
    try {
      await rescheduleAppointment(detail.appointment.id, { ...composeAgendaTime(rescheduleForm.local_date, rescheduleForm.local_time, detail.appointment.timezone), duration_minutes: Number(rescheduleForm.duration_minutes), technician_id: Number(rescheduleForm.technician_id) });
      setRescheduleOpen(false);
      setFeedback({ tone: 'success', title: 'Visita reprogramada' });
      await retry();
    } catch (error) {
      setFeedback({ tone: 'danger', title: 'No se pudo reprogramar la visita', detail: error instanceof Error ? error.message : 'Intenta nuevamente.' });
    } finally {
      setMutating(false);
    }
  };

  if (!detail) {
    return <PageFrame title="Detalle de visita" meta="Datos y ciclo de vida de la visita" state={stateMessage(state)}>
      {state === 'error' ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}
    </PageFrame>;
  }

  const { appointment, customer, conversation_summary: summary } = detail;
  const localStart = new Date(`${appointment.local_start.slice(0, 16)}:00Z`);
  const technicianLabel = appointment.technician_id ? `Técnico #${appointment.technician_id}` : 'Técnico no asignado';
  return <PageFrame className="appointment-detail-page" eyebrow={<><button type="button" className="appointment-detail__back" onClick={() => window.history.back()}><Icon icon={ArrowLeft} />Volver a agenda</button><span>DETALLE DE VISITA</span></>} title={appointment.service} subtitle="Información y seguimiento de la visita."
    titleAdornment={<Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge>}
    actions={appointment.status === 'booked' ? <>
        <Button variant="secondary" aria-label="Reprogramar" title="Reprogramar" onClick={() => { const start = appointment.local_start; setRescheduleForm({ local_date: start.slice(0, 10), local_time: start.slice(11, 16), duration_minutes: String(appointment.duration_minutes ?? 60), technician_id: String(appointment.technician_id ?? '') }); setFeedback(null); setRescheduleOpen(true); void fetchUsers().then((response) => setTechnicians(response.users.filter((user) => user.role === 'tecnico'))); }}><Icon icon={CalendarDays} /><span>Reprogramar</span></Button>
        <Button variant="primary" aria-label="Cerrar visita" title="Cerrar visita" onClick={() => { setFeedback(null); setCloseOpen(true); }}><Icon icon={Check} /><span>Cerrar visita</span></Button>
      </> : null} state={stateMessage(state)}>
    {feedback?.tone === 'success' ? <StateMessage tone="success" role="status" title={feedback.title} /> : null}
    <div className="detail-region">
      <section className="detail-region__rail" aria-label="Información de la visita">
        <Card title="Programación" icon={CalendarDays} className="appointment-detail__schedule">
          <div className="appointment-detail__schedule-main">
            <div className="appointment-detail__date-block"><strong>{DATE_DAY_FORMAT.format(localStart)}</strong><span>{DATE_MONTH_FORMAT.format(localStart).replace('.', '').toUpperCase()}</span></div>
            <div className="appointment-detail__date-copy"><strong>{DATE_LONG_FORMAT.format(localStart)}</strong><span>{localStart.getFullYear()}</span></div>
            <div className="appointment-detail__time"><Icon icon={Clock3} /><strong>{TIME_FORMAT.format(localStart)}</strong><span>Hora de inicio</span></div>
          </div>
          <div className="appointment-detail__sync"><Icon icon={CalendarCheck} /><span>Estado del calendario no disponible</span></div>
        </Card>
        <Card title="Cliente" icon={UserRound} className="appointment-detail__people">
          <div className="appointment-detail__identity"><Avatar name={customer.name ?? 'Cliente sin nombre'} /><div><strong>{customer.name ?? 'Cliente sin nombre'}</strong><a href={pathForRoute({ view: 'clients', clientId: customer.id })}>Ver ficha del cliente <Icon icon={ArrowRight} /></a></div></div>
          <div className="appointment-detail__identity appointment-detail__technician"><Avatar name={technicianLabel} /><div><h3>Técnico asignado</h3><strong>{technicianLabel}</strong><span>Responsable de la visita</span></div></div>
        </Card>
        <Card title="Resumen" icon={FileText} className="appointment-detail__summary">
          <div className="appointment-detail__summary-row"><span>Motivo</span><strong>{appointment.service}</strong></div>
          <div className="appointment-detail__summary-row"><span>Estado</span><Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge></div>
        </Card>
      </section>
      <div className="detail-region__main">
        {summary ? <Card title="Resumen de la conversación"><p>{summary}</p></Card> : null}
        <Card title="Historial de la visita" icon={FileText} className="appointment-detail__history">
          {appointment.history.length ? <ol aria-label="Historial de la visita">
            {appointment.history.map((entry) => <li key={entry.id}>
              <span className="appointment-detail__history-icon"><Icon icon={CalendarCheck} /></span>
              <div className="appointment-detail__history-copy"><strong>{entry.action === 'booked' || entry.action === 'created' ? 'Visita reservada' : entry.action}</strong>
                <time dateTime={entry.created_at}>{DATE_TIME_FORMAT.format(new Date(entry.created_at))}</time>
                <p>{entry.action === 'booked' || entry.action === 'created' ? `Se creó la reserva con estado «${appointmentStatusLabel(entry.to_status)}».` : `${entry.actor} registró el cambio de ${entry.from_status ?? '—'} a ${entry.to_status}.`}</p>
                {!entry.from_status ? <Badge tone="success">Registro inicial</Badge> : null}
                <details><summary><Icon icon={ChevronDown} />Ver detalles</summary><div><span>Responsable: {entry.actor}</span><span>Estado: {entry.from_status ?? '—'} → {entry.to_status}</span>{entry.details ? <pre>{JSON.stringify(entry.details, null, 2)}</pre> : null}</div></details>
              </div>
            </li>)}
          </ol> : <p>No hay cambios registrados.</p>}
        </Card>
      </div>
    </div>
    <Dialog open={closeOpen} onClose={() => { if (!mutating) setCloseOpen(false); }} title="Cerrar visita">
      <p>Registra el resultado de la visita. Esta acción no se puede revertir desde la agenda.</p>
      {feedback?.tone === 'danger' ? <StateMessage tone="danger" role="alert" title={feedback.title} detail={feedback.detail} /> : null}
      <Button variant="secondary" disabled={mutating} onClick={() => void close('completed')}>Completar</Button>
      <Button variant="secondary" disabled={mutating} onClick={() => void close('no_show')}>No asistió</Button>
    </Dialog>
    <Dialog open={rescheduleOpen} onClose={() => { if (!mutating) setRescheduleOpen(false); }} title="Reprogramar visita">
      <Input label="Fecha local" type="date" value={rescheduleForm.local_date} onChange={(event) => setRescheduleForm((form) => ({ ...form, local_date: event.target.value }))} />
      <Input label="Hora local" type="time" value={rescheduleForm.local_time} onChange={(event) => setRescheduleForm((form) => ({ ...form, local_time: event.target.value }))} />
      <Input label="Duración (minutos)" type="number" min="1" value={rescheduleForm.duration_minutes} onChange={(event) => setRescheduleForm((form) => ({ ...form, duration_minutes: event.target.value }))} />
      <Select label="Técnico" value={rescheduleForm.technician_id} onChange={(event) => setRescheduleForm((form) => ({ ...form, technician_id: event.target.value }))} options={[{ value: '', label: 'Selecciona un técnico' }, ...technicians.map((user) => ({ value: String(user.id), label: user.username }))]} />
      {feedback?.tone === 'danger' ? <StateMessage tone="danger" role="alert" title={feedback.title} detail={feedback.detail} /> : null}
      <Button variant="secondary" disabled={mutating} onClick={() => void reschedule()}>{mutating ? 'Reprogramando…' : 'Confirmar reprogramación'}</Button>
    </Dialog>
  </PageFrame>;
}
