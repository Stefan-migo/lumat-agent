import {
  agendaDayNumber,
  agendaMonthDays,
  agendaMonthLabel,
  agendaPeriodLabel,
  agendaTodayKey,
  agendaWeekDays,
  agendaWeekdayLabels,
} from "./agendaTime";
import { Button } from "../primitives/Button";

export type AgendaCalendarView = "month" | "week";

export interface AgendaCalendarProps {
  view: AgendaCalendarView;
  anchor: string;
  selectedDay?: string | null;
  visitCounts: Record<string, number>;
  timezone: string;
  onSelectDay: (day: string | null) => void;
  onViewChange: (view: AgendaCalendarView) => void;
  onNavigate: (direction: -1 | 0 | 1) => void;
  today?: string;
}

function visitLabel(count: number) {
  return `${count} ${count === 1 ? "visita" : "visitas"}`;
}

export function AgendaCalendar({
  view,
  anchor,
  selectedDay = null,
  visitCounts,
  timezone,
  onSelectDay,
  onViewChange,
  onNavigate,
  today = agendaTodayKey(timezone),
}: AgendaCalendarProps) {
  const monthDays = agendaMonthDays(anchor, timezone);
  const days = view === "month" ? monthDays : agendaWeekDays(anchor, timezone);
  const leadingEmptyCells = view === "month" ? (new Date(`${monthDays[0]}T12:00:00Z`).getUTCDay() + 6) % 7 : 0;
  const monthLabel = agendaMonthLabel(anchor, timezone);
  const monthCells = [...Array.from({ length: leadingEmptyCells }), ...days];
  const trailingEmptyCells = view === "month" ? (7 - (monthCells.length % 7)) % 7 : 0;
  const tableCells = view === "month" ? [...monthCells, ...Array.from({ length: trailingEmptyCells })] : days;
  const rows = view === "month" ? Array.from({ length: tableCells.length / 7 }, (_, index) => tableCells.slice(index * 7, index * 7 + 7)) : [tableCells];

  return (
    <section className="agenda-calendar" aria-labelledby="agenda-calendar-title">
      <div className="agenda-calendar__toolbar">
        <h2 id="agenda-calendar-title">{view === "month" ? monthLabel : `Semana del ${agendaPeriodLabel(days[0], timezone)}`}</h2>
        <div className="agenda-calendar__actions">
          <Button variant="secondary" onClick={() => onNavigate(-1)}>Período anterior</Button>
          <Button variant="secondary" onClick={() => onNavigate(0)}>Hoy</Button>
          <Button variant="secondary" onClick={() => onNavigate(1)}>Período siguiente</Button>
          <div className="agenda-calendar__view-toggle" aria-label="Vista del calendario">
            <Button variant="secondary" onClick={() => onViewChange(view === "month" ? "week" : "month")}>
              {view === "month" ? "Ver semana" : "Ver mes"}
            </Button>
          </div>
        </div>
      </div>
      <table className="agenda-calendar__table" aria-label={`Calendario de ${monthLabel}`}>
        <thead><tr>{agendaWeekdayLabels(timezone).map((label) => <th key={label} className="agenda-calendar__weekday" scope="col">{label}</th>)}</tr></thead>
        <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((day, index) => {
          if (typeof day !== "string") return <td key={`empty-${rowIndex}-${index}`} className="agenda-calendar__empty" aria-hidden="true" />;
          const count = visitCounts[day] ?? 0;
          const selected = selectedDay === day;
          const current = today === day;
           return <td key={day} className="agenda-calendar__cell">
             <button type="button" className="agenda-calendar__day" aria-label={`${agendaPeriodLabel(day, timezone)}, ${visitLabel(count)}`} aria-pressed={selected} aria-selected={selected} aria-current={current ? "date" : undefined} onClick={() => onSelectDay(selected ? null : day)}>
              <span className="agenda-calendar__number">{agendaDayNumber(day)}</span>
              <span className="agenda-calendar__count">{visitLabel(count)}</span>
              {current || selected ? <span className={current ? "agenda-calendar__today" : "agenda-calendar__selected"}>{current && selected ? "Hoy · Seleccionado" : current ? "Hoy" : "Seleccionado"}</span> : null}
            </button>
          </td>;
        })}</tr>)}</tbody>
      </table>
    </section>
  );
}
