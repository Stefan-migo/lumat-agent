/** 24-hour slots stay unambiguous and avoid repeating a meridiem across a range. */
const slotFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('es-CL', { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });

const dayFormat = (timeZone: string) =>
  new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' });

/** Formats an agenda slot in the appointment's own timezone using 24-hour time. */
export function formatAgendaSlot(iso: string, timeZone: string) {
  return slotFormat(timeZone).format(new Date(iso));
}

/** Returns the appointment's local calendar day as a comparable YYYY-MM-DD key. */
export function agendaDayKey(iso: string, timeZone: string) {
  return dayFormat(timeZone).format(new Date(iso));
}
