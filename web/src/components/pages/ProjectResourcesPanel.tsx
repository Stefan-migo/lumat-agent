import { useEffect, useRef, useState } from "react";
import { BookOpen, ChevronDown, ChevronRight, Download, FileText, Folder, FolderPlus, Trash2, Upload } from "lucide-react";
import { ApiError, createProjectFolder, deleteProjectFolder, downloadProjectFile, getThreadResources, listProjectFiles, listProjectFolders, refreshKbDocuments, uploadProjectFile } from "../../api";
import type { Doc, Project, ProjectFile, ProjectFolder, ThreadResourceSkill } from "../../types";

export function ProjectResourcesPanel({ project, threadId, expanded }: { project?: Project; threadId?: number; expanded: boolean }) {
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [folders, setFolders] = useState<ProjectFolder[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [skills, setSkills] = useState<ThreadResourceSkill[]>([]);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [folderName, setFolderName] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let live = true;
    setError(null);
    setFiles([]); setFolders([]); setDocs([]); setSkills([]);
    if (expanded && project) {
      void Promise.all([listProjectFiles(project.slug), listProjectFolders(project.slug), refreshKbDocuments(project.id)])
        .then(([f, d, k]) => { if (live) { setFiles(f.files); setFolders(d.folders); setDocs(k.docs.filter((doc) => doc.project_id === project.id)); } })
        .catch((reason: unknown) => { if (live) setError(reason instanceof ApiError ? reason.detail : "No pudimos cargar los recursos del proyecto."); });
    }
    if (expanded && threadId) void getThreadResources(threadId).then((result) => { if (live) setSkills(result.available.skills); }).catch((reason: unknown) => { if (live) setError(reason instanceof ApiError ? reason.detail : "No pudimos cargar las habilidades."); });
    return () => { live = false; };
  }, [expanded, project?.id, project?.slug, threadId]);

  const reloadTree = async () => {
    if (!project) return;
    const [f, d] = await Promise.all([listProjectFiles(project.slug), listProjectFolders(project.slug)]);
    setFiles(f.files); setFolders(d.folders);
  };
  const upload = async (file?: File, folderId?: number | null) => {
    if (!project || !file) return;
    setBusy(true); setError(null);
    try { await uploadProjectFile(project.slug, file, folderId); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos subir el archivo."); }
    finally { setBusy(false); }
  };
  const createFolder = async (parentId: number | null) => {
    if (!project || !folderName.trim()) return;
    setBusy(true); setError(null);
    try { await createProjectFolder(project.slug, { name: folderName.trim(), parent_id: parentId }); setFolderName(""); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos crear la carpeta."); }
    finally { setBusy(false); }
  };
  const download = async (file: ProjectFile) => {
    if (!project) return;
    try { await downloadProjectFile(project.slug, file.id, file.filename); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos descargar el archivo."); }
  };
  const removeFolder = async (folder: ProjectFolder) => {
    if (!project || !window.confirm(`¿Eliminar la carpeta ${folder.name}?`)) return;
    setError(null);
    try { await deleteProjectFolder(project.slug, folder.id); await reloadTree(); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos eliminar la carpeta."); }
  };
  const onDrop = (event: React.DragEvent, folderId: number | null) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) void upload(file, folderId);
  };
  const fileRow = (file: ProjectFile) => <li key={`file-${file.id}`} className="assistant-project-resources__file" draggable onDragStart={(event) => { event.dataTransfer.setData("application/x-lumat-project-file", JSON.stringify({ slug: project?.slug, fileId: file.id, filename: file.filename })); event.dataTransfer.effectAllowed = "copy"; }}><FileText size={15} /><span>{file.filename}</span><button type="button" aria-label={`Descargar ${file.filename}`} onClick={() => void download(file)}><Download size={14} /></button></li>;
  const tree = (parentId: number | null): React.ReactNode => <ul className="assistant-project-resources__tree">{folders.filter((folder) => folder.parent_id === parentId).map((folder) => {
    const expanded = open.has(folder.id);
    return <li key={folder.id}>
      <div className="assistant-project-resources__folder" onDragOver={(event) => event.preventDefault()} onDrop={(event) => onDrop(event, folder.id)}><button type="button" aria-expanded={expanded} onClick={() => setOpen((value) => { const next = new Set(value); expanded ? next.delete(folder.id) : next.add(folder.id); return next; })}><span aria-hidden="true">{expanded ? <ChevronDown /> : <ChevronRight />}</span><Folder size={15} />{folder.name}</button><button type="button" aria-label={`Eliminar carpeta ${folder.name}`} onClick={() => void removeFolder(folder)}><Trash2 size={14} /></button></div>
      {expanded ? <>{tree(folder.id)}{files.filter((file) => file.folder_id === folder.id).map(fileRow)}</> : null}
    </li>;
  })}{files.filter((file) => file.folder_id === parentId).map(fileRow)}</ul>;

  return <div className="assistant-project-resources">
    {!project ? <p>Selecciona un proyecto para ver sus recursos.</p> : <>
      <section aria-label="Archivos del proyecto"><h3>Archivos</h3>
        <div className="assistant-project-resources__actions"><button type="button" disabled={busy} onClick={() => fileInput.current?.click()}><Upload size={14} />Subir archivo</button><button type="button" disabled={busy || !folderName.trim()} onClick={() => void createFolder(null)}><FolderPlus size={14} />Crear carpeta</button></div>
        <input ref={fileInput} type="file" hidden aria-label="Archivo del proyecto" onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; void upload(file); }} />
        <div className="assistant-project-resources__drop" onDragOver={(event) => event.preventDefault()} onDrop={(event) => onDrop(event, null)}><Folder size={15} />{project.name}{tree(null)}</div>
      </section>
      <label className="assistant-project-resources__new-folder">Nueva carpeta<input value={folderName} onChange={(event) => setFolderName(event.target.value)} /></label>
      <section aria-label="Base de conocimientos"><h3><BookOpen size={15} /> Conocimiento del proyecto</h3><p>Solo lectura · Configurado en Configuración.</p>{docs.map((doc) => <div className="assistant-project-resources__doc" key={doc.id}><span>{doc.title}</span><small>{doc.format.toUpperCase()} · v{doc.active_version} · {doc.active ? "Activo" : "Deshabilitado"}</small></div>)}{docs.length === 0 ? <p>Sin documentos.</p> : null}</section>
    </>}
    <section aria-label="Habilidades"><h3>Habilidades</h3>{skills.map((skill) => <div className="assistant-project-resources__skill" key={skill.name}><strong>{skill.name}</strong><small>{skill.description}</small></div>)}{skills.length === 0 ? <p>Sin habilidades disponibles.</p> : null}</section>
    {error ? <p role="alert">{error}</p> : null}
  </div>;
}
