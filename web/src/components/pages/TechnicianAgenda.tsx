import { useCallback } from 'react';
import { fetchTechnicianAgenda } from '../../api';
import type { TechnicianAppointment } from '../../types';
import { useAsyncData, type AsyncDataState } from '../../hooks/useAsyncData';
import { Button } from '../primitives/Button';
import { EmptyState } from '../shared/EmptyState';
import { PageFrame } from '../shared/PageFrame';
import { StateMessage } from '../shared/StateMessage';

/** Technician agenda (TECH-AGENDA-1).
 *
 * The endpoint returns past, today and future appointments in one chronological
 * list, so the reading work belongs here: the list splits at today and groups by
 * the appointment's own local day. A technician scans by "when" and then "what",
 * which is why the slot leads each card and the day carries the heading. */

/** 24-hour: an agenda slot must be unambiguous and fit a phone width, and a
 *  range rendered as "03:00 p. m. – 04:00 p. m." repeats the meridiem. */
const clockFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('es-CL', { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });

/** `en-CA` yields YYYY-MM-DD, which is directly comparable as a string. */
const dayKeyFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' });

const dayLabelFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('es-CL', { timeZone, weekday: 'long', day: 'numeric', month: 'long' });

/** Local calendar day of an instant in the appointment's own zone. */
function dayKey(iso: string, timezone: string) {
  return dayKeyFormat(timezone).format(new Date(iso));
}

function clock(iso: string, timezone: string) {
  return clockFormat(timezone).format(new Date(iso));
}

interface DayGroup {
  key: string;
  label: string;
  rows: TechnicianAppointment[];
}

/** Chronological day groups. Today and tomorrow are named; the rest are dated. */
function groupByDay(rows: TechnicianAppointment[], now: Date): DayGroup[] {
  const nowIso = now.toISOString();
  const tomorrowIso = new Date(now.getTime() + 86_400_000).toISOString();
  const groups: DayGroup[] = [];
  for (const row of rows) {
    const key = dayKey(row.starts_at, row.timezone);
    const current = groups[groups.length - 1];
    if (current && current.key === key) {
      current.rows.push(row);
      continue;
    }
    const label = key === dayKey(nowIso, row.timezone)
      ? 'Hoy'
      : key === dayKey(tomorrowIso, row.timezone)
        ? 'Mañana'
        : capitalize(dayLabelFormat(row.timezone).format(new Date(row.starts_at)));
    groups.push({ key, label, rows: [row] });
  }
  return groups;
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/** Today stays with the upcoming work: it is still today's round. */
function splitAtToday(rows: TechnicianAppointment[], now: Date) {
  const nowIso = now.toISOString();
  const upcoming: TechnicianAppointment[] = [];
  const past: TechnicianAppointment[] = [];
  for (const row of rows) {
    (dayKey(row.starts_at, row.timezone) < dayKey(nowIso, row.timezone) ? past : upcoming).push(row);
  }
  return { upcoming, past };
}

function stateMessage(state: AsyncDataState, retry: () => void) {
  if (state === 'loading') return <StateMessage tone="info" role="status" spinner title="Cargando agenda" />;
  if (state === 'denied') return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver la agenda" />;
  if (state === 'error') return <div className="technician-agenda__error"><StateMessage tone="danger" role="alert" title="No pudimos cargar la agenda" /><Button variant="secondary" onClick={retry}>Reintentar</Button></div>;
  return null;
}

function AppointmentCard({ row }: { row: TechnicianAppointment }) {
  return (
    <article className="technician-agenda__item">
      <p className="technician-agenda__slot">
        <time dateTime={row.starts_at}>{clock(row.starts_at, row.timezone)}</time>
        <span aria-hidden="true">–</span>
        <time dateTime={row.ends_at}>{clock(row.ends_at, row.timezone)}</time>
      </p>
      <p className="technician-agenda__service">{row.service}</p>
      <strong>{row.customer.name ?? 'Cliente sin nombre'}</strong>
      <span>{row.customer.address ?? 'Dirección no registrada'}</span>
      <span>{row.customer.comuna ?? 'Comuna no registrada'}</span>
      {row.customer.phone
        ? <Button className="technician-agenda__call" variant="secondary" href={`tel:${row.customer.phone}`}>{row.customer.phone}</Button>
        : <span>Teléfono no registrado</span>}
      {row.case_summary ? <p>{row.case_summary}</p> : null}
    </article>
  );
}

function DayGroups({ groups }: { groups: DayGroup[] }) {
  return groups.map((group) => (
    <section key={group.key} className="technician-agenda__day" aria-labelledby={`technician-day-${group.key}`}>
      <h3 id={`technician-day-${group.key}`} className="technician-agenda__day-label">{group.label}</h3>
      {group.rows.map((row) => <AppointmentCard key={row.id} row={row} />)}
    </section>
  ));
}

export function TechnicianAgenda() {
  const load = useCallback(() => fetchTechnicianAgenda().then((response) => response.appointments), []);
  const { data, state, retry } = useAsyncData(load);
  const appointments = data ?? [];
  const now = new Date();
  const { upcoming, past } = splitAtToday(appointments, now);
  return (
    <PageFrame title="Agenda técnica" meta={state === 'ready' ? `${appointments.length} visitas` : undefined} state={stateMessage(state, retry)}>
      {state === 'loading' || state === 'error' || state === 'denied' ? null : state === 'empty' ? <EmptyState title="No hay visitas asignadas" description="No tienes visitas en tu agenda." /> : (
        <div className="technician-agenda">
          {upcoming.length > 0 ? (
            <section className="technician-agenda__section" aria-labelledby="technician-upcoming">
              <h2 id="technician-upcoming" className="technician-agenda__section-title">Próximas visitas</h2>
              <DayGroups groups={groupByDay(upcoming, now)} />
            </section>
          ) : null}
          {past.length > 0 ? (
            <section className="technician-agenda__section" aria-labelledby="technician-past">
              <h2 id="technician-past" className="technician-agenda__section-title">Visitas anteriores</h2>
              <DayGroups groups={groupByDay(past, now)} />
            </section>
          ) : null}
        </div>
      )}
    </PageFrame>
  );
}
