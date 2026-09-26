import { useCallback, useState } from 'react';
import { closeAppointment, getAppointment } from '../../api';
import { useAsyncData, type AsyncDataState } from '../../hooks/useAsyncData';
import type { AppointmentDetail as AppointmentDetailData } from '../../types';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Dialog } from '../primitives/Dialog';
import { Card } from '../primitives/Card';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';
import { appointmentStatusLabel, appointmentStatusTone } from '../shared/toneMaps';
import { pathForRoute } from '../domain/panelRoutes';

export interface AppointmentDetailProps {
  appointmentId?: number;
  data?: AppointmentDetailData | null;
  state?: AsyncDataState;
  onRetry?: () => void;
}

const DATE_TIME_FORMAT = new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' });

function stateMessage(state: AsyncDataState) {
  if (state === 'loading') return <StateMessage tone="info" role="status" spinner title="Cargando visita" />;
  if (state === 'denied') return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver esta visita" />;
  if (state === 'error') return <StateMessage tone="danger" role="alert" title="No pudimos cargar la visita" detail="Reintenta para recuperar los datos." />;
  return null;
}

export function AppointmentDetail({ appointmentId, data: controlledData, state: controlledState, onRetry }: AppointmentDetailProps) {
  const [closeOpen, setCloseOpen] = useState(false);
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

  if (!detail) {
    return <PageFrame title="Detalle de visita" meta="Datos y ciclo de vida de la visita" state={stateMessage(state)}>
      {state === 'error' ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}
    </PageFrame>;
  }

  const { appointment, customer, conversation_summary: summary } = detail;
  return <PageFrame title="Detalle de visita" meta="Datos y ciclo de vida de la visita" actions={<><Button variant="secondary" onClick={() => window.history.back()}>Volver a la agenda</Button>{appointment.status === 'booked' ? <Button variant="secondary" onClick={() => { setFeedback(null); setCloseOpen(true); }}>Cerrar visita</Button> : null}</>} state={stateMessage(state)}>
    {feedback?.tone === 'success' ? <StateMessage tone="success" role="status" title={feedback.title} /> : null}
    {feedback?.tone === 'danger' ? <StateMessage tone="danger" role="alert" title={feedback.title} detail={feedback.detail} /> : null}
    <div className="detail-region">
      <section className="detail-region__rail" aria-label="Datos de la visita">
        <Card title="Visita">
          <dl className="detail-region__facts">
            <div><dt>Cliente</dt><dd><a href={pathForRoute({ view: 'clients', clientId: customer.id })}>{customer.name ?? 'Cliente sin nombre'}</a></dd></div>
            <div><dt>Motivo de visita</dt><dd>{appointment.service}</dd></div>
            <div><dt>Estado</dt><dd><Badge tone={appointmentStatusTone(appointment.status)}>{appointmentStatusLabel(appointment.status)}</Badge></dd></div>
            <div><dt>Fecha y hora</dt><dd>{DATE_TIME_FORMAT.format(new Date(appointment.starts_at))}</dd></div>
          </dl>
        </Card>
      </section>
      <div className="detail-region__main">
        {summary ? <Card title="Resumen de la conversación"><p>{summary}</p></Card> : null}
        <Card title="Historial de la visita">
          {appointment.history.length ? <ol aria-label="Historial de la visita">
            {appointment.history.map((entry) => <li key={entry.id}>
              <time dateTime={entry.created_at}>{DATE_TIME_FORMAT.format(new Date(entry.created_at))}</time>
              {' · '}{entry.actor} · {entry.action} · {entry.from_status ?? '—'} → {entry.to_status}
              {entry.details ? <pre>{JSON.stringify(entry.details, null, 2)}</pre> : null}
            </li>)}
          </ol> : <p>No hay cambios registrados.</p>}
        </Card>
      </div>
    </div>
    <Dialog open={closeOpen} onClose={() => { if (!mutating) setCloseOpen(false); }} title="Cerrar visita">
      <p>Registra el resultado de la visita. Esta acción no se puede revertir desde la agenda.</p>
      <Button variant="secondary" disabled={mutating} onClick={() => void close('completed')}>Completar</Button>
      <Button variant="secondary" disabled={mutating} onClick={() => void close('no_show')}>No asistió</Button>
    </Dialog>
  </PageFrame>;
}
