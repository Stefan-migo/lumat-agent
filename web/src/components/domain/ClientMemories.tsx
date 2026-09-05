import { useState } from "react";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Textarea } from "../primitives/Textarea";
import type { Column } from "../shared/DataTable";
import { DataTable } from "../shared/DataTable";
import { PageHeader } from "../shared/PageHeader";
import type { Memory } from "../../types";

export type MemoryHandler = (memoryId: number) => void;
export type MemoryPinHandler = (memoryId: number, pin: boolean) => void;

export interface ClientMemoriesProps {
  /** Customer-scoped memories for the ficha (MEM-6). */
  memories: Memory[];
  /** Customer display name for the PageHeader meta. */
  customerName?: string | null;
  /** Upsert a new memory; the parent refreshes the list. */
  onUpsert?: (contenido: string) => void;
  onDelete?: MemoryHandler;
  onPin?: MemoryPinHandler;
}

function statusTone(status: Memory["status"]): "neutral" | "success" | "warning" | "danger" {
  switch (status) {
    case "active":
      return "success";
    case "needs_review":
      return "warning";
    case "archived":
      return "neutral";
  }
}

function tipoTone(tipo: Memory["tipo"]): "neutral" | "success" | "warning" | "danger" {
  return tipo === "customer_memo" ? "warning" : "neutral";
}

/** Ficha memories panel (MEM-6): list + edit + delete + mark(pin) over the
 *  customer's `scope='customer'` memories. Reuses primitives (Card,
 *  DataTable, Textarea, Button) and PageHeader per the ClientFicha pattern.
 *  Pure-presentational: the parent owns fetch + mutation wiring. */
export function ClientMemories({
  memories,
  customerName,
  onUpsert,
  onDelete,
  onPin,
}: ClientMemoriesProps) {
  const [draft, setDraft] = useState("");

  const columns: Column<Memory>[] = [
    {
      key: "tipo",
      header: "Tipo",
      render: (m) => <Badge tone={tipoTone(m.tipo)}>{m.tipo}</Badge>,
    },
    { key: "titulo", header: "Titulo", render: (m) => m.titulo ?? "—" },
    { key: "contenido", header: "Contenido", render: (m) => m.contenido ?? "—" },
    {
      key: "status",
      header: "Estado",
      render: (m) => <Badge tone={statusTone(m.status)}>{m.status}</Badge>,
    },
    { key: "pin", header: "Pin", render: (m) => (m.pin ? "✓" : "—") },
  ];

  return (
    <Card title="Memorias del cliente">
      <PageHeader title="Memorias" meta={customerName ? `Ficha de ${customerName}` : undefined} />
      <DataTable
        columns={columns}
        rows={memories}
        emptyMessage="Sin memorias todavía"
        rowKey={(m) => String(m.id)}
        actions={(m) => (
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            {onPin ? (
              <Button variant="secondary" onClick={() => onPin(m.id, !m.pin)}>
                {m.pin ? "Quitar pin" : "Fijar"}
              </Button>
            ) : null}
            {onDelete ? (
              <Button variant="secondary" onClick={() => onDelete(m.id)}>
                Eliminar
              </Button>
            ) : null}
          </div>
        )}
      />
      {onUpsert ? (
        <div style={{ display: "grid", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
          <Textarea
            label="Nueva memoria"
            placeholder="Escribe una memoria sobre este cliente…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div>
            <Button
              onClick={() => {
                onUpsert(draft);
                setDraft("");
              }}
              disabled={!draft.trim()}
            >
              Agregar memoria
            </Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
