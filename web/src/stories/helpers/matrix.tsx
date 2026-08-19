import type { ReactNode } from "react";

/** Local story-grid helper (DS-STORY-4) — token-styled, no component tree change.
 *  Shared by all 10 doc-level stories (D10); one definition, zero duplication. */
export function Matrix({ cells }: { cells: Array<[string, ReactNode]> }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "var(--space-3)",
        padding: "var(--space-2)",
      }}
    >
      {cells.map(([name, node]) => (
        <div
          key={name}
          style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--space-3)",
          }}
        >
          <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
            {name}
          </p>
          <div style={{ marginTop: "var(--space-2)" }}>{node}</div>
        </div>
      ))}
    </div>
  );
}
