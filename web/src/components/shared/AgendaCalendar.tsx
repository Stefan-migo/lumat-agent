import {
  agendaDayNumber,
  agendaMonthDays,
  agendaMonthLabel,
  agendaPeriodLabel,
  agendaTodayKey,
  agendaWeekDays,
  agendaWeekdayLabels,
} from "./agendaTime";

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
  const gridCells = view === "month" ? [...monthCells, ...Array.from({ length: trailingEmptyCells })] : days;

  return (
    <section className="agenda-calendar" aria-labelledby="agenda-calendar-title">
      <div className="agenda-calendar__toolbar">
        <h2 id="agenda-calendar-title">{view === "month" ? monthLabel : `Semana del ${agendaPeriodLabel(days[0], timezone)}`}</h2>
        <div className="agenda-calendar__actions">
          <button type="button" className="btn btn--secondary" onClick={() => onNavigate(-1)}>Período anterior</button>
          <button type="button" className="btn btn--secondary" onClick={() => onNavigate(0)}>Hoy</button>
          <button type="button" className="btn btn--secondary" onClick={() => onNavigate(1)}>Período siguiente</button>
          <div className="agenda-calendar__view-toggle" aria-label="Vista del calendario">
            <button type="button" className="btn btn--secondary" aria-pressed={view === "month"} onClick={() => onViewChange("month")}>Mes</button>
            <button type="button" className="btn btn--secondary" aria-pressed={view === "week"} onClick={() => onViewChange("week")}>Semana</button>
          </div>
        </div>
      </div>
      <div className="agenda-calendar__grid" role="grid" aria-label={`Calendario de ${monthLabel}`}>
        {agendaWeekdayLabels(timezone).map((label) => <div key={label} className="agenda-calendar__weekday" role="columnheader">{label}</div>)}
        {gridCells.map((day, index) => {
          if (typeof day !== "string") {
            return <div key={`empty-${index}`} className="agenda-calendar__empty" role="gridcell" aria-hidden="true" />;
          }
          const count = visitCounts[day] ?? 0;
          const selected = selectedDay === day;
          const current = today === day;
          return (
            <div key={day} className="agenda-calendar__cell" role="gridcell" aria-selected={selected}>
              <button
                type="button"
                className="agenda-calendar__day"
                aria-label={`${agendaPeriodLabel(day, timezone)}, ${visitLabel(count)}`}
                aria-selected={selected}
                aria-current={current ? "date" : undefined}
                onClick={() => onSelectDay(selected ? null : day)}
              >
                <span className="agenda-calendar__number">{agendaDayNumber(day)}</span>
                <span className="agenda-calendar__count">{visitLabel(count)}</span>
                {current ? <span className="agenda-calendar__today">Hoy</span> : null}
                {selected ? <span className="agenda-calendar__selected">Seleccionado</span> : null}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
