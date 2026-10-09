import type { CSSProperties, ReactNode } from "react";

/** Column definition for DataTable (design D6). */
export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right";
  /** Optional column width applied to the header cell. */
  width?: string;
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

/** Numeric-column helper resolved through `--corp-value` (CST-ALIAS-5 / DS-TKN-11). */
export function tabularNum(cell: ReactNode): ReactNode {
  return <span style={{ fontVariantNumeric: "var(--corp-value)" }}>{cell}</span>;
}

/** Generic shared table emitting the tokenized `.table` primitive. */
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
        <p role="status" className="table__stale">
          Datos posiblemente desactualizados
        </p>
      ) : null}
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" style={{ width: c.width, textAlign: c.align ?? "left" }}>{c.header}</th>
            ))}
            {actions ? <th scope="col">{actionsHeader}</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={rowKey ? rowKey(row) : i} style={rowStyle ? rowStyle(row) : undefined}>
              {columns.map((c) => (
                <td key={c.key} style={{ textAlign: c.align ?? "left" }}>{c.render(row)}</td>
              ))}
              {actions ? <td className="table__actions-cell">{actions(row)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
