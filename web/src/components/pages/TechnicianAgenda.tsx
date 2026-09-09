import { useCallback } from 'react';
import { fetchTechnicianAgenda } from '../../api';
import type { TechnicianAppointment } from '../../types';
import { useAsyncData, type AsyncDataState } from '../../hooks/useAsyncData';
import { EmptyState } from '../shared/EmptyState';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';

function localTime(row: TechnicianAppointment) {
  return new Intl.DateTimeFormat('es-CL', { timeZone: row.timezone, dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.starts_at));
}

function stateMessage(state: AsyncDataState, retry: () => void) {
  if (state === 'loading') return <StateMessage tone="info" role="status" spinner title="Cargando agenda" />;
  if (state === 'denied') return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver la agenda" />;
  if (state === 'error') return <div><StateMessage tone="danger" role="alert" title="No pudimos cargar la agenda" /><button type="button" onClick={retry}>Reintentar</button></div>;
  return null;
}

export function TechnicianAgenda() {
  const load = useCallback(() => fetchTechnicianAgenda().then((response) => response.appointments), []);
  const { data, state, retry } = useAsyncData(load);
  const appointments = data ?? [];
  return (
    <PageFrame title="Agenda técnica" meta={state === 'ready' ? `${appointments.length} visitas` : undefined} state={stateMessage(state, retry)}>
      {state === 'loading' || state === 'error' || state === 'denied' ? null : state === 'empty' ? <EmptyState title="No hay visitas asignadas" description="No tienes visitas en tu agenda." /> : (
        <div className="technician-agenda" style={{ display: 'grid', gap: 'var(--space-3)' }}>
          {appointments.map((row) => <article key={row.id} style={{ display: 'grid', gap: 'var(--space-2)', padding: 'var(--space-4)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}>
            <h2>{row.service}</h2>
            <time dateTime={row.starts_at}>{localTime(row)}</time>
            <strong>{row.customer.name ?? 'Cliente sin nombre'}</strong>
            <span>{row.customer.address ?? 'Dirección no registrada'}</span>
            <span>{row.customer.comuna ?? 'Comuna no registrada'}</span>
            <a href={`tel:${row.customer.phone ?? ''}`}>{row.customer.phone ?? 'Teléfono no registrado'}</a>
            {row.case_summary ? <p>{row.case_summary}</p> : null}
          </article>)}
        </div>
      )}
    </PageFrame>
  );
}
