import { useEffect, useState, type ChangeEvent } from "react";
import { ApiError, approveChatPlan, closePlanningSession, createChatThread, getChatThread, listActiveConversations, listConversations, openPlanningSession, sendChatMessage, streamChatEvents, uploadAssistantAttachment } from "../../api";
import type { AssistantApproval, AssistantAttachment, AssistantCapabilities, AssistantEvidence, AssistantEvent, AssistantPlan, InternalChatMessage, InternalChatResponse, InternalChatThread, PlanningSession, CortexArtifact, CortexHandoff } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Textarea } from "../primitives/Textarea";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { realtimeClient, type ConnectionStatus } from "../../realtime";

export function PlanCard({ plan, approval, onApprove, onReject, busy = false }: { plan: AssistantPlan; approval?: AssistantApproval | null; onApprove?: () => void; onReject?: () => void; busy?: boolean }) {
  const pending = approval?.status === "pending" || plan.status === "pending";
  const statusLabel = { pending: "Pendiente", rejected: "Rechazado", consumed: "Aprobado", completed: "Completado" }[plan.status ?? ""] ?? plan.status ?? "Propuesto";
  return <Card title="Plan de acción" className="ai-agent-grammar__plan-card">
    <dl><dt>Herramienta</dt><dd>{plan.tool || "Respuesta del asistente"}</dd><dt>Argumentos</dt><dd><code>{JSON.stringify(plan.arguments ?? {})}</code></dd></dl>
    <Badge tone={pending ? "warning" : plan.status === "rejected" ? "danger" : "success"}>{statusLabel}</Badge>
    {pending && onApprove && onReject ? <div className="ai-agent-grammar__plan-actions">
      <Button onClick={onApprove} disabled={busy}>Aprobar</Button>
      <Button variant="secondary" onClick={onReject} disabled={busy}>Rechazar</Button>
    </div> : null}
  </Card>;
}

function EvidenceList({ evidence }: { evidence: AssistantEvidence[] }) {
  return <div aria-label="Evidencia de herramientas" className="ai-agent-grammar__evidence">
    {evidence.map((item, index) => <Card key={`${item.tool ?? "assistant"}-${index}`} title={item.tool || "Asistente"}>
      <Badge tone={item.status === "error" ? "danger" : item.status === "completed" ? "success" : "neutral"}>{item.status}</Badge>
      {item.detail ? <p>{item.detail}</p> : null}
      {item.result !== undefined ? <code>{JSON.stringify(item.result)}</code> : null}
    </Card>)}
  </div>;
}

export interface AgentChatProps { threadId?: number }

function planningCommand(value: string): { action: "open" | "close"; topic?: string } | null {
  const match = value.match(/^\/planning(?:\s+(.+))?$/);
  if (!match?.[1]) return match ? { action: "close" } : null;
  return match[1].trim().toLowerCase() === "close" ? { action: "close" } : { action: "open", topic: match[1].trim() };
}

export function AssistantCapabilitiesView({ capabilities }: { capabilities: AssistantCapabilities }) {
  return <Card title="Capacidades del asistente">
    <h3>Herramientas</h3>
    <ul>{capabilities.tools.map((tool) => <li key={tool.name}><strong>{tool.name}</strong>: {tool.description} <Badge tone={tool.read_only ? "neutral" : "warning"}>{tool.read_only ? "Solo lectura" : "Puede escribir"}</Badge></li>)}</ul>
    <h3>Configuración activa</h3>
    <p>Personas: {capabilities.personas.join(", ")}</p>
    <p>Prompts: {capabilities.prompts.join(", ")}</p>
    <p>{capabilities.kb_available ? "KB disponible" : "KB no disponible"} · {capabilities.memory_available ? "Memoria disponible" : "Memoria no disponible"}</p>
  </Card>;
}

