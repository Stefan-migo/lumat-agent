import { useCallback, useEffect, useState, type FormEvent } from "react";
import { FileText, Folder } from "lucide-react";
import { ApiError, createProject, getProject, listProjects, updateProjectConfig } from "../../api";
import type { Project, ProjectCandidate, ProjectDetailResponse, ProjectsResponse, Role } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { DataTable } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { projectStatusLabel, projectStatusTone } from "../shared/toneMaps";
import { Tabs } from "../primitives/Tabs";
import { ProjectResources } from "./ProjectResources";
import { ProjectSkills } from "./ProjectSkills";
import { ProjectAgents } from "./ProjectAgents";
import { ProjectThreads } from "./ProjectThreads";
import "./ProjectsPage.css";

export function ProjectsPage({ projectSlug, onOpenProject, onOpenChat, onOpenThread, onOpenHistory, data, state, role, embedded = false }: { projectSlug?: string; onOpenProject?: (slug: string) => void; onOpenChat?: (slug: string) => void; onOpenThread?: (threadId: number, slug: string) => void; onOpenHistory?: (slug: string) => void; data?: ProjectsResponse; state?: AsyncDataState; role?: Role; embedded?: boolean }) {
  const [form, setForm] = useState({ slug: "", name: "", purpose: "" });
  const [createdProjects, setCreatedProjects] = useState<ProjectsResponse | null>(null);
  const [creationError, setCreationError] = useState<{ detail: string; candidates: ProjectCandidate[] } | null>(null);
  const [creating, setCreating] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [savingInstructions, setSavingInstructions] = useState(false);
  const [instructionsError, setInstructionsError] = useState<string | null>(null);
  const load = useCallback(() => listProjects(), []);
  const fetched = useAsyncData(load, data === undefined);
  const detailLoad = useCallback(() => getProject(projectSlug!), [projectSlug]);
  const detail = useAsyncData(detailLoad, projectSlug !== undefined);
  const body = detail.data as ProjectDetailResponse | null;
  useEffect(() => {
    setInstructions(body?.project.config?.instructions ?? "");
  }, [body?.project.slug, body?.project.config?.instructions]);
  const saveInstructions = async () => {
    setSavingInstructions(true);
    setInstructionsError(null);
    try {
      await updateProjectConfig(projectSlug!, { instructions });
    } catch (reason: unknown) {
      setInstructionsError(reason instanceof ApiError ? reason.detail : "No pudimos guardar las instrucciones.");
    } finally {
      setSavingInstructions(false);
    }
  };
  if (projectSlug) {
    const notFound = detail.state === "error" && detail.error instanceof ApiError && detail.error.status === 404;
    return <PageFrame className={embedded ? "projects-page--embedded" : undefined} title={body?.project.name ?? "Proyecto"} titleIcon={body ? Folder : undefined} titleAdornment={body ? <Badge tone={projectStatusTone(body.project.status)}>{projectStatusLabel(body.project.status)}</Badge> : null} subtitle={body ? body.project.purpose : "Detalle del proyecto"} actions={embedded ? null : <><Button variant="secondary" onClick={() => onOpenChat?.(body?.project.slug ?? projectSlug)}>Abrir asistente</Button><Button variant="secondary" onClick={() => window.history.back()}>Volver a proyectos</Button></>} state={detail.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyecto" /> : notFound ? <StateMessage tone="warning" role="alert" title="No encontramos este proyecto" detail="Revisa el enlace o vuelve a la lista de proyectos." /> : detail.state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el proyecto" detail="Intenta cargar el proyecto nuevamente más tarde." /><Button variant="secondary" onClick={detail.retry}>Reintentar</Button></> : undefined}>
      {body ? <Tabs ariaLabel="Secciones del proyecto" tabs={[{ id: "context", label: "Contexto" }, { id: "threads", label: "Hilos" }, { id: "agents", label: "Agentes" }, { id: "skills", label: "Skills" }]}>{(active) => {
        if (active === "threads") return <ProjectThreads projectSlug={body.project.slug} projectName={body.project.name} onOpenThread={onOpenThread} onOpenHistory={onOpenHistory} />;
        if (active === "agents") return <ProjectAgents projectSlug={body.project.slug} />;
        if (active === "skills") return <ProjectSkills projectSlug={body.project.slug} role={role} skills={body.project.config?.skills ?? []} />;
        return <div className="projects-page__context">
          <Card icon={FileText} title="Instrucciones del proyecto" description="Define el contexto compartido por el asistente." footer={<Button disabled={savingInstructions} onClick={() => void saveInstructions()}>{savingInstructions ? "Guardando…" : "Guardar cambios"}</Button>}>
            <Input label="Nombre del proyecto" value={body.project.name} disabled onChange={() => undefined} />
            <Textarea label="Propósito" value={body.project.purpose} disabled onChange={() => undefined} />
            <Textarea label="Instrucciones del proyecto" placeholder="Describe cómo debe trabajar el asistente en este proyecto…" value={instructions} onChange={(event) => setInstructions(event.target.value)} />
            <p className="projects-page__hint">Estas instrucciones forman parte del contexto del proyecto.</p>
            {instructionsError ? <p role="alert">No se guardaron los cambios: {instructionsError}</p> : null}
          </Card>
          <ProjectResources projectSlug={body.project.slug} projectId={body.project.id} projectName={body.project.name} role={role} />
        </div>;
      }}</Tabs> : null}
    </PageFrame>;
  }
  const projects = data ?? fetched.data;
  const currentState = state ?? (data ? "ready" : fetched.state);
  const create = async (event: FormEvent) => {
    event.preventDefault();
    setCreating(true);
    setCreationError(null);
    try {
      let created: Project;
      try {
        created = (await createProject(form)).project;
      } catch (reason: unknown) {
        const detail = reason instanceof ApiError ? reason.detail : "No pudimos crear el proyecto";
        const candidates = reason instanceof ApiError && Array.isArray(reason.structuredDetail?.candidates)
          ? reason.structuredDetail.candidates as ProjectCandidate[]
          : [];
        setCreationError({ detail, candidates });
        return;
      }
      setForm({ slug: "", name: "", purpose: "" });
      try {
        setCreatedProjects(await listProjects());
      } catch {
        // The refresh is best-effort: the project was created, so a list failure
        // must neither read as a creation error nor hide the new project.
        setCreatedProjects({ projects: [...(createdProjects ?? projects)?.projects ?? [], created] });
      }
    } finally {
      setCreating(false);
    }
  };
  const visibleProjects = createdProjects ?? projects;
  return <PageFrame title="Proyectos" meta={<span>Espacios de proyecto del asistente</span>} state={currentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyectos" /> : currentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los proyectos" /> : undefined}>
    <Card title="Crear proyecto">
      <form onSubmit={(event) => void create(event)}>
        <Input label="Slug" maxLength={100} required value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} />
        <Input label="Nombre" maxLength={200} required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <Textarea label="Propósito" maxLength={500} required value={form.purpose} onChange={(event) => setForm({ ...form, purpose: event.target.value })} />
        <Button type="submit" disabled={creating}>{creating ? "Creando…" : "Crear proyecto"}</Button>
        {creationError ? <section role="alert"><p>{creationError.detail}</p>{creationError.candidates.map((candidate) => <p key={candidate.slug}>{candidate.name} ({candidate.slug}) · {candidate.similarity}</p>)}</section> : null}
      </form>
    </Card>
    {!visibleProjects || visibleProjects.projects.length === 0 ? <EmptyState title="No hay proyectos" description="No hay espacios de proyecto registrados para mostrar." /> : <DataTable rows={visibleProjects.projects} rowKey={(project) => project.slug} columns={[{ key: "name", header: "Proyecto", render: (project) => <Button variant="tertiary" onClick={() => onOpenProject?.(project.slug)}>{project.name}</Button> }, { key: "purpose", header: "Propósito", render: (project) => project.purpose }, { key: "status", header: "Estado", render: (project) => <Badge tone={projectStatusTone(project.status)}>{projectStatusLabel(project.status)}</Badge> }]} />}
  </PageFrame>;
}
