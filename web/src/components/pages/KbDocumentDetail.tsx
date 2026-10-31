import { useCallback, useEffect, useState } from "react";
import { Code2, FileText, Layers, LockKeyhole, Pause, Play, Trash2 } from "lucide-react";
import { ApiError, deleteKbDocument, disableKbDocument, editKbDocument, enableKbDocument, getKbDocument, restoreKbDocument, setKbVisibility } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { KbDocument, KbVisibility } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { Icon } from "../primitives/Icon";
import { Tabs } from "../primitives/Tabs";
import { useToast } from "../primitives/Toast";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { Markdown } from "../shared/Markdown";
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

type Mutation = "edit" | "disable" | "enable" | "restore" | "visibility" | "delete";
type Confirmation = { kind: "disable" | "delete"; doc: KbDocument } | { kind: "restore"; doc: KbDocument; version: number };
function docStatus(doc: KbDocument): "activo" | "deshabilitado" {
  return doc.active ? "activo" : "deshabilitado";
}

const AUDIENCE_LABEL: Record<KbVisibility, string> = {
  customer: "Cliente y Lumat",
  internal: "Interno (solo Lumat)",
};
const AUDIENCE_OPTIONS = [
  { value: "internal", label: AUDIENCE_LABEL.internal },
  { value: "customer", label: AUDIENCE_LABEL.customer },
];
const DATE_FORMAT = new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" });
const DETAIL_TABS = [{ id: "summary", label: "Resumen" }, { id: "content", label: "Contenido y versiones" }];

function safeMutationError(error: unknown) {
  if (error instanceof ApiError && (error.status === 400 || error.status === 422)) return "Revisa los campos e inténtalo nuevamente.";
  if (error instanceof ApiError && error.status === 403) return "No tienes permiso para modificar la base de conocimientos.";
  return "No pudimos guardar los cambios. Inténtalo nuevamente.";
}

