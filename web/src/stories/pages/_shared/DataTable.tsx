import type { ReactNode } from "react";

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
  rowKey?: (row: T) => string;
}

/** Generic story-local table emitting the tokenized `.table` primitive.
 *  Rows render inside th/td with the `--space-3` gap; when `rows` is empty
 *  and `emptyMessage` is set, `.empty-state` is rendered instead (D6). */
export function DataTable<T>({
  columns,
  rows,
  emptyMessage,
  actions,
  rowKey,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state__title">{emptyMessage ?? "No data"}</p>
      </div>
    );
  }

  return (
    <table className="table">
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key} style={{ textAlign: c.align ?? "left", gap: "var(--space-3)" }}>
              {c.header}
            </th>
          ))}
          {actions ? <th style={{ gap: "var(--space-3)" }}>Actions</th> : null}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={rowKey ? rowKey(row) : i}>
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
  );
}
