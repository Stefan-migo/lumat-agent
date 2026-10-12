import type { InternalChatThreadSummary } from "../../types";

export interface ThreadDateGroup {
  label: string;
  threads: InternalChatThreadSummary[];
}

export function groupThreadsByDate(threads: InternalChatThreadSummary[], now = new Date()): ThreadDateGroup[] {
  const today = dateKey(now);
  const todayParts = dateParts(now);
  const currentYear = Number(todayParts.year);
  const yesterday = dateKey(new Date(Date.UTC(currentYear, Number(todayParts.month) - 1, Number(todayParts.day) - 1, 12)));
  const groups = new Map<string, ThreadDateGroup & { timestamp: number }>();

  for (const thread of threads) {
    const activity = thread.updated_at || thread.created_at;
    const date = activity ? new Date(activity) : null;
    const key = date && !Number.isNaN(date.getTime()) ? dateKey(date) : "unknown";
    const label = key === today ? "Hoy" : key === yesterday ? "Ayer" : date && !Number.isNaN(date.getTime())
      ? new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", ...(Number(dateParts(date).year) !== currentYear ? { year: "numeric" } : {}), timeZone: "America/Santiago" }).format(date).replace(".", "")
      : "Sin fecha";
    const group = groups.get(key) ?? { label, threads: [], timestamp: date?.getTime() ?? Number.NEGATIVE_INFINITY };
    group.threads.push(thread);
    group.timestamp = Math.max(group.timestamp, date && !Number.isNaN(date.getTime()) ? date.getTime() : Number.NEGATIVE_INFINITY);
    groups.set(key, group);
  }

  return [...groups.values()]
    .sort((a, b) => b.timestamp - a.timestamp)
    .map(({ label, threads: entries }) => ({ label, threads: entries.sort((a, b) => activityTime(b) - activityTime(a)) }));
}

function activityTime(thread: InternalChatThreadSummary): number {
  const value = thread.updated_at || thread.created_at;
  const time = value ? new Date(value).getTime() : Number.NEGATIVE_INFINITY;
  return Number.isNaN(time) ? Number.NEGATIVE_INFINITY : time;
}

function dateKey(date: Date): string {
  const { year, month, day } = dateParts(date);
  return `${year}-${month}-${day}`;
}

function dateParts(date: Date): Record<string, string> {
  return Object.fromEntries(new Intl.DateTimeFormat("en", { timeZone: "America/Santiago", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date).map(({ type, value }) => [type, value]));
}
