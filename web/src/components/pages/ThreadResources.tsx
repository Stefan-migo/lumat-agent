import { useCallback, useEffect, useState } from "react";
import { ApiError, getThreadResources, updateThreadResources } from "../../api";
import type { ThreadResourcesSelection } from "../../types";
import { useAsyncData } from "../../hooks/useAsyncData";
import { StateMessage } from "../shared/StateMessage";

type GroupKey = keyof ThreadResourcesSelection;

/** Pins project-level resources (files, planning sessions, skills) to a thread. */
export function ThreadProjectResources({ threadId, expanded }: { threadId?: number; expanded: boolean }) {
  const enabled = expanded && typeof threadId === "number";
  const fetchResources = useCallback(() => getThreadResources(threadId as number), [threadId]);
  const result = useAsyncData(fetchResources, enabled);
  const [selection, setSelection] = useState<ThreadResourcesSelection | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelection(result.data?.resources ?? null);
  }, [result.data]);

  const apply = async (next: ThreadResourcesSelection) => {
    if (typeof threadId !== "number") return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateThreadResources(threadId, next);
      setSelection(updated.resources);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos guardar los recursos.");
    } finally {
      setSaving(false);
    }
  };

  const toggle = (group: GroupKey, value: number | string) => {
    if (!selection || saving) return;
    const current = selection[group] as (number | string)[];
    const nextValues = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
    void apply({ ...selection, [group]: nextValues } as ThreadResourcesSelection);
  };

  if (!enabled) return null;
  if (result.state === "loading" && !result.data) return <StateMessage tone="info" role="status" spinner title="Cargando recursos" />;
  if (result.state === "error" || result.state === "denied") return <StateMessage tone="danger" role="alert" title="No pudimos cargar los recursos del proyecto" />;
  if (!selection || !result.data) return <div className="assistant-workspace__context-box">Sin información disponible.</div>;

  const available = result.data.available;
  const groups = [
    {
      key: "project_files" as const,
      title: "Archivos del proyecto",
      rows: available.project_files.map((file) => ({ value: file.id, label: file.filename })),
      empty: "Este proyecto no tiene archivos.",
    },
    {
      key: "planning_sessions" as const,
      title: "Sesiones de planning",
      rows: available.planning_sessions.map((session) => ({ value: session.slug, label: session.topic ?? session.slug })),
      empty: "Este proyecto no tiene sesiones de planning.",
    },
    {
      key: "skills" as const,
      title: "Habilidades",
      rows: available.skills.map((skill) => ({ value: skill.name, label: skill.name })),
      empty: "Este proyecto no tiene habilidades.",
    },
  ];

  return (
    <div className="assistant-workspace__resources">
      <p className="assistant-workspace__context-note">
        Los recursos fijados quedan disponibles para este hilo; el asistente los lee cuando los necesita.
      </p>
      {groups.map((group) => (
        <div className="assistant-workspace__resource-group" key={group.key}>
          <p className="assistant-workspace__resource-group-title">{group.title}</p>
          {group.rows.length === 0 ? (
            <p className="assistant-workspace__context-box assistant-workspace__context-box--empty">{group.empty}</p>
          ) : (
            <ul className="assistant-workspace__resource-list">
              {group.rows.map((row) => (
                <li key={String(row.value)}>
                  <label className="assistant-workspace__resource-row">
                    <input
                      type="checkbox"
                      aria-label={row.label}
                      checked={(selection[group.key] as (number | string)[]).includes(row.value)}
                      disabled={saving}
                      onChange={() => toggle(group.key, row.value)}
                    />
                    <span>{row.label}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      {error ? <p role="alert">{error}</p> : null}
    </div>
  );
}
