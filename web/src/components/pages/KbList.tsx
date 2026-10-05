import { useCallback, useState } from "react";
import { ChevronRight, FileText, Lock } from "lucide-react";
import { ApiError, refreshKbDocuments, searchKb, uploadKbDocument } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Doc, DocsResponse, KbSearchResult, KbVisibility } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Select, type SelectOption } from "../primitives/Select";
import { DataTable, tabularNum, type Column } from "../shared/DataTable";
import { Icon } from "../primitives/Icon";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { KB_OPERATION_TONES, kbStatusLabel, kbStatusTone } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";

export interface KbListProps { data?: DocsResponse | null; onRetry?: () => void; onOpenDocument?: (id: number) => void; fetchDocuments?: () => Promise<DocsResponse>; }

const ACCEPTED_EXTENSIONS = [".pdf", ".md", ".txt", ".csv"];
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

// `customer` means the customer channel may ground on the document AND Lumat may still read it —
// never client-only. The label says who reads it, symmetrically with `internal`.
const AUDIENCE_LABEL: Record<KbVisibility, string> = {
  customer: "Cliente y Lumat",
  internal: "Interno (solo Lumat)",
};

const TABLE_AUDIENCE_LABEL: Record<KbVisibility, string> = {
  customer: "Cliente · Cliente y Lumat",
  internal: "Interno · Solo Lumat",
};

// One source for the audience choices: the badge and both selectors used to carry their own literal.
const AUDIENCE_OPTIONS: SelectOption[] = [
  { value: "internal", label: AUDIENCE_LABEL.internal },
  { value: "customer", label: AUDIENCE_LABEL.customer },
];

function docStatus(doc: Doc): "activo" | "deshabilitado" { return doc.active ? "activo" : "deshabilitado"; }

const columns = (onOpenDocument?: (id: number) => void): Column<Doc>[] => [
  { key: "title", header: "Documento", render: (doc) => <DocumentIdentity doc={doc} onOpenDocument={onOpenDocument} /> },
  { key: "version", header: "Versión", render: (doc) => `v${doc.active_version} · Activa` },
  { key: "status", header: "Estado", render: (doc) => <Badge tone={kbStatusTone(docStatus(doc))}>{kbStatusLabel(docStatus(doc))}</Badge> },
  { key: "visibility", header: "Audiencia", render: (doc) => <span className="kb-list__audience">{doc.visibility === "internal" ? <Icon icon={Lock} size="sm" /> : null}{TABLE_AUDIENCE_LABEL[doc.visibility]}</span> },
  { key: "cost", header: "Costo", render: (doc) => doc.cost_meta !== null ? tabularNum(`$${doc.cost_meta.toFixed(6)}`) : "—" },
];

function DocumentIdentity({ doc, onOpenDocument }: { doc: Doc; onOpenDocument?: (id: number) => void }) {
  return <a className="kb-list__identity" href={pathForRoute({ view: "kb", kbDocId: doc.id })} onClick={onOpenDocument ? (event) => { event.preventDefault(); onOpenDocument(doc.id); } : undefined}>
    <span className="kb-list__file"><Icon icon={FileText} /></span>
    <span className="kb-list__identity-copy"><strong>{doc.title}</strong><small>#{doc.id} · {doc.format.toUpperCase()}</small></span>
    <Icon icon={ChevronRight} size="sm" />
  </a>;
}

const searchColumns: Column<KbSearchResult>[] = [
  { key: "title", header: "Documento", render: (result) => result.title },
  { key: "version", header: "Versión", render: (result) => `v${result.version}` },
  { key: "chunk", header: "Fragmento", render: (result) => result.chunk_index + 1 },
  { key: "similarity", header: "Similitud", align: "right", render: (result) => tabularNum(result.similarity.toFixed(3)) },
  { key: "content", header: "Contenido", render: (result) => <span className="kb-search__result-content">{result.content}</span> },
];

function stateMessage(state: AsyncDataState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando base de conocimientos" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone={KB_OPERATION_TONES.error} role="alert" title="No pudimos cargar la base de conocimientos" />;
  return null;
}

