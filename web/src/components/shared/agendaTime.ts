/** 24-hour slots stay unambiguous and avoid repeating a meridiem across a range. */
const slotFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('es-CL', { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });

const dayFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' });

const dateParts = (dayKey: string) => {
  const [year, month, day] = dayKey.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day, 12));
};

const dayKeyFromDate = (date: Date) => date.toISOString().slice(0, 10);

const localNoonForDay = (dayKey: string, timeZone: string) => {
  const probe = dateParts(dayKey);
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(probe);
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, Number(value)]));
  const localAsUtc = Date.UTC(values.year, values.month - 1, values.day, values.hour, values.minute, values.second);
  return new Date(probe.getTime() - (localAsUtc - probe.getTime()));
};

const calendarFormat = (timeZone: string, options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('es-CL', { ...options, timeZone });

/** Formats an agenda slot in the appointment's own timezone using 24-hour time. */
export function formatAgendaSlot(iso: string, timeZone: string) {
  return slotFormat(timeZone).format(new Date(iso));
}

/** Returns the appointment's local calendar day as a comparable YYYY-MM-DD key. */
export function agendaDayKey(iso: string, timeZone: string) {
  return dayFormat(timeZone).format(new Date(iso));
}

/** Returns today's local calendar day in the requested timezone. */
export function agendaTodayKey(timeZone: string) {
  return agendaDayKey(new Date().toISOString(), timeZone);
}

/** Returns a localized month heading for an agenda anchor. */
export function agendaMonthLabel(anchorDay: string, timeZone: string) {
  return calendarFormat(timeZone, { month: 'long', year: 'numeric' }).format(localNoonForDay(anchorDay, timeZone));
}

/** Returns only the days belonging to the anchor's month. */
export function agendaMonthDays(anchorDay: string, _timeZone: string) {
  const anchor = dateParts(anchorDay);
  const days = new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth(), 1));
  const result: string[] = [];
  while (days.getUTCMonth() === anchor.getUTCMonth()) {
    result.push(dayKeyFromDate(days));
    days.setUTCDate(days.getUTCDate() + 1);
  }
  return result;
}

/** Returns the Monday-first week containing the anchor day. */
export function agendaWeekDays(anchorDay: string, _timeZone: string) {
  const start = dateParts(anchorDay);
  const mondayOffset = (start.getUTCDay() + 6) % 7;
  start.setUTCDate(start.getUTCDate() - mondayOffset);
  return Array.from({ length: 7 }, (_, index) => {
    const day = new Date(start);
    day.setUTCDate(start.getUTCDate() + index);
    return dayKeyFromDate(day);
  });
}

/** Returns short Monday-first weekday labels in Chilean Spanish. */
export function agendaWeekdayLabels(timeZone: string) {
  return agendaWeekDays('2026-01-05', timeZone).map((day) =>
    calendarFormat(timeZone, { weekday: 'short' }).format(localNoonForDay(day, timeZone)).replace('.', ''),
  );
}

/** Returns the non-padded day number for a day key. */
export function agendaDayNumber(dayKey: string) {
  return String(Number(dayKey.slice(8, 10)));
}

/** Returns a long localized date heading for a register section. */
export function agendaPeriodLabel(dayKey: string, timeZone: string) {
  return calendarFormat(timeZone, { weekday: 'long', day: 'numeric', month: 'long' })
    .format(localNoonForDay(dayKey, timeZone))
    .replace(', ', ' ');
}

/** Moves an agenda anchor by month or Monday-first week. */
export function agendaShiftPeriod(
  anchorDay: string,
  view: 'month' | 'week',
  direction: -1 | 0 | 1,
  timeZone: string,
) {
  if (direction === 0) return agendaTodayKey(timeZone);
  const anchor = dateParts(anchorDay);
  if (view === 'month') {
    anchor.setUTCDate(1);
    anchor.setUTCMonth(anchor.getUTCMonth() + direction);
  } else {
    const mondayOffset = (anchor.getUTCDay() + 6) % 7;
    anchor.setUTCDate(anchor.getUTCDate() - mondayOffset + direction * 7);
  }
  return dayKeyFromDate(anchor);
}
