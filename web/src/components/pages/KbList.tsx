import { useCallback, useState } from "react";
import { ApiError, disableKbDocument, editKbDocument, getKbDocument, refreshKbDocuments, restoreKbDocument, searchKb, uploadKbDocument } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Doc, DocsResponse, KbSearchResult } from "../../types";
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
  const [content, setContent] = useState<string | null>(null);
  const [contentState, setContentState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const loadContent = async () => {
    setContentState("loading");
    try {
      const fullDoc = await getKbDocument(doc.id);
      setContent(fullDoc.content);
      setContentState("ready");
    } catch {
      setContentState("error");
    }
  };

  return <div className="kb-actions">
    <details onToggle={(event) => { if (event.currentTarget.open && contentState === "idle") void loadContent(); }}>
      <summary>Editar</summary>
      <div className="kb-actions__edit-form">
        <Input label="Título" defaultValue={doc.title} id={`kb-title-${doc.id}`} />
        {contentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando contenido" /> : null}
        {contentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar el contenido" detail="Reintenta antes de guardar para evitar reemplazar el texto almacenado." /> : null}
        <Textarea label="Contenido" rows={3} value={content ?? ""} onChange={(event) => setContent(event.target.value)} disabled={contentState !== "ready" || busy !== null} id={`kb-content-${doc.id}`} />
        <div><Button variant="secondary" disabled={busy !== null || contentState !== "ready"} onClick={() => onEdit((document.getElementById(`kb-title-${doc.id}`) as HTMLInputElement).value, content ?? "")}>Guardar (nueva versión)</Button></div>
        <div className="kb-actions__technical">
          <p className="kb-actions__technical-title">Detalle técnico · proveedor y modelo</p>
          <p className="kb-actions__technical-copy">Metadatos avanzados del motor que responde con este documento. No es necesario cambiarlos en el uso habitual.</p>
          <p>Proveedor: <span className="kb-actions__technical-value">{doc.provider ?? "—"}</span>&nbsp;·&nbsp;Modelo: <span className="kb-actions__technical-value">{doc.model ?? "—"}</span></p>
        </div>
      </div>
    </details>
    {doc.active ? <Button variant="secondary" disabled={busy !== null} onClick={onDisable}>Deshabilitar</Button> : <span className="kb-actions__technical-copy">Deshabilitado</span>}
    {doc.version > 1 ? <div className="kb-actions__restore"><Select label="Restaurar" aria-label={`Restaurar doc ${doc.id}`} defaultValue={String(doc.active_version)} options={Array.from({ length: doc.version }, (_, index) => ({ value: String(index + 1), label: `v${index + 1}` }))} size="sm" disabled={busy !== null} /><Button variant="secondary" disabled={busy !== null} onClick={(event) => onRestore(Number((event.currentTarget.parentElement?.querySelector("select") as HTMLSelectElement).value))}>Restaurar</Button></div> : null}
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

const searchColumns: Column<KbSearchResult>[] = [
  { key: "title", header: "Documento", render: (result) => result.title },
  { key: "version", header: "Versión", render: (result) => `v${result.version}` },
  { key: "chunk", header: "Fragmento", render: (result) => result.chunk_index + 1 },
  { key: "similarity", header: "Similitud", align: "right", render: (result) => tabularNum(result.similarity.toFixed(3)) },
  { key: "content", header: "Contenido", render: (result) => <span className="kb-search__result-content">{result.content}</span> },
];

function stateMessage(state: KbListState, storyError: boolean) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando base de conocimientos" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={storyError ? "No pudimos procesar el documento" : "No pudimos cargar la base de conocimientos"} />;
  if (state === "processing") return <StateMessage tone="info" role="status" spinner title="Procesando documento" detail="Revisando el formato, tamaño y contenido. Verifica el estado en unos momentos." />;
  return null;
}

function SearchPanel() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState("5");
  const [minSim, setMinSim] = useState("0.65");
  const [results, setResults] = useState<KbSearchResult[]>([]);
  const [searchState, setSearchState] = useState<"idle" | "loading" | "ready" | "empty" | "error" | "denied">("idle");

  const runSearch = async () => {
    setSearchState("loading");
    try {
      const response = await searchKb({ q: query, topK: Number(topK), minSim: Number(minSim) });
      setResults(response.results);
      setSearchState(response.results.length > 0 ? "ready" : "empty");
    } catch (error) {
      setSearchState(error instanceof ApiError && error.status === 403 ? "denied" : "error");
    }
  };

  return <Card title="Probar recuperación">
    <div className="kb-search">
      <div className="kb-search__fields">
        <Input label="Consulta" placeholder="Escribe una consulta" value={query} onChange={(event) => setQuery(event.target.value)} />
        <Input label="Máximo de resultados" type="number" min="1" value={topK} onChange={(event) => setTopK(event.target.value)} />
        <Input label="Similitud mínima" type="number" min="0" max="1" step="0.01" value={minSim} onChange={(event) => setMinSim(event.target.value)} />
        <Button onClick={() => void runSearch()} disabled={searchState === "loading"}>Buscar</Button>
      </div>
      {searchState === "loading" ? <StateMessage tone="info" role="status" spinner title="Buscando en la base de conocimientos" /> : null}
      {searchState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para buscar en la base de conocimientos" /> : null}
      {searchState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos realizar la búsqueda" detail="Revisa la consulta y los parámetros e inténtalo nuevamente." /> : null}
      {searchState === "empty" ? <EmptyState title="No encontramos resultados" description="Prueba con otra consulta o baja la similitud mínima." /> : null}
      {searchState === "ready" ? <><p className="kb-search__summary">{results.length} resultados ordenados por similitud.</p><DataTable columns={searchColumns} rows={results} rowKey={(result) => `${result.document_id}-${result.version}-${result.chunk_index}`} /></> : null}
    </div>
  </Card>;
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
  const showWorkspace = state !== "processing" && state !== "error" && state !== "denied" && state !== "loading" && data;
  return <PageFrame title="Base de conocimientos" meta={data ? `${docs.length} documentos` : undefined} state={stateMessage(state, controlledState === "error")}>
    {feedback ? <StateMessage tone={feedback.tone} role="alert" title={feedback.title} /> : null}
    {showWorkspace ? <>
      <Card title="Agregar documento"><div className="kb-upload__fields"><Input label="Título" placeholder="Título del documento" value={title} onChange={(event) => setTitle(event.target.value)} disabled={busy !== null} /><Input label="Archivo (pdf / md / txt / csv)" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} disabled={busy !== null} /><Button disabled={busy !== null} onClick={() => file && mutate("upload", () => uploadKbDocument(title, file))}>Agregar</Button></div></Card>
      {docs.length === 0 ? <EmptyState title="No hay documentos" description="Sube el primer documento para comenzar." /> : <DataTable columns={columns} rows={docs} rowKey={(doc) => String(doc.id)} actions={(doc) => <DocActions doc={doc} busy={busy} onEdit={(nextTitle, content) => mutate("edit", () => editKbDocument(doc.id, { title: nextTitle, content }))} onDisable={() => mutate("disable", () => disableKbDocument(doc.id))} onRestore={(version) => mutate("restore", () => restoreKbDocument(doc.id, version))} />} />}
      <SearchPanel />
    </> : null}
    {controlledState === "disable-confirmation" ? <StateMessage tone="warning" role="alert" title="Confirma la desactivación" detail={`Al deshabilitar «${docs.find((doc) => doc.active)?.title ?? "este documento"}», el agente dejará de responder con él. Puedes volver a activarlo cuando quieras.`} /> : null}
    {state === "error" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