export function AgentChat({ threadId, capabilities }: AgentChatProps & { capabilities?: AssistantCapabilities } = {}) {
  // The panel's stateful navigation has no router params; preserve a deep-link
  // seam through `?thread_id=` while allowing AppShell to pass an explicit id.
  const requestedThreadId = threadId ?? (Number(new URLSearchParams(globalThis.location.search).get("thread_id")) || undefined);
  const [thread, setThread] = useState<InternalChatThread | null>(null);
  const [messages, setMessages] = useState<InternalChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [stream, setStream] = useState("");
  const [plan, setPlan] = useState<AssistantPlan | null>(null);
  const [approval, setApproval] = useState<AssistantApproval | null>(null);
  const [evidence, setEvidence] = useState<AssistantEvidence[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<AssistantAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [cortex, setCortex] = useState<PlanningSession | null>(null);
  const [handoff, setHandoff] = useState<CortexHandoff | null>(null);
  const [report, setReport] = useState<CortexArtifact | null>(null);

  const handleEvent = (event: AssistantEvent) => {
    if (event.type === "plan") setPlan(event.plan ?? null);
    if (event.type === "approval") { setApproval(event.approval ?? null); setLifecycle(event.status ?? null); }
    if (event.type === "tool") setLifecycle(event.status ?? "executing");
    if (event.type === "evidence") setEvidence(event.evidence ?? []);
    if (event.type === "status") setLifecycle(event.status ?? null);
    if (event.type === "response") setStream(event.content ?? "");
    if (event.type === "error") setError(event.error ?? "El stream del asistente falló");
  };

  const openStream = async (id: number, run: string) => {
    setRunId(run);
    try { await streamChatEvents(id, run, handleEvent); } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "El stream del asistente falló"); }
    finally { setProcessing(false); }
  };

  const loadThread = (result: InternalChatResponse) => {
      const state = result.thread.assistant_state;
      setThread(result.thread);
      setMessages(result.messages);
      setPlan(result.thread.current_plan ?? null);
      setApproval(state?.approval ?? null);
      setEvidence((state?.events ?? []).flatMap((event) => event.evidence ?? []));
      setLifecycle(state?.stage ?? null);
       setRunId(result.thread.active_run_id ?? null);
       setAttachments(result.attachments ?? []);
       setCortex(state?.cortex_session ?? null);
      if (result.thread.active_run_id && state?.recoverable && state.stage !== "approval_pending" && state.stage !== "completed") {
        setProcessing(true);
        void openStream(result.thread.id, result.thread.active_run_id);
      }
  };

  const attach = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !thread) return;
    setUploading(true); setError(null);
    try { const result = await uploadAssistantAttachment(thread.id, file); setAttachments((current) => [...current, result.attachment]); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos subir el archivo"); }
    finally { setUploading(false); }
  };

  useEffect(() => {
    const request = requestedThreadId ? getChatThread(requestedThreadId) : createChatThread();
    void request.then(loadThread).catch((reason: unknown) => setError(reason instanceof ApiError ? reason.detail : "No pudimos abrir el chat")).finally(() => setLoading(false));
  }, [requestedThreadId]);

  useEffect(() => {
    if (!thread) return;
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.conversation_id !== thread.id) return;
      if (event.type === "token") {
        const token = typeof event.data === "string" ? event.data : String((event.data as { token?: unknown }).token ?? "");
        setStream((current) => current + token);
      }
      if (event.type === "message") {
        setStream("");
        setMessages((current) => [...current.filter((message) => message.id !== (event.data as InternalChatMessage).id), event.data as InternalChatMessage]);
      }
    });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    const unregisterRecovery = realtimeClient.registerRecovery(async () => {
      await Promise.all([getChatThread(thread.id), listConversations(), listActiveConversations()]);
      const current = await getChatThread(thread.id);
      setMessages(current.messages);
    });
    realtimeClient.connect();
    return () => { unsubscribe(); unsubscribeStatus(); unregisterRecovery(); };
  }, [thread]);

  const send = async () => {
    if (!thread || !content.trim() || processing) return;
    const submitted = content.trim();
    setContent("");
    const command = planningCommand(submitted);
    if (command) {
      setError(null);
      try {
        if (command.action === "open") {
          const result = await openPlanningSession(command.topic!, thread.id);
          setCortex(result.session);
        } else if (cortex?.slug) {
          const result = await closePlanningSession(cortex.slug);
          setCortex(result.session); setHandoff(result.handoff); setReport(result.report);
        }
      } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "Could not update planning session"); }
      setProcessing(false);
      return;
    }
    setProcessing(true);
    setError(null);
    setPlan(null); setApproval(null); setEvidence([]); setStream(""); setLifecycle("planning");
    try {
       const result = await sendChatMessage(thread.id, submitted, attachments.map((item) => item.id));
      setMessages((current) => [...current, result.message]);
      const run = result.message.assistant_metadata?.run_id;
      if (run) { setProcessing(true); void openStream(thread.id, run); }
      else setProcessing(false);
      if (result.message.status === "failed") setError("No se pudo procesar el mensaje");
      try {
        const current = await getChatThread(thread.id);
        setMessages(current.messages);
      } catch {
        // The submitted row remains visible when polling is temporarily unavailable.
      }
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No se pudo procesar el mensaje");
      setMessages((current) => [...current, { id: Date.now(), thread_id: thread.id, author: "admin", content: submitted, status: "failed", error: "temporary" }]);
    }
  };

  const closeSession = async () => {
    if (!cortex?.slug) return;
    setError(null);
    try { const result = await closePlanningSession(cortex.slug); setCortex(result.session); setHandoff(result.handoff); setReport(result.report); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "Could not close planning session"); }
  };

  const openSession = async () => {
    if (!thread) return;
    const topic = globalThis.prompt("Planning topic");
    if (!topic?.trim()) return;
    try { const result = await openPlanningSession(topic.trim(), thread.id); setCortex(result.session); setError(null); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "Could not open planning session"); }
  };

  const approvalAction = async (reject: boolean) => {
    if (!thread || !runId || !approval?.token) return;
    setProcessing(true); setError(null);
    try {
      const result = await approveChatPlan(thread.id, runId, approval.token, reject);
      setApproval({ ...approval, status: result.status });
      setPlan((current) => current ? { ...current, status: result.status } : current);
      setMessages((current) => [...current, result.message]);
      if (!reject) void openStream(thread.id, runId);
      else setProcessing(false);
    } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.detail : "No pudimos actualizar el plan"); setProcessing(false); }
  };

  const state = loading ? <StateMessage tone="info" role="status" spinner title="Cargando chat" /> : error ? <StateMessage tone="danger" role="alert" title={error} /> : null;
  const canRenderThread = !loading && thread !== null;
  const composerDisabled = loading || processing || thread === null;
   return <PageFrame title="Asistente Lumat" meta="Chat interno con el agente virtual." actions={<div><Button variant="secondary" onClick={() => void openSession()} disabled={composerDisabled || cortex?.status === "active"}>Open planning session</Button>{cortex?.status === "active" ? <Button onClick={() => void closeSession()}>Close session</Button> : null}</div>} state={state}>
      {cortex?.status === "active" ? <p role="status">Cortex planning active: {cortex.topic}</p> : cortex?.status === "closed" ? <p role="status">Cortex planning closed: {cortex.topic}</p> : null}
      {handoff?.status === "pending" ? <section role="status"><strong>Approved plan pending</strong><p>{report?.contenido ?? "The closing report is ready for approval."}</p></section> : null}
     {capabilities ? <AssistantCapabilitiesView capabilities={capabilities} /> : null}
     <div className="ai-agent-grammar__thread-area" aria-label="Mensajes del chat interno" aria-live="polite">
       {connection !== "connected" && <p role="status">Conexión en tiempo real: {connection === "reconnecting" ? "reconectando" : "desconectada"}.</p>}
      {canRenderThread && messages.length === 0 && !error ? <StateMessage tone="info" role="status" title="Chat interno vacío" detail="Escribe un mensaje para iniciar la conversación." /> : null}
        {canRenderThread && processing ? <StateMessage tone="info" role="status" title={lifecycle === "approval_pending" ? "Esperando aprobación" : "Procesando respuesta"} /> : null}
        {canRenderThread && plan ? <PlanCard plan={plan} approval={approval} busy={processing} onApprove={approval && (approval.status === "pending" || plan.status === "pending") ? () => void approvalAction(false) : undefined} onReject={approval && (approval.status === "pending" || plan.status === "pending") ? () => void approvalAction(true) : undefined} /> : null}
        {evidence.length > 0 ? <EvidenceList evidence={evidence} /> : null}
       {stream && <p role="status" aria-label="Respuesta del agente en curso">{stream}</p>}
      {canRenderThread ? messages.map((message) => {
        const author = message.author === "agent" ? "Agente Lumat" : "Administrador";
        const outbound = message.author === "admin";
        return <article key={message.id} className={`ai-agent-grammar__bubble-row${outbound ? " ai-agent-grammar__bubble-row--outbound" : ""}`} aria-label={`Mensaje de ${message.author === "agent" ? "agente" : "administrador"}`}>
          {!outbound ? <Avatar name={author} /> : null}
          <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
            <span className="ai-agent-grammar__message-meta">{author}</span>
            <p>{message.content}</p>
            {message.status === "failed" ? <Button variant="secondary" onClick={() => setContent(message.content)}>Reintentar</Button> : null}
          </div>
          {outbound ? <Avatar name={author} /> : null}
        </article>;
      }) : null}
    </div>
     <div className="ai-agent-grammar__composer" aria-label="Enviar mensaje al chat interno">
       <Textarea label="Mensaje" value={content} onChange={(event) => setContent(event.target.value)} disabled={composerDisabled} placeholder="Escribe tu mensaje al asistente..." />
       <label>Adjuntar archivo<input aria-label="Adjuntar archivo" type="file" accept="image/*,.pdf,.csv,.txt" onChange={(event) => void attach(event)} disabled={composerDisabled || uploading} /></label>
       {uploading ? <p role="status">Subiendo archivo...</p> : null}
       {attachments.length > 0 ? <ul aria-label="Archivos adjuntos">{attachments.map((item) => <li key={item.id}>{item.filename}</li>)}</ul> : null}
      <div className="ai-agent-grammar__composer-actions">
        <Button onClick={() => void send()} disabled={composerDisabled || !content.trim()}>Enviar</Button>
      </div>
    </div>
  </PageFrame>;
}