function SearchPanel() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState("5");
  const [minSim, setMinSim] = useState("0");
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

  return <section aria-label="Herramienta de recuperación"><Card title="Probar recuperación">
    <div className="kb-search">
      <div className="kb-search__fields">
        <Input label="Consulta" placeholder="Escribe una consulta" value={query} onChange={(event) => setQuery(event.target.value)} />
        <Input label="Máximo de resultados" type="number" min="1" value={topK} onChange={(event) => setTopK(event.target.value)} />
        <Input label="Similitud mínima" type="number" min="0" max="1" step="0.01" value={minSim} onChange={(event) => setMinSim(event.target.value)} />
        <Button onClick={() => void runSearch()} disabled={searchState === "loading"}>Buscar</Button>
      </div>
      <p className="kb-search__hint">La similitud mínima filtra los resultados: con 0 ves el ranking completo y sus puntajes. Auméntala para exigir más coincidencia.</p>
      {searchState === "loading" ? <StateMessage tone="info" role="status" spinner title="Buscando en la base de conocimientos" /> : null}
      {searchState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para buscar en la base de conocimientos" /> : null}
      {searchState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos realizar la búsqueda" detail="Revisa la consulta y los parámetros e inténtalo nuevamente." /> : null}
      {searchState === "empty" ? <EmptyState title="No encontramos resultados" description="Prueba con otra consulta o baja la similitud mínima." /> : null}
      {searchState === "ready" ? <><p className="kb-search__summary">{results.length} resultados ordenados por similitud.</p><DataTable columns={searchColumns} rows={results} rowKey={(result) => `${result.document_id}-${result.version}-${result.chunk_index}`} /></> : null}
    </div>
  </Card></section>;
}

export function KbList({ data: controlledData, onRetry, onOpenDocument, fetchDocuments }: KbListProps = {}) {
  const fetchDocs = useCallback(() => (fetchDocuments ?? refreshKbDocuments)(), [fetchDocuments]);
  const fetched = useAsyncData(fetchDocs, controlledData === undefined);
  const [refreshed, setRefreshed] = useState<DocsResponse | null>(null);
  const [busy, setBusy] = useState<"upload" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "danger"; title: string; retry?: boolean } | null>(null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState<KbVisibility>("internal");
  const [uploadDraft, setUploadDraft] = useState<{ title: string; file: File; visibility: KbVisibility } | null>(null);
  const [documentQuery, setDocumentQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const data = refreshed ?? controlledData ?? fetched.data;
  const state: AsyncDataState = controlledData !== undefined ? (controlledData ? "ready" : "empty") : fetched.state;
  const docs = data?.docs ?? [];
  const filteredDocs = docs.filter((doc) => {
    const matchesQuery = `${doc.title} ${doc.format} ${doc.id}`.toLowerCase().includes(documentQuery.toLowerCase());
    return matchesQuery && (statusFilter === "all" || (statusFilter === "active" ? doc.active : !doc.active));
  });
  const refresh = async () => setRefreshed(await refreshKbDocuments());
  const mutate = async (commit: () => Promise<unknown>) => {
    setBusy("upload"); setFeedback(null);
    try { await commit(); await refresh(); setFeedback({ tone: "success", title: "Documento agregado" }); }
     catch (error) { setFeedback({ tone: "danger", retry: true, title: error instanceof ApiError && error.status === 403 ? "No tienes permiso para modificar la base de conocimientos." : "No pudimos procesar el documento" }); }
    finally { setBusy(null); }
  };
  const retry = onRetry ?? fetched.retry;
  const showWorkspace = (state === "ready" || state === "empty") && data;
  const submitUpload = () => {
    if (!file) return;
    const dot = file.name.lastIndexOf(".");
    const extension = dot > 0 ? file.name.slice(dot).toLowerCase() : "";
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setFeedback({ tone: "danger", title: "Formato no compatible. Usa PDF, Markdown, TXT o CSV." });
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setFeedback({ tone: "danger", title: "El archivo supera el tamaño máximo de 5 MB." });
      return;
    }
    const draft = { title, file, visibility };
    setUploadDraft(draft);
    void mutate(() => uploadKbDocument(draft.title, draft.file, draft.visibility));
  };
  const retryUpload = () => {
    if (uploadDraft) void mutate(() => uploadKbDocument(uploadDraft.title, uploadDraft.file, uploadDraft.visibility));
  };
  return <PageFrame title="Base de conocimientos" subtitle="Gestiona los documentos y prueba la recuperación de información." meta={!data ? "Documentos de la base de conocimientos" : undefined} titleAdornment={data ? <Badge>{docs.length} {docs.length === 1 ? "documento" : "documentos"}</Badge> : null} state={stateMessage(state)} className="kb-list">
     {showWorkspace ? <>
         <div className="kb-list__layout">
           <Card title="Documentos" className="kb-list__documents">
             <div className="kb-list__toolbar"><Input type="search" label="Buscar documentos" placeholder="Buscar documentos" value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)} /><div className="kb-list__filters"><Button variant="secondary" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((open) => !open)}>Filtros</Button>{filtersOpen ? <Select label="Estado" value={statusFilter} options={[{ value: "all", label: "Todos" }, { value: "active", label: "Activos" }, { value: "inactive", label: "Deshabilitados" }]} onChange={(event) => setStatusFilter(event.target.value)} /> : null}</div></div>
             {docs.length === 0 ? <EmptyState title="No hay documentos" description="Sube el primer documento para comenzar." /> : <>
               <div className="kb-list__table"><DataTable columns={columns(onOpenDocument)} rows={filteredDocs} rowKey={(doc) => String(doc.id)} /></div>
               <ul className="kb-list__mobile" aria-label="Documentos">{filteredDocs.map((doc) => <li key={doc.id} aria-label={doc.title}>
                 <DocumentIdentity doc={doc} onOpenDocument={onOpenDocument} />
                 <div className="kb-list__mobile-meta"><span>v{doc.active_version} · Activa</span><Badge tone={kbStatusTone(docStatus(doc))}>{kbStatusLabel(docStatus(doc))}</Badge><span className="kb-list__audience">{doc.visibility === "internal" ? <Icon icon={Lock} size="sm" /> : null}{TABLE_AUDIENCE_LABEL[doc.visibility]}</span><span>{doc.cost_meta !== null ? tabularNum(`$${doc.cost_meta.toFixed(6)}`) : "—"}</span></div>
               </li>)}</ul>
               <footer className="kb-list__count">{filteredDocs.length} {filteredDocs.length === 1 ? "documento" : "documentos"}</footer>
             </>}
           </Card>
           <div className="kb-list__secondary">
             <section aria-labelledby="kb-upload-heading"><h2 id="kb-upload-heading">Agregar documento</h2><div>{busy ? <StateMessage tone={KB_OPERATION_TONES.procesando} role="status" spinner title="Procesando documento" detail="Revisando el formato, tamaño y contenido." /> : null}{feedback ? <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.title} /> : null}<Input label="Título" placeholder="Título del documento" value={title} onChange={(event) => setTitle(event.target.value)} disabled={busy !== null} /><Input label="Archivo (PDF / MD / TXT / CSV)" type="file" accept={ACCEPTED_EXTENSIONS.join(",")} onChange={(event) => setFile(event.target.files?.[0] ?? null)} disabled={busy !== null} /><p className="kb-search__hint">Formatos admitidos: PDF, Markdown, TXT y CSV. Máximo 5 MB.</p><Select label="Audiencia" value={visibility} options={AUDIENCE_OPTIONS} onChange={(event) => setVisibility(event.target.value as KbVisibility)} disabled={busy !== null} /><p className="kb-search__hint">Un documento interno nunca se usa para responder a clientes.</p><Button disabled={busy !== null} onClick={submitUpload}>Agregar</Button>{feedback?.retry ? <Button variant="secondary" disabled={busy !== null} onClick={retryUpload}>Reintentar carga</Button> : null}</div></section>
             <SearchPanel />
           </div>
         </div>
      </> : null}
    {state === "error" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
