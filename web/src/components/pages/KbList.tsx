import { useCallback, useState } from "react";
import { ApiError, disableKbDocument, editKbDocument, refreshKbDocuments, restoreKbDocument, uploadKbDocument } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Doc, DocsResponse } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { DataTable, tabularNum, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { kbStatusLabel } from "../shared/toneMaps";

export type KbListState = AsyncDataState | "processing" | "disable-confirmation";
export interface KbListProps { data?: DocsResponse | null; state?: KbListState; onRetry?: () => void; }

function docStatus(doc: Doc): "activo" | "deshabilitado" { return doc.active ? "activo" : "deshabilitado"; }

type Mutation = "upload" | "edit" | "disable" | "restore";
function safeMutationError(error: unknown): string {
  if (error instanceof ApiError && (error.status === 400 || error.status === 422)) return "Revisa los campos e inténtalo nuevamente.";
  if (error instanceof ApiError && error.status === 403) return "No tienes permiso para modificar la base de conocimientos.";
  return "No pudimos guardar los cambios. Inténtalo nuevamente.";
}

function DocActions({ doc, busy, onEdit, onDisable, onRestore }: { doc: Doc; busy: Mutation | null; onEdit: (title: string, content: string) => void; onDisable: () => void; onRestore: (version: number) => void }) {
  return <div style={{ display: "grid", gap: "var(--space-2)" }}>
    <details>
      <summary style={{ cursor: "pointer" }}>Editar</summary>
      <div style={{ marginTop: "var(--space-2)", display: "grid", gap: "var(--space-2)" }}>
        <Input label="Título" defaultValue={doc.title} id={`kb-title-${doc.id}`} />
        <Textarea label="Contenido" rows={3} defaultValue={`Contenido de ${doc.title}…`} id={`kb-content-${doc.id}`} />
        <div style={{ display: "flex", gap: "var(--space-2)" }}><Button variant="secondary" disabled={busy !== null} onClick={() => onEdit((document.getElementById(`kb-title-${doc.id}`) as HTMLInputElement).value, (document.getElementById(`kb-content-${doc.id}`) as HTMLTextAreaElement).value)}>Guardar (nueva versión)</Button></div>
        <div style={{ marginTop: "var(--space-2)", padding: "var(--space-3)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", background: "var(--surface)" }}>
          <p style={{ margin: 0, fontSize: "var(--text-sm)", fontWeight: "var(--weight-bold)" }}>Detalle técnico · proveedor y modelo</p>
          <p style={{ margin: "0 0 var(--space-2)", color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>Metadatos avanzados del motor que responde con este documento. No es necesario cambiarlos en el uso habitual.</p>
          <p style={{ margin: 0, fontSize: "var(--text-sm)" }}>Proveedor: <span style={{ fontVariantNumeric: "tabular-nums" }}>{doc.provider ?? "—"}</span>&nbsp;·&nbsp;Modelo: <span style={{ fontVariantNumeric: "tabular-nums" }}>{doc.model ?? "—"}</span></p>
        </div>
      </div>
    </details>
    {doc.active ? <Button variant="secondary" disabled={busy !== null} onClick={onDisable}>Deshabilitar</Button> : <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>Deshabilitado</span>}
    {doc.version > 1 ? <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}><Select label="Restaurar" aria-label={`Restaurar doc ${doc.id}`} defaultValue={String(doc.active_version)} options={Array.from({ length: doc.version }, (_, index) => ({ value: String(index + 1), label: `v${index + 1}` }))} size="sm" disabled={busy !== null} /><Button variant="secondary" disabled={busy !== null} onClick={(event) => onRestore(Number((event.currentTarget.parentElement?.querySelector("select") as HTMLSelectElement).value))}>Restaurar</Button></div> : null}
  </div>;
}

const columns: Column<Doc>[] = [
  { key: "id", header: "#", render: (doc) => `#${doc.id}` },
  { key: "title", header: "Título", render: (doc) => doc.title },
  { key: "format", header: "Formato", render: (doc) => doc.format },
  { key: "version", header: "Versión", render: (doc) => `${doc.version} (activa: ${doc.active_version})` },
  { key: "status", header: "Estado", render: (doc) => <Badge tone={doc.active ? "success" : "neutral"}>{kbStatusLabel(docStatus(doc))}</Badge> },
  { key: "cost", header: "Costo", render: (doc) => doc.cost_meta !== null ? tabularNum(`$${doc.cost_meta.toFixed(6)}`) : "—" },
];

function stateMessage(state: KbListState, storyError: boolean) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando base de conocimientos" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={storyError ? "No pudimos procesar el documento" : "No pudimos cargar la base de conocimientos"} />;
  if (state === "processing") return <StateMessage tone="info" role="status" spinner title="Procesando documento" detail="Revisando el formato, tamaño y contenido. Verifica el estado en unos momentos." />;
  return null;
}

export function KbList({ data: controlledData, state: controlledState, onRetry }: KbListProps = {}) {
  const fetchDocs = useCallback(() => refreshKbDocuments(), []);
  const fetched = useAsyncData(fetchDocs, controlledData === undefined);
  const [refreshed, setRefreshed] = useState<DocsResponse | null>(null);
  const [busy, setBusy] = useState<Mutation | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "danger"; title: string } | null>(null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const data = refreshed ?? controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const docs = data?.docs ?? [];
  const refresh = async () => setRefreshed(await refreshKbDocuments());
  const mutate = async (action: Mutation, commit: () => Promise<unknown>) => {
    setBusy(action); setFeedback(null);
    try { await commit(); await refresh(); setFeedback({ tone: "success", title: "Cambios guardados" }); }
    catch (error) { setFeedback({ tone: "danger", title: safeMutationError(error) }); }
    finally { setBusy(null); }
  };
  const retry = onRetry ?? fetched.retry;
  return <PageFrame title="Base de conocimientos" meta={data ? `${docs.length} documentos` : undefined} state={stateMessage(state, controlledState === "error")}>
    {feedback ? <StateMessage tone={feedback.tone} role="alert" title={feedback.title} /> : null}
    {state === "processing" || state === "error" || state === "denied" || state === "loading" ? null : state === "empty" || (state === "ready" && data && docs.length === 0) ? <EmptyState title="No hay documentos" description="Subí el primer documento para empezar." /> : data ? <><Card title="Agregar documento"><div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end", flexWrap: "wrap" }}><Input label="Título" placeholder="Título del documento" value={title} onChange={(event) => setTitle(event.target.value)} disabled={busy !== null} /><Input label="Archivo (pdf / md / txt / csv)" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} disabled={busy !== null} /><Button disabled={busy !== null} onClick={() => file && mutate("upload", () => uploadKbDocument(title, file))}>Agregar</Button></div></Card><DataTable columns={columns} rows={docs} rowKey={(doc) => String(doc.id)} actions={(doc) => <DocActions doc={doc} busy={busy} onEdit={(nextTitle, content) => mutate("edit", () => editKbDocument(doc.id, { title: nextTitle, content }))} onDisable={() => mutate("disable", () => disableKbDocument(doc.id))} onRestore={(version) => mutate("restore", () => restoreKbDocument(doc.id, version))} />} /></> : null}
    {controlledState === "disable-confirmation" ? <StateMessage tone="warning" role="alert" title="Confirma la desactivación" detail={`Al deshabilitar «${docs.find((doc) => doc.active)?.title ?? "este documento"}», el agente dejará de responder con él. Puedes volver a activarlo cuando quieras.`} /> : null}
    {state === "error" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