export function KbDocumentDetail({ documentId, data: controlledData, state: controlledState, onRetry }: KbDocumentDetailProps) {
  const toast = useToast();
  const fetchDocument = useCallback(() => {
    if (documentId === undefined) throw new Error("document id is required");
    return getKbDocument(documentId);
  }, [documentId]);
  const fetched = useAsyncData(fetchDocument, documentId !== undefined && controlledData === undefined);
  const doc = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const retry = onRetry ?? fetched.retry;
  const [refreshed, setRefreshed] = useState<KbDocument | null>(null);
  const [busy, setBusy] = useState<Mutation | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [preview, setPreview] = useState(false);
  const [contentState, setContentState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [visibility, setVisibility] = useState<KbVisibility>(doc?.visibility ?? "internal");
  const [restoreVersion, setRestoreVersion] = useState(1);
  const [activeTab, setActiveTab] = useState("summary");
  const current = refreshed ?? doc;
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
    try {
      await commit();
      await refresh();
      toast.show("Cambios guardados");
    } catch (error) {
      toast.show(safeMutationError(error), "danger");
    } finally {
      setBusy(null);
    }
  };
  const removeDocument = async (target: KbDocument) => {
    if (busy) return;
    setBusy("delete");
    try {
      await deleteKbDocument(target.id);
      window.history.back();
    } catch (error) {
      toast.show(safeMutationError(error), "danger");
      setBusy(null);
    }
  };

  if (!doc) {
    return <PageFrame title="Documento de base de conocimientos" meta="Contenido y versiones del documento" actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a documentos</Button>} state={stateMessage(state)}>{state === "error" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}</PageFrame>;
  }

  if (!current) return null;

  const fileAdornment = <span className="kb-list__file"><Icon icon={FileText} size="lg" /></span>;
  const editContent = () => {
    setActiveTab("content");
    setPreview(false);
    if (contentState === "idle") void loadContent();
  };
  const editForm = <div className="kb-actions__edit-form">
    <Input label="Título" defaultValue={current.title} id={`kb-title-${current.id}`} />
    {contentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando contenido" /> : null}
    {contentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar el contenido" detail="Reintenta antes de guardar para evitar reemplazar el texto almacenado." /> : null}
    {contentState === "ready" ? <div className="kb-document__content-toggle" aria-label="Modo de contenido">
      <Button variant={preview ? "secondary" : "primary"} onClick={() => setPreview(false)}>Editar</Button>
      <Button variant={preview ? "primary" : "secondary"} onClick={() => setPreview(true)}>Vista previa</Button>
    </div> : null}
    {preview && contentState === "ready" ? <Markdown content={content ?? ""} className="kb-document__preview" /> : <Textarea label="Contenido" rows={5} value={content ?? ""} onChange={(event) => setContent(event.target.value)} disabled={contentState !== "ready" || busy !== null} id={`kb-content-${current.id}`} />}
    <Button variant="secondary" disabled={busy !== null || contentState !== "ready"} onClick={() => void mutate("edit", () => editKbDocument(current.id, { title: (document.getElementById(`kb-title-${current.id}`) as HTMLInputElement).value, content: content ?? "" }))}>Guardar (nueva versión)</Button>
  </div>;

  return <PageFrame title={current.title} titleAdornment={<>{fileAdornment}<Badge tone={kbStatusTone(docStatus(current))}>{kbStatusLabel(docStatus(current))}</Badge></>} meta={`#${current.id} · ${current.format.toUpperCase()} · Creado el ${current.created_at ? DATE_FORMAT.format(new Date(current.created_at)) : "—"}`} actions={<><Button onClick={editContent}>Editar contenido</Button><Button variant="danger" disabled={busy !== null} onClick={() => setConfirmation({ kind: "delete", doc: current })}><Icon icon={Trash2} />Eliminar</Button></>} state={stateMessage(state)}>
    <div className="detail-region__main">
      <Tabs tabs={DETAIL_TABS} activeTab={activeTab} ariaLabel="Secciones del documento" onTabChange={(tab) => { setActiveTab(tab); if (tab === "content" && contentState === "idle") void loadContent(); }}>
        {(tab) => tab === "summary" ? <div className="kb-document__layout" role="region" aria-label="Resumen del documento">
          <section className="kb-document__column" aria-label="Información y detalles técnicos">
            <Card title="Información del documento" icon={FileText}>
              <dl className="detail-region__facts">
                <div><dt>Título</dt><dd>{current.title}</dd></div>
                <div><dt>Formato</dt><dd><span className="kb-document__format"><Icon icon={FileText} size="sm" />{current.format.toUpperCase()}</span></dd></div>
                <div><dt>Creado</dt><dd>{current.created_at ? DATE_FORMAT.format(new Date(current.created_at)) : "—"}</dd></div>
                <div><dt>Cantidad de versiones</dt><dd>{current.version}</dd></div>
              </dl>
              <div className="kb-document__active-version"><Icon icon={Layers} size="lg" /><strong>Versión activa</strong><b>v{current.active_version}</b><Badge tone="success">En uso</Badge><button className="kb-document__versions-link" type="button" onClick={editContent}>Ver versiones →</button></div>
            </Card>
            <details className="card kb-document__technical" aria-label="Detalles técnicos" open>
              <summary><Icon icon={Code2} size="lg" /><h2>Detalles técnicos</h2></summary>
              <div className="kb-document__technical-fields">
                <Input label="Proveedor" value={current.provider ?? "—"} disabled />
                <Input label="Costo" value={current.cost_meta !== null ? `$${current.cost_meta.toFixed(6)}` : "—"} disabled />
                <Input label="Modelo" value={current.model ?? "—"} disabled />
              </div>
            </details>
          </section>
          <section className="kb-document__column" aria-label="Audiencia y disponibilidad">
            <Card title="Audiencia" icon={LockKeyhole} description="Define quién puede utilizar este documento.">
              <div className="kb-document__audience">
                <Select label="Audiencia del documento" value={visibility} options={AUDIENCE_OPTIONS} onChange={(event) => setVisibility(event.target.value as KbVisibility)} disabled={busy !== null} />
                <p className="kb-document__notice"><Icon icon={LockKeyhole} />Los documentos internos no se usan para responder a clientes.</p>
                <Button variant="secondary" disabled={busy !== null || visibility === current.visibility} onClick={() => void mutate("visibility", () => setKbVisibility(current.id, visibility))}>Guardar audiencia</Button>
              </div>
            </Card>
            <Card title="Disponibilidad" icon={FileText}>
              <div className="kb-document__availability">
                <div className="kb-document__availability-heading"><Badge tone={kbStatusTone(docStatus(current))}>{kbStatusLabel(docStatus(current))}</Badge></div>
                <p>{current.active ? "El documento está habilitado." : "El documento está deshabilitado."}</p>
                {current.active ? <Button variant="secondary" disabled={busy !== null} onClick={() => setConfirmation({ kind: "disable", doc: current })}><Icon icon={Pause} />Deshabilitar</Button> : <Button disabled={busy !== null} onClick={() => void mutate("enable", () => enableKbDocument(current.id))}><Icon icon={Play} />Habilitar</Button>}
              </div>
            </Card>
          </section>
        </div> : <div className="kb-document__content-panel">{editForm}<Card title="Versiones"><p>Versión activa: v{current.active_version} · {current.version} versiones disponibles.</p>{current.version > 1 ? <div className="kb-actions__restore"><Select label="Restaurar" value={String(restoreVersion)} options={Array.from({ length: current.version }, (_, index) => ({ value: String(index + 1), label: `v${index + 1}` }))} size="sm" disabled={busy !== null} onChange={(event) => setRestoreVersion(Number(event.target.value))} /><Button variant="secondary" disabled={busy !== null} onClick={() => setConfirmation({ kind: "restore", doc: current, version: restoreVersion })}>Restaurar</Button></div> : null}</Card></div>}
      </Tabs>
      {confirmation ? <><StateMessage tone="warning" role="alert" title={confirmation.kind === "restore" ? "Confirma la restauración" : confirmation.kind === "delete" ? "Confirma la eliminación permanente" : "Confirma la desactivación"} detail={confirmation.kind === "restore" ? "El documento se reabrirá como Interno (solo Lumat). El asistente dejará de usarlo para responder a clientes hasta que lo marques como Cliente y Lumat nuevamente." : confirmation.kind === "delete" ? `Esto elimina «${confirmation.doc.title}» de forma permanente. No se puede deshacer.` : `Al deshabilitar «${confirmation.doc.title}», el agente dejará de responder con él. Puedes volver a activarlo cuando quieras.`} /><div className="kb-actions__confirmation"><Button variant={confirmation.kind === "delete" ? "danger" : "primary"} disabled={busy !== null} onClick={() => { const pending = confirmation; setConfirmation(null); if (pending.kind === "delete") void removeDocument(pending.doc); else void mutate(pending.kind, () => pending.kind === "restore" ? restoreKbDocument(pending.doc.id, pending.version) : disableKbDocument(pending.doc.id)); }}>Confirmar</Button><Button variant="secondary" onClick={() => setConfirmation(null)}>Cancelar</Button></div></> : null}
    </div>
  </PageFrame>;
}
