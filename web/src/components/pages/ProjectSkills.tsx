import { useCallback, useState } from "react";
import { ChevronDown, ChevronUp, FileText, Folder, Globe, Info, Lock, Pencil, Plus, Puzzle, Trash2 } from "lucide-react";
import { ApiError, listGlobalSkills, updateProjectConfig } from "../../api";
import type { GlobalSkill, ProjectSkill, Role } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { Markdown } from "../shared/Markdown";
import { StateMessage } from "../shared/StateMessage";

function SkillContent({ body }: { body: string | null }) {
  return <div className="project-skills__content">
    <div className="project-skills__content-head">
      <Icon icon={FileText} />
      <div className="project-skills__content-copy"><strong>Contenido de la habilidad</strong><span>Vista de lectura</span></div>
    </div>
    <div className="project-skills__content-body">
      {body?.trim() ? <Markdown content={body} /> : <p className="project-skills__content-empty">Esta habilidad no tiene contenido cargado.</p>}
    </div>
  </div>;
}

export function ProjectSkills({ projectSlug, skills }: { projectSlug: string; role?: Role; skills: ProjectSkill[] }) {
  const load = useCallback(() => listGlobalSkills(), []);
  const catalog = useAsyncData(load, true);
  const [filter, setFilter] = useState("");
  const [items, setItems] = useState(skills);
  const [draft, setDraft] = useState<ProjectSkill>({ name: "", description: "", body: "" });
  const [editing, setEditing] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const query = filter.trim().toLocaleLowerCase("es-CL");
  const matches = (name: string, description: string) => !query || `${name} ${description}`.toLocaleLowerCase("es-CL").includes(query);
  const persist = async (next: ProjectSkill[]) => {
    setSaving(true);
    setError(null);
    try {
      await updateProjectConfig(projectSlug, { skills: next });
      setItems(next);
      closeDialog();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos guardar las habilidades del proyecto.");
    } finally {
      setSaving(false);
    }
  };
  const toggleOpen = (key: string) => setOpen((previous) => {
    const next = new Set(previous);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });
  const openCreate = () => { setEditing(null); setDraft({ name: "", description: "", body: "" }); setError(null); setDialogOpen(true); };
  const startEdit = (item: ProjectSkill) => { setDraft({ ...item }); setEditing(item.name); setError(null); setDialogOpen(true); };
  const closeDialog = () => { setEditing(null); setDraft({ name: "", description: "", body: "" }); setError(null); setDialogOpen(false); };
  const save = () => {
    if (!draft.name.trim()) return;
    const next = editing === null ? [...items, draft] : items.map((item) => item.name === editing ? draft : item);
    void persist(next);
  };
  const globalSkills = catalog.data?.skills ?? [];
  const visibleGlobal = globalSkills.filter((skill) => matches(skill.name, skill.description));
  const visibleProject = items.filter((item) => matches(item.name, item.description));

  const renderGlobal = (skill: GlobalSkill) => {
    const key = `global:${skill.name}`;
    const isOpen = open.has(key);
    return <li className="project-skills__item" key={key}>
      <div className="project-skills__row">
        <button type="button" className="project-skills__summary" aria-expanded={isOpen} onClick={() => toggleOpen(key)}>
          <span className="project-skills__tile" aria-hidden="true"><Icon icon={Puzzle} /></span>
          <span className="project-skills__copy"><strong>{skill.name}</strong><span>{skill.description}</span></span>
          <span className="project-skills__meta">
            <Badge tone="neutral"><Icon icon={Globe} size="sm" /> Global</Badge>
            <Badge tone="neutral"><Icon icon={Lock} size="sm" /> Solo lectura</Badge>
            <Icon icon={isOpen ? ChevronUp : ChevronDown} size="sm" />
          </span>
        </button>
      </div>
      {isOpen ? <SkillContent body={skill.body} /> : null}
    </li>;
  };

  const renderProject = (item: ProjectSkill) => {
    const key = `project:${item.name}`;
    const isOpen = open.has(key);
    return <li className="project-skills__item" key={key}>
      <div className="project-skills__row">
        <button type="button" className="project-skills__summary" aria-expanded={isOpen} onClick={() => toggleOpen(key)}>
          <span className="project-skills__icon" aria-hidden="true"><Icon icon={Puzzle} /></span>
          <span className="project-skills__copy"><strong>{item.name}</strong><span>{item.description}</span></span>
          <span className="project-skills__meta">
            <Badge tone="neutral"><Icon icon={Folder} size="sm" /> Proyecto</Badge>
            <Icon icon={isOpen ? ChevronUp : ChevronDown} size="sm" />
          </span>
        </button>
        <Menu
          trigger="icon"
          label={`Acciones de ${item.name}`}
          align="end"
          items={[
            { value: "edit", label: "Editar", icon: Pencil },
            { value: "delete", label: "Eliminar", icon: Trash2, tone: "danger" },
          ]}
          onSelect={(value) => (value === "edit" ? startEdit(item) : void persist(items.filter((entry) => entry.name !== item.name)))}
        />
      </div>
      {isOpen ? <SkillContent body={item.body} /> : null}
    </li>;
  };

  return <div className="project-skills">
    <SearchInput aria-label="Buscar habilidad" placeholder="Buscar habilidad por nombre o descripción…" onSearch={setFilter} />

    <Card title="Catálogo global" description="Habilidades globales de solo lectura." headerAction={<Badge>{globalSkills.length}</Badge>}>
      {catalog.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando catálogo global" /> : null}
      {catalog.state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar el catálogo global" /><Button variant="secondary" onClick={catalog.retry}>Reintentar</Button></> : null}
      {catalog.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver el catálogo global." /> : null}
      {catalog.state === "ready" ? (visibleGlobal.length === 0
        ? <EmptyState title={globalSkills.length ? "Sin coincidencias" : "Catálogo global vacío"} description={globalSkills.length ? "No hay habilidades que coincidan con la búsqueda." : "No hay habilidades globales disponibles."} />
        : <ul className="project-skills__list">{visibleGlobal.map(renderGlobal)}</ul>) : null}
    </Card>

    <Card
      className="project-skills__project-card"
      title="Habilidades del proyecto"
      description="Se guardan en la configuración de este proyecto."
      headerAction={<><Badge>{items.length}</Badge><Button onClick={openCreate}><Icon icon={Plus} /> Agregar habilidad</Button></>}
    >
      {visibleProject.length === 0
        ? <EmptyState variant="dashed" icon={Puzzle} title={items.length ? "Sin coincidencias" : "Aún no hay habilidades en este proyecto"} description={items.length ? "No hay habilidades que coincidan con la búsqueda." : "Agrega una habilidad para definir instrucciones específicas."} />
        : <ul className="project-skills__list">{visibleProject.map(renderProject)}</ul>}
    </Card>

    <p className="projects-page__note"><Icon icon={Info} size="sm" />Las habilidades globales se consultan; las del proyecto se gestionan aquí.</p>

    <Dialog open={dialogOpen} onClose={closeDialog} title={editing === null ? "Agregar habilidad" : "Editar habilidad"} icon={Puzzle}>
      <div className="project-skills__dialog-body">
        <Input label="Nombre de habilidad" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        <Input label="Descripción de habilidad" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
        <Textarea label="Contenido de habilidad" value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} />
        {error ? <StateMessage tone="danger" role="alert" title="No se guardaron los cambios" detail={error} /> : null}
      </div>
      <div className="project-skills__dialog-actions">
        <Button variant="secondary" onClick={closeDialog}>Cancelar</Button>
        <Button disabled={saving || !draft.name.trim()} onClick={save}>{saving ? "Guardando…" : "Guardar habilidad"}</Button>
      </div>
    </Dialog>
  </div>;
}
