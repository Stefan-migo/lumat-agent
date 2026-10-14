import { useCallback, useRef, useState } from "react";
import { BookOpen, Download, FileSearch, FileText, Info, Paperclip, Upload } from "lucide-react";
import { ApiError, downloadProjectFile, listProjectFiles, refreshKbDocuments, uploadKbDocument, uploadProjectFile } from "../../api";
import type { Doc, ProjectFile, Role } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";
import { kbStatusLabel, kbStatusTone } from "../shared/toneMaps";

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function ProjectResources({ projectSlug, projectId, role }: { projectSlug: string; projectId: number; role?: Role }) {
  const loadFiles = useCallback(() => listProjectFiles(projectSlug), [projectSlug]);
  const files = useAsyncData(loadFiles, true);
  const isAdmin = role === "admin";
  const loadDocs = useCallback(() => refreshKbDocuments(), []);
  const docs = useAsyncData(loadDocs, isAdmin);
  const inputRef = useRef<HTMLInputElement>(null);
  const kbInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadingKb, setUploadingKb] = useState(false);
  const [kbFeedback, setKbFeedback] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const [busyFileId, setBusyFileId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "danger"; text: string } | null>(null);

  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    setFeedback(null);
    try {
      await uploadProjectFile(projectSlug, file);
      setFeedback({ tone: "success", text: "Archivo subido correctamente." });
      files.retry();
      if (isAdmin) docs.retry();
    } catch (reason: unknown) {
      setFeedback({ tone: "danger", text: reason instanceof ApiError ? reason.detail : "No pudimos subir el archivo." });
    } finally {
      setUploading(false);
    }
  };

  const download = async (row: ProjectFile) => {
    setBusyFileId(row.id);
    setFeedback(null);
    try {
      await downloadProjectFile(projectSlug, row.id, row.filename);
    } catch (reason: unknown) {
      setFeedback({ tone: "danger", text: reason instanceof ApiError ? reason.detail : "No pudimos descargar el archivo." });
    } finally {
      setBusyFileId(null);
    }
  };

  // Add a document straight to the project-scoped KB (POST /kb with project_id).
  // Unlike a project file, this does not create a ProjectFile, so it only shows
  // in the knowledge card; project files are indexed automatically instead.
  const uploadToKb = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploadingKb(true);
    setKbFeedback(null);
    try {
      await uploadKbDocument(file.name.replace(/\.[^.]+$/, ""), file, "internal", projectId);
      setKbFeedback({ tone: "success", text: "Documento agregado a la base de conocimientos." });
      if (isAdmin) docs.retry();
    } catch (reason: unknown) {
      setKbFeedback({ tone: "danger", text: reason instanceof ApiError ? reason.detail : "No pudimos agregar el documento a la base de conocimientos." });
    } finally {
      setUploadingKb(false);
    }
  };

  const kbState = (row: ProjectFile): { label: string; tone: "success" | "danger" | "neutral" } =>
    row.kb_document_id != null ? { label: "En la KB", tone: "success" }
      : row.status === "failed" ? { label: "Falló", tone: "danger" }
        : { label: "No indexado", tone: "neutral" };
  const fileColumns: Column<ProjectFile>[] = [
    { key: "filename", header: "Archivo", render: (row) => <span><Icon icon={FileText} /> {row.filename}</span> },
    { key: "size", header: "Tamaño", render: (row) => formatBytes(row.size) },
    { key: "kb", header: "En la KB", render: (row) => { const state = kbState(row); return <Badge tone={state.tone}>{state.label}</Badge>; } },
    { key: "created_at", header: "Subido", render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString("es-CL") : "—" },
    { key: "download", header: "Descargar", render: (row) => <Button variant="tertiary" aria-label={`Descargar ${row.filename}`} disabled={busyFileId === row.id} onClick={() => void download(row)}><Icon icon={Download} /></Button> },
  ];
  const docColumns: Column<Doc>[] = [
    { key: "title", header: "Documento", render: (doc) => doc.title },
    { key: "format", header: "Formato", render: (doc) => doc.format.toUpperCase() },
    { key: "version", header: "Versión", render: (doc) => `v${doc.active_version}` },
    { key: "status", header: "Estado", render: (doc) => { const status = doc.active ? "activo" : "deshabilitado"; return <Badge tone={kbStatusTone(status)}>{kbStatusLabel(status)}</Badge>; } },
  ];
  const projectFiles = files.data?.files ?? [];
  const filesState = files.state === "empty" || (files.state === "ready" && projectFiles.length === 0) ? "empty" : files.state;
  // Documents already surfaced by the file card (auto-indexed uploads) are not
  // repeated here; this card owns what was added straight to the project KB.
  const indexedDocIds = new Set(projectFiles.map((file) => file.kb_document_id).filter((id): id is number => id != null));
  const directDocs = (docs.data?.docs ?? []).filter((doc) => doc.project_id === projectId && !indexedDocIds.has(doc.id));
  const docsState = docs.state === "empty" || (docs.state === "ready" && directDocs.length === 0) ? "empty" : docs.state;

  return <div className="projects-page__resources">
    <Card
      icon={Paperclip}
      title="Archivos del proyecto"
      headerAction={<><Badge>{files.data?.files?.length ?? 0}</Badge><Button variant="secondary" disabled={uploading} onClick={() => inputRef.current?.click()}>{uploading ? "Subiendo…" : "Subir archivo"}</Button></>}
    >
      <input type="file" aria-label="Archivo del proyecto" hidden ref={inputRef} onChange={(event) => void upload(event)} />
      {feedback ? <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.text} /> : null}
      {filesState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando archivos" /> : null}
      {filesState === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar los archivos" /><Button variant="secondary" onClick={files.retry}>Reintentar</Button></> : null}
      {filesState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver los archivos de este proyecto." /> : null}
      {filesState === "empty" ? <EmptyState variant="dashed" icon={Upload} title="Aún no hay archivos" description="Sube el primer documento de este proyecto." /> : null}
      {filesState === "ready" ? <DataTable columns={fileColumns} rows={files.data?.files ?? []} rowKey={(row) => String(row.id)} /> : null}
    </Card>
    <Card
      icon={BookOpen}
      title="Conocimiento del proyecto"
      headerAction={isAdmin ? <><Badge>{directDocs.length}</Badge><Button variant="secondary" disabled={uploadingKb} onClick={() => kbInputRef.current?.click()}>{uploadingKb ? "Subiendo…" : "Subir archivo a la KB"}</Button></> : null}
      footer={<p className="projects-page__note"><Icon icon={Info} size="sm" />Los archivos del proyecto se comparten como contexto; los adjuntos de un hilo permanecen en ese hilo.</p>}
    >
      <input type="file" aria-label="Documento de la base de conocimientos" hidden ref={kbInputRef} onChange={(event) => void uploadToKb(event)} />
      {kbFeedback ? <StateMessage tone={kbFeedback.tone} role={kbFeedback.tone === "danger" ? "alert" : "status"} title={kbFeedback.text} /> : null}
      {!isAdmin ? <StateMessage tone="info" role="status" title="Conocimiento del proyecto" detail="Solo los administradores pueden ver los documentos indexados de un proyecto." /> : <>
        {docsState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conocimiento" /> : null}
        {docsState === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el conocimiento del proyecto" /><Button variant="secondary" onClick={docs.retry}>Reintentar</Button></> : null}
        {docsState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver el conocimiento del proyecto." /> : null}
        {docsState === "empty" ? <EmptyState variant="dashed" icon={FileSearch} title="Sin documentos agregados a la KB" description="Sube un documento directo a la KB del proyecto; los archivos del proyecto se indexan solos arriba." /> : null}
        {docsState === "ready" ? <DataTable columns={docColumns} rows={directDocs} rowKey={(row) => String(row.id)} /> : null}
      </>}
    </Card>
  </div>;
}
