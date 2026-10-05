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

export type AgendaTimeErrorCode = 'nonexistent_local_time' | 'ambiguous_local_time';

export class AgendaTimeError extends Error {
  readonly code: AgendaTimeErrorCode;

  constructor(code: AgendaTimeErrorCode, message: string) {
    super(message);
    this.name = 'AgendaTimeError';
    this.code = code;
  }
}

const localParts = (instant: Date, timeZone: string) => {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(instant);
  return Object.fromEntries(parts.filter(({ type }) => type !== 'literal').map(({ type, value }) => [type, value]));
};

const offsetAt = (instant: Date, timeZone: string) => {
  const parts = localParts(instant, timeZone);
  const localAsUtc = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute), Number(parts.second));
  return localAsUtc - instant.getTime();
};

/** Converts operator-entered local time without allowing the runtime to normalize DST gaps/folds. */
export function composeAgendaTime(localDate: string, localTime: string, timeZone: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(localDate) || !/^\d{2}:\d{2}(?::\d{2})?$/.test(localTime)) {
    throw new RangeError('Invalid local date or time');
  }
  const [year, month, day] = localDate.split('-').map(Number);
  const [hour, minute, second = 0] = localTime.split(':').map(Number);
  if (month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 59) {
    throw new RangeError('Invalid local date or time');
  }

  const target = { year: String(year), month: String(month).padStart(2, '0'), day: String(day).padStart(2, '0'), hour: String(hour).padStart(2, '0'), minute: String(minute).padStart(2, '0'), second: String(second).padStart(2, '0') };
  const wallUtc = Date.UTC(year, month - 1, day, hour, minute, second);
  const offsets = new Set<number>();
  for (let hours = -48; hours <= 48; hours += 1) offsets.add(offsetAt(new Date(wallUtc + hours * 60 * 60 * 1000), timeZone));
  const matches = [...offsets]
    .map((offset) => new Date(wallUtc - offset))
    .filter((instant) => JSON.stringify(localParts(instant, timeZone)) === JSON.stringify(target));

  if (matches.length === 0) throw new AgendaTimeError('nonexistent_local_time', 'This local time does not exist because of a daylight-saving transition.');
  if (matches.length > 1) throw new AgendaTimeError('ambiguous_local_time', 'This local time is ambiguous because daylight-saving time repeats it.');
  return { local_date: localDate, local_time: `${target.hour}:${target.minute}:${target.second}`, timezone: timeZone };
}

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
  const label = calendarFormat(timeZone, { month: 'long', year: 'numeric' }).format(localNoonForDay(anchorDay, timeZone));
  return label[0].toLocaleUpperCase('es-CL') + label.slice(1);
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
  const label = calendarFormat(timeZone, { weekday: 'long', day: 'numeric', month: 'long' })
    .format(localNoonForDay(dayKey, timeZone))
    .replace(', ', ' ');
  return label.charAt(0).toLocaleUpperCase('es-CL') + label.slice(1);
}

/** Returns a compact, capitalized local date for an appointment card. */
export function agendaDayLabel(dayKey: string, timeZone: string) {
  const label = calendarFormat(timeZone, { weekday: 'short', day: 'numeric', month: 'short' })
    .format(localNoonForDay(dayKey, timeZone))
    .replace(/[,.]/g, '');
  return label.charAt(0).toLocaleUpperCase('es-CL') + label.slice(1);
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
