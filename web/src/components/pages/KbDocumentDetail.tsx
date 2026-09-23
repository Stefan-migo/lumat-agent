import { useCallback, useEffect, useState } from "react";
import { ApiError, disableKbDocument, editKbDocument, getKbDocument, restoreKbDocument, setKbVisibility } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { KbDocument, KbVisibility } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { kbStatusLabel, kbStatusTone } from "../shared/toneMaps";

export interface KbDocumentDetailProps {
  documentId?: number;
  data?: KbDocument | null;
  state?: AsyncDataState;
  onRetry?: () => void;
}

function stateMessage(state: AsyncDataState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando documento" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este documento" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title="No pudimos cargar el documento" detail="Reintenta para recuperar los datos." />;
  return null;
}

type Mutation = "edit" | "disable" | "restore" | "visibility";
type Confirmation = { kind: "disable"; doc: KbDocument } | { kind: "restore"; doc: KbDocument; version: number };
type Feedback = { tone: "success" | "danger"; title: string };

const AUDIENCE_LABEL: Record<KbVisibility, string> = {
  customer: "Cliente y Lumat",
  internal: "Interno (solo Lumat)",
};
const AUDIENCE_OPTIONS = [
  { value: "internal", label: AUDIENCE_LABEL.internal },
  { value: "customer", label: AUDIENCE_LABEL.customer },
];
const DATE_FORMAT = new Intl.DateTimeFormat("es-CL", { dateStyle: "short" });

function safeMutationError(error: unknown) {
  if (error instanceof ApiError && (error.status === 400 || error.status === 422)) return "Revisa los campos e inténtalo nuevamente.";
  if (error instanceof ApiError && error.status === 403) return "No tienes permiso para modificar la base de conocimientos.";
  return "No pudimos guardar los cambios. Inténtalo nuevamente.";
}

