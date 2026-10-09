import { useCallback, useState } from "react";
import { ApiError, listGlobalSkills, updateProjectConfig } from "../../api";
import type { GlobalSkill, ProjectSkill, Role } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";

export function ProjectSkills({ projectSlug, projectId, skills }: { projectSlug: string; projectId: number; role?: Role; skills: ProjectSkill[] }) {
  const load = useCallback(() => listGlobalSkills(), []);
  const catalog = useAsyncData(load, true);
  const [filter, setFilter] = useState("");
  const [items, setItems] = useState(skills);
  const [draft, setDraft] = useState<ProjectSkill>({ name: "", description: "", body: "" });
  const [editing, setEditing] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const query = filter.trim().toLocaleLowerCase("es-CL");
  const matches = (item: Pick<ProjectSkill, "name" | "description"> | GlobalSkill) => !query || `${item.name} ${item.description}`.toLocaleLowerCase("es-CL").includes(query);
  const persist = async (next: ProjectSkill[]) => {
    setSaving(true);
    setError(null);
    try {
      await updateProjectConfig(projectSlug, { skills: next });
      setItems(next);
      setDraft({ name: "", description: "", body: "" });
      setEditing(null);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos guardar las habilidades del proyecto.");
    } finally {
      setSaving(false);
    }
  };
  const save = () => {
    if (!draft.name.trim()) return;
    const next = editing === null ? [...items, draft] : items.map((item) => item.name === editing ? draft : item);
    void persist(next);
  };
  const startEdit = (item: ProjectSkill) => { setDraft({ ...item }); setEditing(item.name); };
  const visibleGlobal = (catalog.data?.skills ?? []).filter(matches);
  const visibleProject = items.filter(matches);
  return <div>
    <Input label="Filtrar habilidades" value={filter} onChange={(event) => setFilter(event.target.value)} />
    <Card title="Catálogo global">
      {catalog.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando catálogo global" /> : null}
      {catalog.state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el catálogo global" /><Button variant="secondary" onClick={catalog.retry}>Reintentar</Button></> : null}
      {catalog.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver el catálogo global." /> : null}
      {catalog.state === "ready" && visibleGlobal.length === 0 ? <EmptyState title={catalog.data?.skills.length ? "Sin coincidencias" : "Catálogo global vacío"} description={catalog.data?.skills.length ? "No hay habilidades que coincidan con el filtro." : "No hay habilidades globales disponibles."} /> : null}
      {catalog.state === "ready" ? visibleGlobal.map((skill) => <article key={skill.name}><h3>{skill.name}</h3><p>{skill.description}</p><span>Global · solo lectura</span></article>) : null}
    </Card>
    <Card title={`Habilidades del proyecto · ${projectId}`}>
      <p>Estas habilidades se guardan en la configuración del proyecto.</p>
      {visibleProject.length === 0 ? <EmptyState title={items.length ? "Sin coincidencias" : "Sin habilidades de proyecto"} description={items.length ? "No hay habilidades que coincidan con el filtro." : "Agrega la primera habilidad para este proyecto."} /> : visibleProject.map((item) => <article key={item.name}><h3>{item.name}</h3><p>{item.description}</p><pre>{item.body}</pre><Button variant="secondary" onClick={() => startEdit(item)}>Editar</Button><Button variant="secondary" disabled={saving} onClick={() => void persist(items.filter((entry) => entry.name !== item.name))}>Eliminar</Button></article>)}
      <h3>{editing === null ? "Agregar habilidad" : "Editar habilidad"}</h3>
      <Input label="Nombre de habilidad" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
      <Input label="Descripción de habilidad" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
      <Textarea label="Contenido de habilidad" value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} />
      <Button disabled={saving || !draft.name.trim()} onClick={save}>{saving ? "Guardando…" : "Guardar habilidad"}</Button>
      {editing !== null ? <Button variant="secondary" onClick={() => { setEditing(null); setDraft({ name: "", description: "", body: "" }); }}>Cancelar</Button> : null}
      {error ? <StateMessage tone="danger" role="alert" title="No se guardaron los cambios" detail={error} /> : null}
    </Card>
  </div>;
}
