import { useEffect, useRef, useState } from "react";
import { BookOpen, ChevronDown, ChevronRight, Download, FileText, Folder, FolderPlus, Lock, Sparkles, Trash2, Upload } from "lucide-react";
import { ApiError, createProjectFolder, deleteProjectFolder, downloadProjectFile, getThreadResources, listProjectFiles, listProjectFolders, refreshKbDocuments, uploadProjectFile } from "../../api";
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
  const fileInput = useRef<HTMLInputElement>(null);
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
  const onDrop = (event: React.DragEvent, folderId: number | null) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) void upload(file, folderId);
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
  const fileRow = (file: ProjectFile) => <li key={`file-${file.id}`} className="assistant-project-resources__file" draggable onDragStart={(event) => { event.dataTransfer.setData("application/x-lumat-project-file", JSON.stringify({ slug: project?.slug, fileId: file.id, filename: file.filename })); event.dataTransfer.effectAllowed = "copy"; }}>
    <Icon icon={FileText} size="sm" />
    <span>{file.filename}</span>
    <Menu label={`Acciones de ${file.filename}`} trigger="icon" align="end" items={[{ value: "download", label: "Descargar", icon: Download }]} onSelect={() => void download(file)} />
  </li>;
  const tree = (parentId: number | null): React.ReactNode => <ul className="assistant-project-resources__tree">{folders.filter((folder) => folder.parent_id === parentId).map((folder) => {
    const isOpen = open.has(folder.id);
    const folderCount = folderFileCount(folder.id);
    return <li key={folder.id}>
      <div className="assistant-project-resources__folder" onDragOver={(event) => event.preventDefault()} onDrop={(event) => onDrop(event, folder.id)}>
        <button type="button" aria-expanded={isOpen} onClick={() => setOpen((value) => { const next = new Set(value); isOpen ? next.delete(folder.id) : next.add(folder.id); return next; })}>
          <Icon icon={isOpen ? ChevronDown : ChevronRight} size="sm" />
          <Icon icon={Folder} size="sm" />
          <span>{folder.name}</span>
          <Badge>{folderCount}</Badge>
        </button>
        <Menu label={`Acciones de carpeta ${folder.name}`} trigger="icon" align="end" items={[{ value: "delete", label: "Eliminar carpeta", icon: Trash2, tone: "danger" }]} onSelect={() => setFolderToDelete(folder)} />
      </div>
      {isOpen ? <>{tree(folder.id)}{files.filter((file) => file.folder_id === folder.id).map(fileRow)}</> : null}
    </li>;
  })}{files.filter((file) => file.folder_id === parentId).map(fileRow)}</ul>;
  const fileCount = files.length + folders.length;
  const folderMenuAction = (value: string) => {
    if (value === "upload") fileInput.current?.click();
    if (value === "folder") { setFolderName(""); setCreateFolderOpen(true); }
  };

  if (!project) return <div className="assistant-project-resources"><p>Selecciona un proyecto para ver sus recursos.</p></div>;
  if (loading) return <div className="assistant-project-resources"><StateMessage tone="info" role="status" spinner title="Cargando recursos del proyecto" /></div>;

  return <div className="assistant-project-resources">
    {error ? <StateMessage tone="danger" role="alert" title={error} /> : null}
    <section className="assistant-project-resources__card" aria-label="Archivos del proyecto">
      <header className="assistant-project-resources__card-header">
        <div className="assistant-project-resources__heading"><h3>Archivos</h3><Badge>{fileCount}</Badge></div>
        <div className="assistant-project-resources__actions">
          <Button variant="secondary" disabled={busy} onClick={() => fileInput.current?.click()}><Icon icon={Upload} size="sm" />Subir archivo</Button>
          <Menu label="Acciones de archivos" trigger="icon" align="end" disabled={busy} items={[{ value: "upload", label: "Subir archivo", icon: Upload }, { value: "folder", label: "Crear carpeta", icon: FolderPlus }]} onSelect={folderMenuAction} />
        </div>
      </header>
      <p className="assistant-project-resources__subtitle">Documentos compartidos del proyecto</p>
      <input ref={fileInput} type="file" hidden aria-label="Archivo del proyecto" onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; void upload(file); }} />
      <div className="assistant-project-resources__drop" onDragOver={(event) => event.preventDefault()} onDrop={(event) => onDrop(event, null)}>
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
    <Dialog open={folderToDelete !== null} onClose={() => { if (!busy) setFolderToDelete(null); }} title={folderToDelete ? `Eliminar carpeta ${folderToDelete.name}` : "Eliminar carpeta"} icon={Trash2} description={folderToDelete ? `Se eliminará la carpeta ${folderToDelete.name} y su contenido.` : undefined}>
      <div className="assistant-project-resources__dialog-actions"><Button variant="secondary" disabled={busy} onClick={() => setFolderToDelete(null)}>Cancelar</Button><Button variant="danger" disabled={busy} onClick={() => void removeFolder()}>{busy ? "Eliminando…" : "Eliminar carpeta"}</Button></div>
    </Dialog>
  </div>;
}
