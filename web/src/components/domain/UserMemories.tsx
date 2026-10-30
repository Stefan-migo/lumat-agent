import { useEffect, useState } from "react";
import { apiFetch } from "../../api";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";
import { memoryTypeLabel, memoryTypeTone } from "../shared/toneMaps";
import "./UserMemories.css";

interface UserMemory {
  id: number;
  titulo: string;
  contenido: string;
  tipo: string;
  topic_key: string;
  created_at: string | null;
  updated_at: string | null;
  review_after: string | null;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).replace(/\./g, "");
}

export function UserMemories() {
  const [memories, setMemories] = useState<UserMemory[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadMemories = async () => {
    setState("loading");
    try {
      const result = await apiFetch<{ memories: UserMemory[] }>("/panel/api/assistant/memories");
      setMemories(result.memories);
      setState("ready");
    } catch {
      setState("error");
    }
  };

  useEffect(() => { void loadMemories(); }, []);

  const deleteMemory = async (memory: UserMemory) => {
    setDeletingId(memory.id);
    setDeleteError(null);
    try {
      await apiFetch<void>(`/panel/api/assistant/memories/${memory.id}`, { method: "DELETE" });
      setMemories((current) => current.filter((item) => item.id !== memory.id));
    } catch {
      setDeleteError("No pudimos eliminar esta memoria. Inténtalo nuevamente.");
    } finally {
      setDeletingId(null);
    }
  };

  return <Card title="Memorias sobre ti" className="user-memories">
    {state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando tus memorias" /> : null}
    {state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar tus memorias" /><Button variant="secondary" onClick={() => void loadMemories()}>Reintentar</Button></> : null}
    {deleteError ? <StateMessage tone="danger" role="alert" title={deleteError} /> : null}
    {state === "ready" && memories.length === 0 ? <EmptyState title="Sin memorias todavía" description="Cuando el asistente recuerde algo sobre ti, podrás revisarlo aquí." /> : null}
    {state === "ready" && memories.length > 0 ? <ul className="user-memories__list">
      {memories.map((memory) => <li key={memory.id}>
        <article className="user-memories__item">
          <div className="user-memories__copy">
            <h3>{memory.titulo || "Sin título"}</h3>
            <p>{memory.contenido}</p>
            <div className="user-memories__metadata"><Badge tone={memoryTypeTone(memory.tipo)}>{memoryTypeLabel(memory.tipo)}</Badge><time dateTime={memory.created_at ?? undefined}>{formatDate(memory.created_at)}</time></div>
          </div>
          <Button variant="secondary" disabled={deletingId !== null} onClick={() => void deleteMemory(memory)}>{deletingId === memory.id ? "Eliminando…" : "Eliminar"}</Button>
        </article>
      </li>)}
    </ul> : null}
  </Card>;
}
