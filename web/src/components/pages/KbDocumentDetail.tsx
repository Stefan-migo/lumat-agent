import { useCallback } from "react";
import { getKbDocument } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { KbDocument } from "../../types";
import { Button } from "../primitives/Button";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

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

export function KbDocumentDetail({ documentId, data: controlledData, state: controlledState, onRetry }: KbDocumentDetailProps) {
  const fetchDocument = useCallback(() => {
    if (documentId === undefined) throw new Error("document id is required");
    return getKbDocument(documentId);
  }, [documentId]);
  const fetched = useAsyncData(fetchDocument, documentId !== undefined && controlledData === undefined);
  const document = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const retry = onRetry ?? fetched.retry;

  if (!document) {
    return <PageFrame title="Documento de base de conocimientos" actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a documentos</Button>} state={stateMessage(state)}>{state === "error" ? <Button variant="secondary" onClick={retry}>Reintentar</Button> : null}</PageFrame>;
  }

  return <PageFrame title={document.title} actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a documentos</Button>} state={stateMessage(state)}>{null}</PageFrame>;
}
