import { useCallback } from "react";
import { apiFetch } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { Doc, DocsResponse } from "../../types";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Textarea } from "../primitives/Textarea";
import { DataTable, tabularNum, type Column } from "../shared/DataTable";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { kbStatusLabel } from "../shared/toneMaps";

export type KbListState = AsyncDataState | "processing" | "disable-confirmation";
export interface KbListProps { data?: DocsResponse | null; state?: KbListState; onRetry?: () => void; }

function docStatus(doc: Doc): "activo" | "deshabilitado" { return doc.active ? "activo" : "deshabilitado"; }

function DocActions({ doc }: { doc: Doc }) {
  return <div style={{ display: "grid", gap: "var(--space-2)" }}>
    <details>
      <summary style={{ cursor: "pointer" }}>Editar</summary>
      <div style={{ marginTop: "var(--space-2)", display: "grid", gap: "var(--space-2)" }}>
        <Input label="Título" defaultValue={doc.title} />
        <Textarea label="Contenido" rows={3} defaultValue={`Contenido de ${doc.title}…`} />
        <div style={{ display: "flex", gap: "var(--space-2)" }}><Button variant="secondary">Guardar (nueva versión)</Button></div>
        <div style={{ marginTop: "var(--space-2)", padding: "var(--space-3)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", background: "var(--surface)" }}>
          <p style={{ margin: 0, fontSize: "var(--text-sm)", fontWeight: "var(--weight-bold)" }}>Detalle técnico · proveedor y modelo</p>
          <p style={{ margin: "0 0 var(--space-2)", color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>Metadatos avanzados del motor que responde con este documento. No es necesario cambiarlos en el uso habitual.</p>
          <p style={{ margin: 0, fontSize: "var(--text-sm)" }}>Proveedor: <span style={{ fontVariantNumeric: "tabular-nums" }}>{doc.provider ?? "—"}</span>&nbsp;·&nbsp;Modelo: <span style={{ fontVariantNumeric: "tabular-nums" }}>{doc.model ?? "—"}</span></p>
        </div>
      </div>
    </details>
    {doc.active ? <Button variant="secondary">Deshabilitar</Button> : <span style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>Deshabilitado</span>}
    {doc.version > 1 ? <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}><Select label="Restaurar" aria-label={`Restaurar doc ${doc.id}`} defaultValue={String(doc.active_version)} options={Array.from({ length: doc.version }, (_, index) => ({ value: String(index + 1), label: `v${index + 1}` }))} size="sm" /><Button variant="secondary">Restaurar</Button></div> : null}
  </div>;
}

const columns: Column<Doc>[] = [
  { key: "id", header: "#", render: (doc) => `#${doc.id}` },
  { key: "title", header: "Título", render: (doc) => doc.title },
  { key: "format", header: "Formato", render: (doc) => doc.format },
  { key: "version", header: "Versión", render: (doc) => `${doc.version} (activa: ${doc.active_version})` },
  { key: "status", header: "Estado", render: (doc) => <Badge tone={doc.active ? "success" : "neutral"}>{kbStatusLabel(docStatus(doc))}</Badge> },
  { key: "cost", header: "Costo", render: (doc) => doc.cost_meta !== null ? tabularNum(`$${doc.cost_meta.toFixed(6)}`) : "—" },
];

function stateMessage(state: KbListState, storyError: boolean) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando base de conocimientos" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title={storyError ? "No pudimos procesar el documento" : "No pudimos cargar la base de conocimientos"} />;
  if (state === "processing") return <StateMessage tone="info" role="status" spinner title="Procesando documento" detail="Revisando el formato, tamaño y contenido. Verifica el estado en unos momentos." />;
  return null;
}

export function KbList({ data: controlledData, state: controlledState, onRetry }: KbListProps = {}) {
  const fetchDocs = useCallback(() => apiFetch<DocsResponse>("/panel/api/kb"), []);
  const fetched = useAsyncData(fetchDocs, controlledData === undefined);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const docs = data?.docs ?? [];
  void (onRetry ?? fetched.retry);
  return <PageFrame title="Base de conocimientos" meta={data ? `${docs.length} documentos` : undefined} state={stateMessage(state, controlledState === "error")}>
    {state === "processing" || state === "error" || state === "denied" || state === "loading" ? null : state === "empty" || (state === "ready" && data && docs.length === 0) ? <EmptyState title="No hay documentos" description="Subí el primer documento para empezar." /> : data ? <><Card title="Agregar documento"><div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end", flexWrap: "wrap" }}><Input label="Título" placeholder="Título del documento" /><Input label="Archivo (pdf / md / txt / csv)" type="file" /><Button>Agregar</Button></div></Card><DataTable columns={columns} rows={docs} rowKey={(doc) => String(doc.id)} actions={(doc) => <DocActions doc={doc} />} /></> : null}
    {controlledState === "disable-confirmation" ? <StateMessage tone="warning" role="alert" title="Confirma la desactivación" detail={`Al deshabilitar «${docs.find((doc) => doc.active)?.title ?? "este documento"}», el agente dejará de responder con él. Puedes volver a activarlo cuando quieras.`} /> : null}
  </PageFrame>;
}
