import { useCallback, useRef, useState } from "react";
import { Download, FileText } from "lucide-react";
import { ApiError, downloadProjectFile, listProjectFiles, refreshKbDocuments, uploadProjectFile } from "../../api";
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
  const [uploading, setUploading] = useState(false);
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

  const fileColumns: Column<ProjectFile>[] = [
    { key: "filename", header: "Archivo", render: (row) => <span><Icon icon={FileText} /> {row.filename}</span> },
    { key: "size", header: "Tamaño", render: (row) => formatBytes(row.size) },
    { key: "status", header: "Estado", render: (row) => <Badge tone={row.status === "ready" ? "success" : row.status === "failed" ? "danger" : "neutral"}>{row.status === "ready" ? "Listo" : row.status === "failed" ? "Falló" : row.status}</Badge> },
    { key: "created_at", header: "Subido", render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString("es-CL") : "—" },
    { key: "download", header: "Descargar", render: (row) => <Button variant="tertiary" aria-label={`Descargar ${row.filename}`} disabled={busyFileId === row.id} onClick={() => void download(row)}><Icon icon={Download} /></Button> },
  ];
  const docColumns: Column<Doc>[] = [
    { key: "title", header: "Documento", render: (doc) => doc.title },
    { key: "format", header: "Formato", render: (doc) => doc.format.toUpperCase() },
    { key: "version", header: "Versión", render: (doc) => `v${doc.active_version}` },
    { key: "status", header: "Estado", render: (doc) => { const status = doc.active ? "activo" : "deshabilitado"; return <Badge tone={kbStatusTone(status)}>{kbStatusLabel(status)}</Badge>; } },
  ];
  const filesState = files.state === "empty" || (files.state === "ready" && (files.data?.files ?? []).length === 0) ? "empty" : files.state;
  const projectDocs = (docs.data?.docs ?? []).filter((doc) => doc.project_id === projectId);
  const docsState = docs.state === "empty" || (docs.state === "ready" && projectDocs.length === 0) ? "empty" : docs.state;

  return <Card title="Archivos y conocimiento">
    <section>
      <h3>Archivos del proyecto</h3>
      <Button variant="secondary" disabled={uploading} onClick={() => inputRef.current?.click()}>{uploading ? "Subiendo…" : "Subir archivo"}</Button>
      <input type="file" aria-label="Archivo del proyecto" hidden ref={inputRef} onChange={(event) => void upload(event)} />
      {feedback ? <StateMessage tone={feedback.tone} role={feedback.tone === "danger" ? "alert" : "status"} title={feedback.text} /> : null}
      {filesState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando archivos" /> : null}
      {filesState === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar los archivos" /><Button variant="secondary" onClick={files.retry}>Reintentar</Button></> : null}
      {filesState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver los archivos de este proyecto." /> : null}
      {filesState === "empty" ? <EmptyState title="Sin archivos" description="Sube el primer archivo de este proyecto." /> : null}
      {filesState === "ready" ? <DataTable columns={fileColumns} rows={files.data?.files ?? []} rowKey={(row) => String(row.id)} /> : null}
    </section>
    <section>
      <h3>Conocimiento del proyecto</h3>
      {!isAdmin ? <StateMessage tone="info" role="status" title="Conocimiento del proyecto" detail="Solo los administradores pueden ver los documentos indexados de un proyecto." /> : <>
        {docsState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conocimiento" /> : null}
        {docsState === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el conocimiento del proyecto" /><Button variant="secondary" onClick={docs.retry}>Reintentar</Button></> : null}
        {docsState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver el conocimiento del proyecto." /> : null}
        {docsState === "empty" ? <EmptyState title="Sin documentos indexados" description="Los archivos compatibles que subas se indexan aquí automáticamente." /> : null}
        {docsState === "ready" ? <DataTable columns={docColumns} rows={projectDocs} rowKey={(row) => String(row.id)} /> : null}
      </>}
    </section>
  </Card>;
}
