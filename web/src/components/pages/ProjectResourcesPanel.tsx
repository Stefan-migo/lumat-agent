import { useEffect, useRef, useState } from "react";
import { BookOpen, ChevronDown, ChevronRight, Download, FileText, Folder, FolderPlus, Lock, Sparkles, Trash2, Upload } from "lucide-react";
import { ApiError, createProjectFolder, deleteProjectFile, deleteProjectFolder, downloadProjectFile, getThreadResources, listProjectFiles, listProjectFolders, moveProjectFile, refreshKbDocuments, uploadProjectFile } from "../../api";
import type { Doc, Project, ProjectFile, ProjectFolder, ThreadResourceSkill } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { StateMessage } from "../shared/StateMessage";

interface ProjectResourcesPanelProps {
  project?: Project;
  threadId?: number;
  expanded: boolean;
  onSummary?: (summary: string) => void;
}

/** Tree drags carry their own type so a folder drop can tell "move this file"
 *  apart from "upload these OS files". */
const PROJECT_FILE_MOVE_TYPE = "application/x-lumat-project-file-move";

const pluralize = (count: number, singular: string, plural: string) => `${count} ${count === 1 ? singular : plural}`;

export function ProjectResourcesPanel({ project, threadId, expanded, onSummary }: ProjectResourcesPanelProps) {
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [folders, setFolders] = useState<ProjectFolder[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [skills, setSkills] = useState<ThreadResourceSkill[]>([]);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [folderToDelete, setFolderToDelete] = useState<ProjectFolder | null>(null);
  const [fileToDelete, setFileToDelete] = useState<ProjectFile | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const uploadFolder = useRef<number | null>(null);
  const onSummaryRef = useRef(onSummary);
  onSummaryRef.current = onSummary;

  useEffect(() => {
    let live = true;
    setError(null);
    setFiles([]);
    setFolders([]);
    setDocs([]);
    setSkills([]);
    if (!expanded || !project) {
      setLoading(false);
      return () => { live = false; };
    }
    setLoading(true);
    const loadSkills = threadId ? getThreadResources(threadId) : Promise.resolve(null);
    void Promise.all([
      listProjectFiles(project.slug),
      listProjectFolders(project.slug),
      refreshKbDocuments(project.id),
      loadSkills,
    ]).then(([fileResult, folderResult, kbResult, resourceResult]) => {
      if (!live) return;
      const projectDocs = kbResult.docs.filter((doc) => doc.project_id === project.id);
      const loadedSkills = resourceResult?.available.skills ?? [];
      setFiles(fileResult.files);
      setFolders(folderResult.folders);
      setDocs(projectDocs);
      setSkills(loadedSkills);
      onSummaryRef.current?.(`${pluralize(fileResult.files.length, "archivo", "archivos")} · ${pluralize(projectDocs.length, "documento", "documentos")} · ${pluralize(loadedSkills.length, "habilidad", "habilidades")}`);
    }).catch((reason: unknown) => {
      if (live) setError(reason instanceof ApiError ? reason.detail : "No pudimos cargar los recursos del proyecto.");
    }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [expanded, project?.id, project?.slug, threadId]);

  const reloadTree = async () => {
    if (!project) return;
    const [fileResult, folderResult] = await Promise.all([listProjectFiles(project.slug), listProjectFolders(project.slug)]);
    setFiles(fileResult.files);
    setFolders(folderResult.folders);
  };
  const upload = async (file?: File, folderId?: number | null) => {
    if (!project || !file) return;
    setBusy(true);
    setError(null);
    try { await uploadProjectFile(project.slug, file, folderId); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos subir el archivo."); }
    finally { setBusy(false); }
  };
  const createFolder = async () => {
    if (!project || !folderName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createProjectFolder(project.slug, { name: folderName.trim(), parent_id: null });
      setFolderName("");
      setCreateFolderOpen(false);
      await reloadTree();
    } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos crear la carpeta."); }
    finally { setBusy(false); }
  };
  const download = async (file: ProjectFile) => {
    if (!project) return;
    try { await downloadProjectFile(project.slug, file.id, file.filename); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos descargar el archivo."); }
  };
  const removeFolder = async () => {
    if (!project || !folderToDelete) return;
    setBusy(true);
    setError(null);
    try { await deleteProjectFolder(project.slug, folderToDelete.id); setFolderToDelete(null); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos eliminar la carpeta."); }
    finally { setBusy(false); }
  };
  /** Remember the destination before opening the picker: the browser gives no
   *  per-dialog context once the native file chooser returns. */
  const openUpload = (folderId: number | null) => {
    uploadFolder.current = folderId;
    fileInput.current?.click();
  };
  const removeFile = async () => {
    if (!project || !fileToDelete) return;
    setBusy(true);
    setError(null);
    try { await deleteProjectFile(project.slug, fileToDelete.id); setFileToDelete(null); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos eliminar el archivo."); }
    finally { setBusy(false); }
  };
  const onDrop = (event: React.DragEvent, folderId: number | null) => {
    event.preventDefault();
    event.stopPropagation();
    const file = event.dataTransfer.files?.[0];
    if (file) void upload(file, folderId);
  };
  const moveFile = async (fileId: number, folderId: number | null) => {
    if (!project) return;
    setError(null);
    try { await moveProjectFile(project.slug, fileId, folderId); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos mover el archivo."); }
  };
  /** A drop zone accepts two different things: OS files to upload and a tree
   *  file being dragged to a new folder. The payload type decides, never the
   *  presence of `files`, so a move never turns into an accidental copy. */
  const onDropZone = (event: React.DragEvent, folderId: number | null) => {
    const types = Array.from(event.dataTransfer.types);
    if (types.includes(PROJECT_FILE_MOVE_TYPE)) {
      event.preventDefault();
      event.stopPropagation();
      const fileId = Number(event.dataTransfer.getData(PROJECT_FILE_MOVE_TYPE));
      if (Number.isInteger(fileId) && fileId > 0) void moveFile(fileId, folderId);
      return;
    }
    onDrop(event, folderId);
  };
  const folderFileCount = (folderId: number): number => {
    const childIds = folders.filter((folder) => folder.parent_id === folderId).map((folder) => folder.id);
    return files.filter((file) => file.folder_id === folderId || childIds.some((childId) => file.folder_id === childId || folderContains(childId, file.folder_id))).length;
  };
  const folderContains = (ancestorId: number, folderId: number | null): boolean => {
    if (folderId === null) return false;
    const parent = folders.find((folder) => folder.id === folderId);
    return parent?.parent_id === ancestorId || (parent ? folderContains(ancestorId, parent.parent_id) : false);
  };
  const fileRow = (file: ProjectFile) => <li key={`file-${file.id}`} className="assistant-project-resources__file" draggable onDragStart={(event) => { event.dataTransfer.setData("application/x-lumat-project-file", JSON.stringify({ slug: project?.slug, fileId: file.id, filename: file.filename })); event.dataTransfer.setData(PROJECT_FILE_MOVE_TYPE, String(file.id)); event.dataTransfer.effectAllowed = "copyMove"; }}>
    <Icon icon={FileText} size="sm" />
    <span className="assistant-project-resources__file-name" title={file.filename}>{file.filename}</span>
    <Menu label={`Acciones de ${file.filename}`} trigger="icon" align="end" items={[{ value: "download", label: "Descargar", icon: Download }, { value: "delete", label: "Eliminar archivo", icon: Trash2, tone: "danger" }]} onSelect={(value) => { if (value === "delete") setFileToDelete(file); else void download(file); }} />
  </li>;
  const tree = (parentId: number | null): React.ReactNode => <ul className="assistant-project-resources__tree">{folders.filter((folder) => folder.parent_id === parentId).map((folder) => {
    const isOpen = open.has(folder.id);
    const folderCount = folderFileCount(folder.id);
    return <li key={`folder-${folder.id}`} className="assistant-project-resources__branch">
      <div className="assistant-project-resources__folder" onDragOver={(event) => event.preventDefault()} onDrop={(event) => onDropZone(event, folder.id)}>
        <button type="button" aria-expanded={isOpen} onClick={() => setOpen((value) => { const next = new Set(value); isOpen ? next.delete(folder.id) : next.add(folder.id); return next; })}>
          <Icon icon={isOpen ? ChevronDown : ChevronRight} size="sm" />
          <Icon icon={Folder} size="sm" />
          <span>{folder.name}</span>
          <Badge>{folderCount}</Badge>
        </button>
        <Menu label={`Acciones de carpeta ${folder.name}`} trigger="icon" align="end" items={[{ value: "upload", label: "Subir aquí", icon: Upload }, { value: "delete", label: "Eliminar carpeta", icon: Trash2, tone: "danger" }]} onSelect={(value) => { if (value === "upload") openUpload(folder.id); else setFolderToDelete(folder); }} />
      </div>
      {isOpen ? tree(folder.id) : null}
    </li>;
  })}{files.filter((file) => file.folder_id === parentId).map(fileRow)}</ul>;
  const fileCount = files.length + folders.length;
  const folderMenuAction = (value: string) => {
    if (value === "upload") openUpload(null);
    if (value === "folder") { setFolderName(""); setCreateFolderOpen(true); }
  };

  if (!project) return <div className="assistant-project-resources"><p>Selecciona un proyecto para ver sus recursos.</p></div>;
  if (loading) return <div className="assistant-project-resources"><StateMessage tone="info" role="status" spinner title="Cargando recursos del proyecto" /></div>;

  return <div className="assistant-project-resources">
    {error ? <StateMessage tone="danger" role="alert" title={error} /> : null}
    <section className="assistant-project-resources__card" aria-label="Archivos del proyecto" onDragOver={(event) => { if (Array.from(event.dataTransfer.types).includes("Files")) event.preventDefault(); }} onDrop={(event) => onDropZone(event, null)}>
      <header className="assistant-project-resources__card-header">
        <div className="assistant-project-resources__heading"><h3>Archivos</h3><Badge>{fileCount}</Badge></div>
        <div className="assistant-project-resources__actions">
          <Button variant="secondary" disabled={busy} onClick={() => openUpload(null)}><Icon icon={Upload} size="sm" />Subir archivo</Button>
          <Menu label="Acciones de archivos" trigger="icon" align="end" disabled={busy} items={[{ value: "upload", label: "Subir archivo", icon: Upload }, { value: "folder", label: "Crear carpeta", icon: FolderPlus }]} onSelect={folderMenuAction} />
        </div>
      </header>
      <p className="assistant-project-resources__subtitle">Documentos compartidos del proyecto</p>
      <input ref={fileInput} type="file" hidden aria-label="Archivo del proyecto" onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; void upload(file, uploadFolder.current); }} />
      <div className="assistant-project-resources__drop" onDragOver={(event) => event.preventDefault()} onDrop={(event) => onDropZone(event, null)}>
        {folders.length === 0 && files.length === 0 ? <p className="assistant-project-resources__empty">Sin archivos del proyecto.</p> : tree(null)}
      </div>
    </section>
    <section className="assistant-project-resources__card" aria-label="Conocimiento del proyecto">
      <header className="assistant-project-resources__card-header">
        <div className="assistant-project-resources__heading"><Icon icon={BookOpen} size="md" /><h3>Conocimiento</h3><Badge>{docs.length}</Badge><Icon icon={Lock} size="sm" /></div>
      </header>
      <p className="assistant-project-resources__subtitle">Información que el asistente puede consultar</p>
      {docs.length ? <div className="assistant-project-resources__readonly-row"><span>{pluralize(docs.length, "documento disponible", "documentos disponibles")}</span><span>Solo lectura</span></div> : null}
      <p className="assistant-project-resources__readonly-note">Configurado en Configuración.</p>      {docs.length ? docs.map((doc) => <div className="assistant-project-resources__doc" key={doc.id}><span>{doc.title}</span><small>{doc.format.toUpperCase()} · v{doc.active_version} · {doc.active ? "Activo" : "Deshabilitado"}</small></div>) : <p className="assistant-project-resources__empty">Sin documentos disponibles.</p>}
    </section>
    <section className="assistant-project-resources__card" aria-label="Habilidades">
      <header className="assistant-project-resources__card-header">
        <div className="assistant-project-resources__heading"><Icon icon={Sparkles} size="md" /><h3>Habilidades</h3><Badge>{skills.length}</Badge></div>
      </header>
      <p className="assistant-project-resources__subtitle">Skills disponibles · Solo lectura</p>
      {skills.map((skill) => <div className="assistant-project-resources__skill" key={skill.name}><Icon icon={Sparkles} size="sm" /><strong>{skill.name}</strong><Badge>Proyecto</Badge><small>{skill.description}</small></div>)}
      {skills.length === 0 ? <p className="assistant-project-resources__empty">Sin habilidades disponibles.</p> : null}
    </section>
    <Dialog open={createFolderOpen} onClose={() => setCreateFolderOpen(false)} title="Nueva carpeta" icon={FolderPlus} description="Crea una carpeta para organizar los archivos del proyecto.">
      <div className="assistant-project-resources__dialog-form">
        <Input label="Nombre de la carpeta" value={folderName} onChange={(event) => setFolderName(event.target.value)} disabled={busy} />
        <div className="assistant-project-resources__dialog-actions"><Button variant="secondary" disabled={busy} onClick={() => setCreateFolderOpen(false)}>Cancelar</Button><Button disabled={busy || !folderName.trim()} onClick={() => void createFolder()}>{busy ? "Creando…" : "Crear carpeta"}</Button></div>
      </div>
    </Dialog>
    <Dialog open={fileToDelete !== null} onClose={() => { if (!busy) setFileToDelete(null); }} title={fileToDelete ? `Eliminar archivo ${fileToDelete.filename}` : "Eliminar archivo"} icon={Trash2} description={fileToDelete ? `Se eliminará ${fileToDelete.filename} del proyecto.` : undefined}>
      <div className="assistant-project-resources__dialog-actions"><Button variant="secondary" disabled={busy} onClick={() => setFileToDelete(null)}>Cancelar</Button><Button variant="danger" disabled={busy} onClick={() => void removeFile()}>{busy ? "Eliminando…" : "Eliminar archivo"}</Button></div>
    </Dialog>
    <Dialog open={folderToDelete !== null} onClose={() => { if (!busy) setFolderToDelete(null); }} title={folderToDelete ? `Eliminar carpeta ${folderToDelete.name}` : "Eliminar carpeta"} icon={Trash2} description={folderToDelete ? `Se eliminará la carpeta ${folderToDelete.name} y su contenido.` : undefined}>
      <div className="assistant-project-resources__dialog-actions"><Button variant="secondary" disabled={busy} onClick={() => setFolderToDelete(null)}>Cancelar</Button><Button variant="danger" disabled={busy} onClick={() => void removeFolder()}>{busy ? "Eliminando…" : "Eliminar carpeta"}</Button></div>
    </Dialog>
  </div>;
}
