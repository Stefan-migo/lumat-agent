/** Dashboard mock data — matches the friendly-dashboard reference layout.
 *  Activity rows match the events surfaced by `app/panel/routes/dashboard.py`
 *  (conversation events, KB lookups, handoffs). The window_days/window_start
 *  pair that used to drive the KPI caption was removed with the titlebar
 *  redesign; the production serializer keeps those fields unchanged. */
export interface ActivityRow {
  id: string;
  /** Agent full name — drives the Avatar initials (DS-UI-AVATAR). */
  name: string;
  /** Event title — bold line of the activity row. */
  title: string;
  /** Channel + outcome line — muted secondary line. */
  context: string;
  /** Wall-clock time of the event, `HH:MM` for the dashboard card. */
  time: string;
}

/** KPI card contract — label, formatted value, and trend delta. */
export interface Kpi {
  label: string;
  /** Formatted value (tabular numerals, locale-aware). */
  value: string;
  /** Trend delta with direction arrow, e.g. "↑ 12,4%". */
  delta: string;
  /** Tone class suffix: positive or negative. */
  deltaTone: "positive" | "negative";
}

/** Dashboard KPIs — the friendly reference layout's three indicators. */
export const kpis: Kpi[] = [
  { label: "Conversaciones", value: "1.248", delta: "↑ 12,4%", deltaTone: "positive" },
  { label: "Resolución autónoma", value: "84%", delta: "↑ 3,1%", deltaTone: "positive" },
  { label: "Tiempo de respuesta", value: "1,8 s", delta: "↓ 0,4 s", deltaTone: "positive" },
];

export const activity: ActivityRow[] = [
  {
    id: "ac-consulta",
    name: "Ana Castro",
    title: "Consulta comercial resuelta",
    context: "Canal web · Confianza alta",
    time: "10:42",
  },
  {
    id: "ms-derivada",
    name: "Marta Silva",
    title: "Conversación derivada",
    context: "WhatsApp · Revisión humana",
    time: "10:31",
  },
  {
    id: "jl-conocimiento",
    name: "Jorge López",
    title: "Respuesta desde conocimiento",
    context: "Portal · 3 fuentes consultadas",
    time: "10:18",
  },
];
