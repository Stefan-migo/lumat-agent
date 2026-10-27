import { useCallback, useEffect, useState } from "react";
import { Clock3 } from "lucide-react";
import { apiFetch, postJson } from "../../api";
import type { SettingsDiffResponse, SettingsVersionEntry, SettingsVersionsResponse } from "../../types";
import { Button } from "../primitives/Button";

export type SettingsVersionScope = "persona" | "emergency";

export interface SettingsVersionHistoryProps {
  scope: SettingsVersionScope;
  /** Called after a successful restore so the owner sees the restored text. */
  onRestored: () => void;
  /** Bumped by the parent after every save so an open history stays current. */
  refreshToken?: number;
  triggerLabel?: string;
}

type HistoryState = "idle" | "loading" | "ready" | "error";

function formatVersionDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" });
}

function diffLabel(diff: Record<string, string>): string {
  return Object.entries(diff)
    .map(([field, text]) => (text.trim() ? `${field}\n${text}` : `${field}: sin cambios`))
    .join("\n\n");
}

/** Version history of one editable scope (S12/S13): view a change, restore it. */
export function SettingsVersionHistory({ scope, onRestored, refreshToken = 0, triggerLabel = "Ver historial" }: SettingsVersionHistoryProps) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<HistoryState>("idle");
  const [versions, setVersions] = useState<SettingsVersionEntry[]>([]);
  const [diff, setDiff] = useState<{ version: number; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    try {
      const payload = await apiFetch<SettingsVersionsResponse>(`/panel/api/settings/versions/${scope}`);
      setVersions(payload.versions);
      setState("ready");
    } catch {
      setState("error");
    }
  }, [scope]);

  useEffect(() => {
    if (open) void load();
  }, [open, load, refreshToken]);

  const showDiff = async (version: number) => {
    if (diff?.version === version) {
      setDiff(null);
      return;
    }
    setError(null);
    try {
      const payload = await apiFetch<SettingsDiffResponse>(`/panel/api/settings/versions/${scope}/diff?from=${Math.max(version - 1, 0)}&to=${version}`);
      setDiff({ version, text: diffLabel(payload.diff) });
    } catch {
      setError("No pudimos cargar los cambios de esa versión.");
    }
  };

  const restore = async (version: number) => {
    setBusy(true);
    setError(null);
    try {
      await postJson(`/panel/api/settings/versions/${scope}/restore`, { version });
      setDiff(null);
      await load();
      onRestored();
    } catch {
      setError("No pudimos restaurar esa versión.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="settings-version-history">
      <Button variant="tertiary" onClick={() => setOpen((current) => !current)} aria-expanded={open}>
        {open ? "Ocultar historial" : <><Clock3 aria-hidden="true" />{triggerLabel}</>}
      </Button>
      {open ? (
        <div className="settings-version-history__body">
          {state === "loading" ? <p className="settings__footer-note">Cargando historial…</p> : null}
          {state === "error" ? <p className="settings__footer-note" role="alert">No pudimos cargar el historial.</p> : null}
          {state === "ready" && versions.length === 0 ? (
            <p className="settings__footer-note">Todavía no hay versiones guardadas: se usa el texto original.</p>
          ) : null}
          {state === "ready" && versions.length > 0 ? (
            <ol className="settings-version-history__list">
              {[...versions].reverse().map((entry) => (
                <li key={entry.version} className="settings-version-history__entry">
                  <div className="settings-version-history__meta">
                    <strong>Versión {entry.version}</strong>
                    <span>{formatVersionDate(entry.created_at)} · {entry.actor}</span>
                  </div>
                  <div className="settings-version-history__actions">
                    <Button variant="tertiary" onClick={() => void showDiff(entry.version)}>
                      {diff?.version === entry.version ? "Ocultar cambios" : "Ver cambios"}
                    </Button>
                    <Button variant="tertiary" disabled={busy} onClick={() => void restore(entry.version)}>Restaurar</Button>
                  </div>
                  {diff?.version === entry.version ? <pre className="settings-version-history__diff">{diff.text}</pre> : null}
                </li>
              ))}
            </ol>
          ) : null}
          <div className="settings-version-history__footer">
            <Button variant="tertiary" disabled={busy} onClick={() => void restore(0)}>Restaurar original</Button>
          </div>
          {error ? <p className="settings__footer-note" role="alert">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