export function KbDocumentDetail({ documentId, data: controlledData, state: controlledState, onRetry }: KbDocumentDetailProps) {
  const fetchDocument = useCallback(() => {
    if (documentId === undefined) throw new Error("document id is required");
    return getKbDocument(documentId);
  }, [documentId]);
  const fetched = useAsyncData(fetchDocument, documentId !== undefined && controlledData === undefined);
  const document = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const retry = onRetry ?? fetched.retry;
  const [refreshed, setRefreshed] = useState<KbDocument | null>(null);
  const [busy, setBusy] = useState<Mutation | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [contentState, setContentState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [visibility, setVisibility] = useState<KbVisibility>(document?.visibility ?? "internal");
  const [restoreVersion, setRestoreVersion] = useState(1);
  const current = refreshed ?? document;
  useEffect(() => {
    if (!current) return;
    setVisibility(current.visibility);
    setRestoreVersion(current.active_version);
  }, [current?.active_version, current?.id, current?.visibility]);

  const loadContent = async () => {
    if (!current) return;
    setContentState("loading");
    try {
      const fullDocument = await getKbDocument(current.id);
      setContent(fullDocument.content);
      setContentState("ready");
    } catch {
      setContentState("error");
    }
  };
  const refresh = async () => {
    if (!current) return;
    setRefreshed(await getKbDocument(current.id));
  };
  const mutate = async (action: Mutation, commit: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(action);
    setFeedback(null);
    try {
      await commit();
      await refresh();
      setFeedback({ tone: "success", title: "Cambios guardados" });
    } catch (error) {
      setFeedback({ tone: "danger", title: safeMutationError(error) });
    } finally {
      setBusy(null);
    }
  };

  if (!document) {
    return <PageFrame title="Documento de base de conocimientos" actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a documentos</Button>} state={stateMessage(state)}>{state === "error" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}</PageFrame>;
  }

  if (!current) return null;

  return <PageFrame title={current.title} actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a documentos</Button>} state={stateMessage(state)}>
    <div className="client-ficha">
      <section className="client-ficha__rail" aria-label="Identidad del documento">
        <Card title="Identidad">
          <dl className="client-ficha__facts">
            <div><dt>Título</dt><dd>{current.title}</dd></div>
            <div><dt>Formato</dt><dd>{current.format}</dd></div>
            <div><dt>Versión activa</dt><dd>v{current.active_version}</dd></div>
            <div><dt>Cantidad de versiones</dt><dd>{current.version}</dd></div>
            <div><dt>Estado</dt><dd><Badge tone={kbStatusTone(current.active ? "activo" : "deshabilitado")}>{kbStatusLabel(current.active ? "activo" : "deshabilitado")}</Badge></dd></div>
            <div><dt>Audiencia</dt><dd>{AUDIENCE_LABEL[current.visibility]}</dd></div>
            <div><dt>Proveedor</dt><dd>{current.provider ?? "—"}</dd></div>
            <div><dt>Modelo</dt><dd>{current.model ?? "—"}</dd></div>
            <div><dt>Costo</dt><dd>{current.cost_meta !== null ? `$${current.cost_meta.toFixed(6)}` : "—"}</dd></div>
            <div><dt>Creado</dt><dd>{current.created_at ? DATE_FORMAT.format(new Date(current.created_at)) : "—"}</dd></div>
          </dl>
        </Card>
      </section>

      <div className="client-ficha__main">
        {feedback ? <StateMessage tone={feedback.tone} role="alert" title={feedback.title} /> : null}
        <Card title="Operaciones">
          <details onToggle={(event) => { if (event.currentTarget.open && contentState === "idle") void loadContent(); }}>
            <summary className="disclosure__summary">Editar contenido</summary>
            <div className="kb-actions__edit-form">
              <Input label="Título" defaultValue={current.title} id={`kb-title-${current.id}`} />
              {contentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando contenido" /> : null}
              {contentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar el contenido" detail="Reintenta antes de guardar para evitar reemplazar el texto almacenado." /> : null}
              <Textarea label="Contenido" rows={5} value={content ?? ""} onChange={(event) => setContent(event.target.value)} disabled={contentState !== "ready" || busy !== null} id={`kb-content-${current.id}`} />
              <Button variant="secondary" disabled={busy !== null || contentState !== "ready"} onClick={() => void mutate("edit", () => editKbDocument(current.id, { title: (globalThis.document.getElementById(`kb-title-${current.id}`) as HTMLInputElement).value, content: content ?? "" }))}>Guardar (nueva versión)</Button>
            </div>
          </details>

          {current.active ? <Button variant="secondary" disabled={busy !== null} onClick={() => setConfirmation({ kind: "disable", doc: current })}>Deshabilitar</Button> : <p>Deshabilitado</p>}

          <div className="kb-actions__visibility">
            <Select label="Audiencia" value={visibility} options={AUDIENCE_OPTIONS} onChange={(event) => setVisibility(event.target.value as KbVisibility)} disabled={busy !== null} />
            <p>Un documento interno nunca se usa para responder a clientes.</p>
            <Button variant="secondary" disabled={busy !== null || visibility === current.visibility} onClick={() => void mutate("visibility", () => setKbVisibility(current.id, visibility))}>Cambiar audiencia</Button>
          </div>

          {current.version > 1 ? <div className="kb-actions__restore"><Select label="Restaurar" value={String(restoreVersion)} options={Array.from({ length: current.version }, (_, index) => ({ value: String(index + 1), label: `v${index + 1}` }))} size="sm" disabled={busy !== null} onChange={(event) => setRestoreVersion(Number(event.target.value))} /><Button variant="secondary" disabled={busy !== null} onClick={() => setConfirmation({ kind: "restore", doc: current, version: restoreVersion })}>Restaurar</Button></div> : null}
        </Card>

        {confirmation ? <><StateMessage tone="warning" role="alert" title={confirmation.kind === "restore" ? "Confirma la restauración" : "Confirma la desactivación"} detail={confirmation.kind === "restore" ? "El documento se reabrirá como Interno (solo Lumat). El asistente dejará de usarlo para responder a clientes hasta que lo marques como Cliente y Lumat nuevamente." : `Al deshabilitar «${confirmation.doc.title}», el agente dejará de responder con él. Puedes volver a activarlo cuando quieras.`} /><div className="kb-actions__confirmation"><Button disabled={busy !== null} onClick={() => { const pending = confirmation; setConfirmation(null); void mutate(pending.kind, () => pending.kind === "restore" ? restoreKbDocument(pending.doc.id, pending.version) : disableKbDocument(pending.doc.id)); }}>Confirmar</Button><Button variant="secondary" onClick={() => setConfirmation(null)}>Cancelar</Button></div></> : null}
      </div>
    </div>
  </PageFrame>;
}
