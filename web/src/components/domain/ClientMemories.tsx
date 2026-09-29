import { useState } from "react";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Textarea } from "../primitives/Textarea";
import type { Column } from "../shared/DataTable";
import { DataTable } from "../shared/DataTable";
import { memoryStatusLabel, memoryStatusTone } from "../shared/toneMaps";
import type { Memory, MemoryRelation, MemoryRelationKind } from "../../types";

export type MemoryHandler = (memoryId: number) => void;
export type MemoryPinHandler = (memoryId: number, pin: boolean) => void;

export interface ClientMemoriesProps {
  /** Customer-scoped memories for the ficha (MEM-6). */
  memories: Memory[];
  /** Upsert a new memory; the parent refreshes the list. */
  onUpsert?: (contenido: string) => void;
  onDelete?: MemoryHandler;
  onPin?: MemoryPinHandler;
  pendingRelations?: MemoryRelation[];
  onResolveRelation?: (relationId: number, relation: MemoryRelationKind) => Promise<void> | void;
}

function tipoTone(tipo: Memory["tipo"]): "neutral" | "success" | "warning" | "danger" {
  return tipo === "customer_memo" ? "warning" : "neutral";
}

/** Ficha memories panel (MEM-6): list + edit + delete + mark(pin) over the
 *  customer's `scope='customer'` memories. Reuses primitives (Card,
  *  DataTable, Textarea, Button) per the ClientFicha pattern.
 *  Pure-presentational: the parent owns fetch + mutation wiring. */
export function ClientMemories({
  memories,
  onUpsert,
  onDelete,
  onPin,
  pendingRelations = [],
  onResolveRelation,
}: ClientMemoriesProps) {
  const [draft, setDraft] = useState("");
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const featuredMemo = memories.find((memory) => memory.topic_key === "customer_memo");
  const tableMemories = featuredMemo
    ? memories.filter((memory) => memory.id !== featuredMemo.id)
    : memories;
  const renderActions = (memory: Memory) => (
    <div className="table__actions">
      {onPin ? (
        <Button variant="secondary" onClick={() => onPin(memory.id, !memory.pin)}>
          {memory.pin ? "Quitar pin" : "Fijar"}
        </Button>
      ) : null}
      {onDelete ? (
        <Button variant="secondary" onClick={() => onDelete(memory.id)}>
          Eliminar
        </Button>
      ) : null}
    </div>
  );

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
      render: (m) => <Badge tone={memoryStatusTone(m.status)}>{memoryStatusLabel(m.status)}</Badge>,
    },
    { key: "pin", header: "Pin", render: (m) => (m.pin ? "✓" : "—") },
  ];

  return (
    <Card title="Memorias del cliente">
      {featuredMemo ? (
        <div className="client-memories__memo">
          <strong>{featuredMemo.contenido}</strong>
          <div>
            <Badge tone={tipoTone(featuredMemo.tipo)}>{featuredMemo.tipo}</Badge>
            <Badge tone={memoryStatusTone(featuredMemo.status)}>{memoryStatusLabel(featuredMemo.status)}</Badge>
          </div>
          {renderActions(featuredMemo)}
        </div>
      ) : null}
      <DataTable
        columns={columns}
        rows={tableMemories}
        emptyMessage="Sin memorias todavía"
        rowKey={(m) => String(m.id)}
        actions={renderActions}
      />
      {onUpsert ? (
        <div className="client-memories__section">
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
      {pendingRelations.length ? (
        <div className="client-memories__section">
          <h3>Relaciones pendientes</h3>
          {pendingRelations.map((pending) => (
            <article key={pending.id} className="client-memories__relation">
              <strong>{pending.memory_a.titulo} · {pending.memory_b.titulo}</strong>
              <p>{pending.memory_a.contenido}</p>
              <p>{pending.memory_b.contenido}</p>
              <p>Propuesta: {pending.relation} · Confianza: {pending.confidence}</p>
              <p>Motivo: {pending.reason ?? "—"}</p>
              {onResolveRelation ? (
                <div className="client-memories__relation-actions">
                  {(["supersedes", "conflicts", "related", "compatible", "scoped", "not_conflict"] as const).map((relation) => (
                    <Button
                      key={relation}
                      variant="secondary"
                      disabled={resolvingId !== null}
                      onClick={() => {
                        setResolvingId(pending.id);
                        void Promise.resolve(onResolveRelation(pending.id, relation)).finally(() => setResolvingId(null));
                      }}
                    >
                      {relation}
                    </Button>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
    </Card>
  );
}
