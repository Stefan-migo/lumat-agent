import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  /** Subtitle / meta line (e.g. window caption), muted and small. */
  meta?: ReactNode;
  /** Header actions (e.g. Export CSV button). */
  actions?: ReactNode;
}

/** Page title block with muted meta and optional actions (design D6 pg header).
 *  No primitive class of its own; styled via tokenized inline styles. */
export function PageHeader({ title, meta, actions }: PageHeaderProps) {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "var(--space-3)",
        marginBottom: "var(--space-4)",
      }}
    >
      <div>
        <h1 style={{ margin: 0, fontSize: "var(--text-2xl)", color: "var(--text)" }}>{title}</h1>
        {meta ? (
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>{meta}</p>
        ) : null}
      </div>
      {actions ? (
        <div style={{ display: "flex", gap: "var(--space-2)" }}>{actions}</div>
      ) : null}
    </header>
  );
}
