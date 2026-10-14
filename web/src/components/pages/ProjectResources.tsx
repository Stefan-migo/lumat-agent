import { useCallback, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Download,
  FileImage,
  FileSearch,
  FileText,
  Folder,
  FolderPlus,
  Info,
  Paperclip,
  Pencil,
  Trash2,
  Upload,
} from "lucide-react";
import {
  ApiError,
  createProjectFolder,
  deleteProjectFile,
  deleteProjectFolder,
  downloadProjectFile,
  listProjectFiles,
  listProjectFolders,
  moveProjectFile,
  refreshKbDocuments,
  renameProjectFolder,
  uploadKbDocument,
  uploadProjectFile,
} from "../../api";
import type { Doc, ProjectFile, ProjectFolder, Role } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { Select } from "../primitives/Select";
import { useToast } from "../primitives/Toast";
import { DataTable, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";
import { kbStatusLabel, kbStatusTone } from "../shared/toneMaps";

const ROOT_DROP_KEY = "root";

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(file: ProjectFile) {
  return file.content_type.startsWith("image/") ? FileImage : FileText;
}

type FolderDialogState =
  | { mode: "create"; parentId: number | null }
  | { mode: "rename"; folder: ProjectFolder };

type DeleteTarget = { kind: "file"; file: ProjectFile } | { kind: "folder"; folder: ProjectFolder };

export function ProjectResources({
  projectSlug,
  projectId,
  projectName,
  role,
}: {
  projectSlug: string;
  projectId: number;
  projectName: string;
  role?: Role;
}) {
  const isAdmin = role === "admin";
  const loadFiles = useCallback(() => listProjectFiles(projectSlug), [projectSlug]);
  const files = useAsyncData(loadFiles, true);
  const loadFolders = useCallback(() => listProjectFolders(projectSlug), [projectSlug]);
  const folders = useAsyncData(loadFolders, true);
  const loadDocs = useCallback(() => refreshKbDocuments(), []);
  const docs = useAsyncData(loadDocs, isAdmin);

  const uploadInputRef = useRef<HTMLInputElement>(null);
  const kbInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const [uploadingKb, setUploadingKb] = useState(false);
  const [busyFileId, setBusyFileId] = useState<number | null>(null);

  const [folderDialog, setFolderDialog] = useState<FolderDialogState | null>(null);
  const [folderName, setFolderName] = useState("");
  const [folderError, setFolderError] = useState<string | null>(null);
  const [folderBusy, setFolderBusy] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadFolderId, setUploadFolderId] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [newFolderBusy, setNewFolderBusy] = useState(false);

  const projectFiles = files.data?.files ?? [];
  const projectFolders = folders.data?.folders ?? [];

  const childFolders = useMemo(() => {
    const map = new Map<number | null, ProjectFolder[]>();
    for (const folder of projectFolders) {
      const list = map.get(folder.parent_id) ?? [];
      list.push(folder);
      map.set(folder.parent_id, list);
    }
    return map;
  }, [projectFolders]);

  const filesByFolder = useMemo(() => {
    const map = new Map<number | null, ProjectFile[]>();
    for (const file of projectFiles) {
      const list = map.get(file.folder_id) ?? [];
      list.push(file);
      map.set(file.folder_id, list);
    }
    return map;
  }, [projectFiles]);

  // Total files inside each folder subtree (a collapsed folder still counts its contents).
  const fileCount = useMemo(() => {
    const counts = new Map<number, number>();
    const count = (folderId: number): number => {
      const cached = counts.get(folderId);
      if (cached !== undefined) return cached;
      let total = (filesByFolder.get(folderId) ?? []).length;
      for (const child of childFolders.get(folderId) ?? []) total += count(child.id);
      counts.set(folderId, total);
      return total;
    };
    for (const folder of projectFolders) count(folder.id);
    return counts;
  }, [projectFolders, childFolders, filesByFolder]);

  // Folder id -> "Parent / Child" label, for the destination selector.
  const folderPaths = useMemo(() => {
    const paths = new Map<number, string>();
    const walk = (parentId: number | null, prefix: string) => {
      for (const folder of childFolders.get(parentId) ?? []) {
        const label = prefix ? `${prefix} / ${folder.name}` : folder.name;
        paths.set(folder.id, label);
        walk(folder.id, label);
      }
    };
    walk(null, "");
    return paths;
  }, [childFolders]);

  const destinationOptions = [
    { value: "root", label: projectName },
    ...[...folderPaths].map(([id, label]) => ({ value: String(id), label })),
  ];

  const q = query.trim().toLowerCase();
  const matches = (text: string) => text.toLowerCase().includes(q);
  const fileMatches = (file: ProjectFile) => q === "" || matches(file.filename);
  const subtreeMatches = (folderId: number): boolean => {
    if ((filesByFolder.get(folderId) ?? []).some((file) => matches(file.filename))) return true;
    return (childFolders.get(folderId) ?? []).some((child) => matches(child.name) || subtreeMatches(child.id));
  };
  const folderMatches = (folder: ProjectFolder) => q === "" || matches(folder.name) || subtreeMatches(folder.id);

  const kbState = (row: ProjectFile): { label: string; tone: "success" | "danger" | "neutral" } =>
    row.kb_document_id != null ? { label: "En la KB", tone: "success" }
      : row.status === "failed" ? { label: "Falló", tone: "danger" }
        : { label: "No indexado", tone: "neutral" };

  const download = async (row: ProjectFile) => {
    setBusyFileId(row.id);
    try {
      await downloadProjectFile(projectSlug, row.id, row.filename);
    } catch (reason: unknown) {
      toast.show(reason instanceof ApiError ? reason.detail : "No pudimos descargar el archivo.", "danger");
    } finally {
      setBusyFileId(null);
    }
  };

  const moveFile = async (fileId: number, folderId: number | null) => {
    try {
      await moveProjectFile(projectSlug, fileId, folderId);
      files.retry();
    } catch (reason: unknown) {
      toast.show(reason instanceof ApiError ? reason.detail : "No pudimos mover el archivo.", "danger");
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
    try {
      await uploadKbDocument(file.name.replace(/\.[^.]+$/, ""), file, "internal", projectId);
      toast.show("Documento agregado a la base de conocimientos.");
      if (isAdmin) docs.retry();
    } catch (reason: unknown) {
      toast.show(reason instanceof ApiError ? reason.detail : "No pudimos agregar el documento a la base de conocimientos.", "danger");
    } finally {
      setUploadingKb(false);
    }
  };

  const openUpload = (folderId: number | null = null) => {
    setUploadFile(null);
    setUploadFolderId(folderId);
    setUploadError(null);
    setNewFolderOpen(false);
    setNewFolderName("");
    setUploadOpen(true);
  };

  const closeUpload = () => {
    setUploadOpen(false);
    setUploadFile(null);
    setUploadError(null);
    setNewFolderOpen(false);
    setNewFolderName("");
  };

  const submitUpload = async () => {
    if (!uploadFile) return;
    setUploadBusy(true);
    setUploadError(null);
    try {
      await uploadProjectFile(projectSlug, uploadFile, uploadFolderId);
      closeUpload();
      toast.show("Archivo subido correctamente.");
      files.retry();
      if (isAdmin) docs.retry();
    } catch (reason: unknown) {
      setUploadError(reason instanceof ApiError ? reason.detail : "No pudimos subir el archivo.");
    } finally {
      setUploadBusy(false);
    }
  };

  const createFolderInline = async () => {
    const name = newFolderName.trim();
    if (!name) return;
    setNewFolderBusy(true);
    setUploadError(null);
    try {
      const response = await createProjectFolder(projectSlug, { name, parent_id: uploadFolderId });
      setUploadFolderId(response.folder.id);
      setNewFolderName("");
      setNewFolderOpen(false);
      folders.retry();
    } catch (reason: unknown) {
      setUploadError(reason instanceof ApiError ? reason.detail : "No pudimos crear la carpeta.");
    } finally {
      setNewFolderBusy(false);
    }
  };

  const toggleFolder = (folderId: number) => {
    setCollapsed((previous) => {
      const next = new Set(previous);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  };

  const expandFolder = (folderId: number) => {
    setCollapsed((previous) => {
      if (!previous.has(folderId)) return previous;
      const next = new Set(previous);
      next.delete(folderId);
      return next;
    });
  };

  const openCreate = (parentId: number | null) => {
    if (parentId != null) expandFolder(parentId);
    setFolderName("");
    setFolderError(null);
    setFolderDialog({ mode: "create", parentId });
  };

  const openRename = (folder: ProjectFolder) => {
    setFolderName(folder.name);
    setFolderError(null);
    setFolderDialog({ mode: "rename", folder });
  };

  const closeFolderDialog = () => {
    setFolderDialog(null);
    setFolderName("");
    setFolderError(null);
  };

  const onFolderAction = (folder: ProjectFolder, value: string) => {
    if (value === "new") openCreate(folder.id);
    else if (value === "rename") openRename(folder);
    else if (value === "delete") { setDeleteError(null); setDeleteTarget({ kind: "folder", folder }); }
  };

  const submitFolder = async () => {
    const dialog = folderDialog;
    if (!dialog) return;
    const name = folderName.trim();
    if (!name) return;
    setFolderBusy(true);
    setFolderError(null);
    try {
      if (dialog.mode === "rename") {
        await renameProjectFolder(projectSlug, dialog.folder.id, name);
      } else {
        await createProjectFolder(projectSlug, { name, parent_id: dialog.parentId });
      }
      closeFolderDialog();
      folders.retry();
    } catch (reason: unknown) {
      setFolderError(reason instanceof ApiError ? reason.detail : "No pudimos guardar la carpeta.");
    } finally {
      setFolderBusy(false);
    }
  };

  const confirmDelete = async () => {
    const target = deleteTarget;
    if (!target) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      if (target.kind === "file") {
        await deleteProjectFile(projectSlug, target.file.id);
        toast.show("Archivo eliminado.");
      } else {
        await deleteProjectFolder(projectSlug, target.folder.id);
        toast.show("Carpeta eliminada.");
      }
      setDeleteTarget(null);
      files.retry();
      folders.retry();
      if (isAdmin) docs.retry();
    } catch (reason: unknown) {
      setDeleteError(reason instanceof ApiError ? reason.detail : "No pudimos eliminar el elemento.");
    } finally {
      setDeleteBusy(false);
    }
  };

  const dropProps = (key: string, folderId: number | null) => ({
    onDragOver: (event: React.DragEvent) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; },
    onDragEnter: () => setDropTarget(key),
    onDragLeave: () => setDropTarget((current) => (current === key ? null : current)),
    onDrop: (event: React.DragEvent) => {
      event.preventDefault();
      setDropTarget(null);
      const fileId = Number(event.dataTransfer.getData("text/plain"));
      if (Number.isFinite(fileId) && fileId > 0) void moveFile(fileId, folderId);
    },
  });

  const renderFile = (file: ProjectFile) => {
    if (!fileMatches(file)) return null;
    const state = kbState(file);
    return (
      <li
        key={`file-${file.id}`}
        className="file-tree__row file-tree__row--file"
        draggable
        onDragStart={(event) => { event.dataTransfer.setData("text/plain", String(file.id)); event.dataTransfer.effectAllowed = "move"; }}
      >
        <span className="file-tree__spacer" aria-hidden="true" />
        <Icon icon={fileIcon(file)} size="sm" />
        <span className="file-tree__name">{file.filename}</span>
        <span className="file-tree__size">{formatBytes(file.size)}</span>
        <Badge tone={state.tone}>{state.label}</Badge>
        <Button variant="tertiary" aria-label={`Descargar ${file.filename}`} disabled={busyFileId === file.id} onClick={() => void download(file)}><Icon icon={Download} /></Button>
        <Button variant="tertiary" className="file-tree__danger" aria-label={`Eliminar ${file.filename}`} onClick={() => { setDeleteError(null); setDeleteTarget({ kind: "file", file }); }}><Icon icon={Trash2} /></Button>
      </li>
    );
  };

  const renderFolder = (folder: ProjectFolder) => {
    if (!folderMatches(folder)) return null;
    const isCollapsed = collapsed.has(folder.id) && q === "";
    const kids = (childFolders.get(folder.id) ?? []).filter(folderMatches);
    const ownFiles = (filesByFolder.get(folder.id) ?? []).filter(fileMatches);
    const count = fileCount.get(folder.id) ?? 0;
    return (
      <li key={`folder-${folder.id}`} className="file-tree__node">
        <div
          className={`file-tree__row file-tree__row--folder${dropTarget === String(folder.id) ? " is-drop-target" : ""}`}
          {...dropProps(String(folder.id), folder.id)}
        >
          <button type="button" className="file-tree__twisty" aria-label={`${isCollapsed ? "Expandir" : "Contraer"} ${folder.name}`} aria-expanded={!isCollapsed} onClick={() => toggleFolder(folder.id)}>
            <Icon icon={isCollapsed ? ChevronRight : ChevronDown} size="sm" />
          </button>
          <Icon icon={Folder} size="sm" />
          <span className="file-tree__name">{folder.name}</span>
          {count > 0 ? <span className="file-tree__count">({count})</span> : null}
          <span className="file-tree__grow" aria-hidden="true" />
          <Menu
            trigger="icon"
            label={`Acciones de ${folder.name}`}
            align="end"
            items={[
              { value: "new", label: "Nueva subcarpeta", icon: FolderPlus },
              { value: "rename", label: "Renombrar", icon: Pencil },
              { value: "delete", label: "Eliminar", icon: Trash2, tone: "danger" },
            ]}
            onSelect={(value) => onFolderAction(folder, value)}
          />
        </div>
        {!isCollapsed ? (
          <ul className="file-tree__children">
            {kids.map(renderFolder)}
            {ownFiles.map(renderFile)}
            {kids.length === 0 && ownFiles.length === 0 ? <li className="file-tree__empty">Carpeta vacía</li> : null}
          </ul>
        ) : null}
      </li>
    );
  };

  const rootFolders = (childFolders.get(null) ?? []).filter(folderMatches);
  const rootFiles = (filesByFolder.get(null) ?? []).filter(fileMatches);

  const loadState =
    files.state === "error" || folders.state === "error" ? "error"
      : files.state === "denied" || folders.state === "denied" ? "denied"
        : files.state === "loading" || folders.state === "loading" ? "loading"
          : "ready";
  const isEmpty = loadState === "ready" && projectFiles.length === 0 && projectFolders.length === 0;

  const docColumns: Column<Doc>[] = [
    { key: "title", header: "Documento", render: (doc) => doc.title },
    { key: "format", header: "Formato", render: (doc) => doc.format.toUpperCase() },
    { key: "version", header: "Versión", render: (doc) => `v${doc.active_version}` },
    { key: "status", header: "Estado", render: (doc) => { const status = doc.active ? "activo" : "deshabilitado"; return <Badge tone={kbStatusTone(status)}>{kbStatusLabel(status)}</Badge>; } },
  ];
  // Documents already surfaced by the file card (auto-indexed uploads) are not
  // repeated here; this card owns what was added straight to the project KB.
  const indexedDocIds = new Set(projectFiles.map((file) => file.kb_document_id).filter((id): id is number => id != null));
  const directDocs = (docs.data?.docs ?? []).filter((doc) => doc.project_id === projectId && !indexedDocIds.has(doc.id));
  const docsState = docs.state === "empty" || (docs.state === "ready" && directDocs.length === 0) ? "empty" : docs.state;

  return <div className="projects-page__resources">
    <Card
      icon={Paperclip}
      title="Archivos del proyecto"
      headerAction={<Badge>{projectFiles.length}</Badge>}
      footer={<p className="projects-page__resources-footer">{projectFiles.length} archivos · {projectFolders.length} carpetas</p>}
    >
      <div className="projects-page__resources-toolbar">
        <SearchInput aria-label="Buscar archivo o carpeta" placeholder="Buscar archivo o carpeta…" onSearch={setQuery} />
        <Menu
          trigger="icon"
          label="Acciones de archivos"
          align="end"
          items={[
            { value: "upload", label: "Subir archivo", icon: Upload },
            { value: "folder", label: "Nueva carpeta", icon: FolderPlus },
          ]}
          onSelect={(value) => (value === "upload" ? openUpload() : openCreate(null))}
        />
      </div>
      {loadState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando archivos" /> : null}
      {loadState === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar los archivos" /><Button variant="secondary" onClick={() => { files.retry(); folders.retry(); }}>Reintentar</Button></> : null}
      {loadState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver los archivos de este proyecto." /> : null}
      {isEmpty ? <EmptyState variant="dashed" icon={Upload} title="Aún no hay archivos" description="Sube el primer documento de este proyecto." /> : null}
      {loadState === "ready" && !isEmpty ? (
        <div className="file-tree">
          <div
            className={`file-tree__row file-tree__row--root${dropTarget === ROOT_DROP_KEY ? " is-drop-target" : ""}`}
            {...dropProps(ROOT_DROP_KEY, null)}
          >
            <span className="file-tree__spacer" aria-hidden="true" />
            <Icon icon={Folder} size="sm" />
            <span className="file-tree__name">{projectName}</span>
            <span className="file-tree__grow" aria-hidden="true" />
          </div>
          <ul className="file-tree__children file-tree__children--root">
            {rootFolders.map(renderFolder)}
            {rootFiles.map(renderFile)}
            {rootFolders.length === 0 && rootFiles.length === 0 ? <li className="file-tree__empty">Sin resultados</li> : null}
          </ul>
        </div>
      ) : null}
    </Card>
    <Card
      icon={BookOpen}
      title="Conocimiento del proyecto"
      headerAction={isAdmin ? <><Badge>{directDocs.length}</Badge><Button variant="secondary" disabled={uploadingKb} onClick={() => kbInputRef.current?.click()}>{uploadingKb ? "Subiendo…" : "Subir archivo a la KB"}</Button></> : null}
      footer={<p className="projects-page__note"><Icon icon={Info} size="sm" />Los archivos del proyecto se comparten como contexto; los adjuntos de un hilo permanecen en ese hilo.</p>}
    >
      <input type="file" aria-label="Documento de la base de conocimientos" hidden ref={kbInputRef} onChange={(event) => void uploadToKb(event)} />
      {!isAdmin ? <StateMessage tone="info" role="status" title="Conocimiento del proyecto" detail="Solo los administradores pueden ver los documentos indexados de un proyecto." /> : <>
        {docsState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conocimiento" /> : null}
        {docsState === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el conocimiento del proyecto" /><Button variant="secondary" onClick={docs.retry}>Reintentar</Button></> : null}
        {docsState === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver el conocimiento del proyecto." /> : null}
        {docsState === "empty" ? <EmptyState variant="dashed" icon={FileSearch} title="Sin documentos agregados a la KB" description="Sube un documento directo a la KB del proyecto; los archivos del proyecto se indexan solos arriba." /> : null}
        {docsState === "ready" ? <div className="projects-page__table-scroll"><DataTable columns={docColumns} rows={directDocs} rowKey={(row) => String(row.id)} /></div> : null}
      </>}
    </Card>

    <Dialog open={uploadOpen} onClose={closeUpload} title="Subir archivo" icon={Upload}>
      <div className="file-tree__dialog-body">
        <Select
          label="Carpeta de destino"
          value={uploadFolderId == null ? "root" : String(uploadFolderId)}
          options={destinationOptions}
          onChange={(event) => setUploadFolderId(event.target.value === "root" ? null : Number(event.target.value))}
        />
        <input ref={uploadInputRef} type="file" aria-label="Archivo del proyecto" hidden onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
        <div className="file-tree__upload-row">
          <Button variant="secondary" onClick={() => uploadInputRef.current?.click()}>
            <Icon icon={Upload} /> {uploadFile ? uploadFile.name : "Elegir archivo"}
          </Button>
        </div>
        {newFolderOpen ? (
          <div className="file-tree__new-folder">
            <Input label="Nombre de la carpeta" value={newFolderName} autoFocus placeholder="Ej. Reportes" onChange={(event) => setNewFolderName(event.target.value)} />
            <Button variant="secondary" disabled={newFolderBusy || newFolderName.trim() === ""} onClick={() => void createFolderInline()}>{newFolderBusy ? "Creando…" : "Crear carpeta"}</Button>
          </div>
        ) : (
          <Button variant="tertiary" onClick={() => setNewFolderOpen(true)}><Icon icon={FolderPlus} /> Crear carpeta</Button>
        )}
        {uploadError ? <StateMessage tone="danger" role="alert" title={uploadError} /> : null}
      </div>
      <div className="file-tree__dialog-actions">
        <Button variant="secondary" onClick={closeUpload}>Cancelar</Button>
        <Button disabled={uploadBusy || !uploadFile} onClick={() => void submitUpload()}>{uploadBusy ? "Subiendo…" : "Subir archivo"}</Button>
      </div>
    </Dialog>

    <Dialog
      open={folderDialog !== null}
      onClose={closeFolderDialog}
      title={folderDialog?.mode === "rename" ? "Renombrar carpeta" : "Nueva carpeta"}
      icon={folderDialog?.mode === "rename" ? Pencil : FolderPlus}
    >
      <div className="file-tree__dialog-body">
        <Input
          label="Nombre de la carpeta"
          value={folderName}
          placeholder="Ej. Reportes"
          autoFocus
          error={folderError ?? undefined}
          onChange={(event) => setFolderName(event.target.value)}
        />
      </div>
      <div className="file-tree__dialog-actions">
        <Button variant="secondary" onClick={closeFolderDialog}>Cancelar</Button>
        <Button disabled={folderBusy || folderName.trim() === ""} onClick={() => void submitFolder()}>
          {folderBusy ? "Guardando…" : folderDialog?.mode === "rename" ? "Guardar" : "Crear carpeta"}
        </Button>
      </div>
    </Dialog>

    <Dialog
      open={deleteTarget !== null}
      onClose={() => { setDeleteTarget(null); setDeleteError(null); }}
      title={deleteTarget?.kind === "folder" ? "Eliminar carpeta" : "Eliminar archivo"}
      icon={Trash2}
    >
      {deleteTarget ? <>
        <p className="file-tree__dialog-question">
          {deleteTarget.kind === "file" ? "¿Quieres eliminar este archivo del proyecto?" : "¿Quieres eliminar esta carpeta del proyecto?"}
        </p>
        <div className="file-tree__dialog-preview">
          <Icon icon={deleteTarget.kind === "file" ? fileIcon(deleteTarget.file) : Folder} />
          <div className="file-tree__dialog-preview-copy">
            <p className="file-tree__dialog-preview-name">{deleteTarget.kind === "file" ? deleteTarget.file.filename : deleteTarget.folder.name}</p>
            <p className="file-tree__dialog-preview-meta">
              {deleteTarget.kind === "file"
                ? `${formatBytes(deleteTarget.file.size)} · ${kbState(deleteTarget.file).label}`
                : `${fileCount.get(deleteTarget.folder.id) ?? 0} archivos`}
            </p>
          </div>
        </div>
        <p className="file-tree__dialog-project"><Icon icon={Folder} size="sm" /> Proyecto: {projectName}</p>
        {deleteError ? <StateMessage tone="danger" role="alert" title={deleteError} /> : null}
      </> : null}
      <div className="file-tree__dialog-actions">
        <Button variant="secondary" onClick={() => { setDeleteTarget(null); setDeleteError(null); }}>Cancelar</Button>
        <Button variant="danger" disabled={deleteBusy} onClick={() => void confirmDelete()}>
          <Icon icon={Trash2} /> {deleteBusy ? "Eliminando…" : deleteTarget?.kind === "folder" ? "Eliminar carpeta" : "Eliminar archivo"}
        </Button>
      </div>
    </Dialog>
  </div>;
}
