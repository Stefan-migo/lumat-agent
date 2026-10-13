import type { ReactNode } from "react";

interface SummarySegment {
  label: string;
  value: string;
}

const SUMMARY_MARKER = /(?:^|[\s,;.!?])(Cliente|Motivo|Intenci[oó]n|Conversaci[oó]n|Datos capturados|Clasificaci[oó]n(?: del caso)?|Siguiente paso|Escalada)\s*:\s*/giu;

function displayLabel(marker: string) {
  if (/^intenci[oó]n$/iu.test(marker)) return "Motivo";
  if (/^clasificaci[oó]n/iu.test(marker)) return "Clasificación";
  return marker.charAt(0).toLocaleUpperCase("es-CL") + marker.slice(1);
}

function parseSummary(summary: string): SummarySegment[] {
  const markers = [...summary.matchAll(SUMMARY_MARKER)];
  return markers.flatMap((marker, index) => {
    const matchStart = marker.index ?? 0;
    const label = marker[1];
    const valueStart = matchStart + marker[0].length;
    const valueEnd = markers[index + 1]?.index ?? summary.length;
    const value = summary.slice(valueStart, valueEnd).trim().replace(/[\s,;.!?]+$/u, "");
    return value ? [{ label: displayLabel(label), value }] : [];
  });
}

export function ConversationSummary({ summary, fallback }: { summary: string; fallback?: ReactNode }) {
  const segments = parseSummary(summary);
  if (!segments.length) return fallback ?? <p className="conversation-summary__fallback">{summary}</p>;

  return <dl className="conversation-summary__segments">{segments.map((segment, index) => (
    <div className="conversation-summary__segment" key={`${segment.label}-${index}`}>
      <dt className="conversation-summary__label">{segment.label}</dt>
      <dd className="conversation-summary__value">{segment.value}</dd>
    </div>
  ))}</dl>;
}
