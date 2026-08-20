import type { CSSProperties, ReactNode } from "react";

/** Column definition for DataTable (design D6). */
export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right";
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
  actions?: (row: T) => ReactNode;
  actionsHeader?: string;
  rowKey?: (row: T) => string;
  /** Optional per-row inline style (e.g. inbox human-row highlight, S1). */
  rowStyle?: (row: T) => CSSProperties | undefined;
  /** Show a loading state instead of the table while data is pending. */
  loading?: boolean;
  /** Show a stale-data note above the table. */
  stale?: boolean;
}

/** Numeric-column helper (design D6/DS-UI-TABLES): comparable numbers render
 *  with tabular numerals so digits align. Used inside a column's `render`. */
export function tabularNum(cell: ReactNode): ReactNode {
  return <span style={{ fontVariantNumeric: "tabular-nums" }}>{cell}</span>;
}

/** Generic shared table emitting the tokenized `.table` primitive.
 *  Rows render inside th/td with the `--space-3` gap; when `rows` is empty
 *  and `emptyMessage` is set, `.empty-state` is rendered instead (D6).
 *  Defaults are Spanish (DS-UI-COPY/DS-UI-TABLES): `No hay registros` empty
 *  message and `Acciones` actions header. `loading`/`stale` mirror the state
 *  matrix (DS-UI-STATES): the loading state replaces the table entirely. */
export function DataTable<T>({
  columns,
  rows,
  emptyMessage = "No hay registros",
  actions,
  actionsHeader = "Acciones",
  rowKey,
  rowStyle,
  loading = false,
  stale = false,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="empty-state" role="status">
        <span className="spinner__indicator" aria-hidden="true" />
        <p className="empty-state__title">Cargando datos…</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state__title">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div>
      {stale ? (
        <p
          role="status"
          style={{ margin: "0 0 var(--space-3)", color: "var(--text-muted)", fontSize: "var(--text-sm)" }}
        >
          Datos posiblemente desactualizados
        </p>
      ) : null}
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={{ textAlign: c.align ?? "left", gap: "var(--space-3)" }}>
                {c.header}
              </th>
            ))}
            {actions ? <th style={{ gap: "var(--space-3)" }}>{actionsHeader}</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={rowKey ? rowKey(row) : i} style={rowStyle ? rowStyle(row) : undefined}>
              {columns.map((c) => (
                <td key={c.key} style={{ textAlign: c.align ?? "left", gap: "var(--space-3)" }}>
                  {c.render(row)}
                </td>
              ))}
              {actions ? <td style={{ gap: "var(--space-3)" }}>{actions(row)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

