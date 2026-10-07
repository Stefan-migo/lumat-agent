import { useCallback, useState, type FormEvent, type ReactNode } from "react";
import { ApiError, createProject, getProject, listProjects } from "../../api";
import type { Project, ProjectCandidate, ProjectDetailResponse, ProjectsResponse } from "../../types";
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

export function ProjectsPage({ projectSlug, onOpenProject, onOpenChat, data, state, sectionTabs }: { projectSlug?: string; onOpenProject?: (slug: string) => void; onOpenChat?: (slug: string) => void; data?: ProjectsResponse; state?: AsyncDataState; sectionTabs?: ReactNode }) {
  const [form, setForm] = useState({ slug: "", name: "", purpose: "" });
  const [createdProjects, setCreatedProjects] = useState<ProjectsResponse | null>(null);
  const [creationError, setCreationError] = useState<{ detail: string; candidates: ProjectCandidate[] } | null>(null);
  const [creating, setCreating] = useState(false);
  const load = useCallback(() => listProjects(), []);
  const fetched = useAsyncData(load, data === undefined);
  const detailLoad = useCallback(() => getProject(projectSlug!), [projectSlug]);
  const detail = useAsyncData(detailLoad, projectSlug !== undefined);
  if (projectSlug) {
    const body = detail.data as ProjectDetailResponse | null;
    return <PageFrame title={body?.project.name ?? "Proyecto"} meta={body ? `${body.project.purpose} · ${projectStatusLabel(body.project.status)}` : "Detalle del proyecto"} actions={<><Button variant="secondary" onClick={() => onOpenChat?.(body?.project.slug ?? projectSlug!)}>Abrir asistente</Button><Button variant="secondary" onClick={() => window.history.back()}>Volver a proyectos</Button></>} state={detail.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyecto" /> : detail.state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar el proyecto" /> : undefined}>
      {sectionTabs}
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
    {sectionTabs}
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
