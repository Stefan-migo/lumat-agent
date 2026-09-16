import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import {
  ApiError,
  approveChatPlan,
  closePlanningSession,
  createChatThread,
  deleteChatThread,
  getAssistantCapabilities,
  getChatThread,
  listChatThreads,
  openPlanningSession,
  renameChatThread,
  sendChatMessage,
  streamChatEvents,
  uploadAssistantAttachment,
} from "../../api";
import type {
  AssistantApproval,
  AssistantAttachment,
  AssistantEvidence,
  AssistantEvent,
  AssistantPlan,
  CortexArtifact,
  CortexHandoff,
  InternalChatMessage,
  InternalChatResponse,
  InternalChatThread,
  InternalChatThreadSummary,
  AssistantCapabilities,
  PlanningSession,
} from "../../types";
import { realtimeClient, type ConnectionStatus } from "../../realtime";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Dialog } from "../primitives/Dialog";
import { Popover } from "../primitives/Popover";
import { Textarea } from "../primitives/Textarea";
import { PageFrame } from "../shared/PageFrame";
import { Markdown } from "../shared/Markdown";
import { StateMessage } from "../shared/StateMessage";

/**
 * Inline SVG icons. The project ships no icon dependency on purpose, so these
 * follow the same convention as `PanelShell`/`Dashboard`: a tiny local helper
 * over a stroked 24x24 viewBox, `currentColor`, and `aria-hidden` (the
 * accessible name always lives on the button, never on the glyph).
 */
const icon = (children: ReactNode, size: number) => (
  <svg
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

function CopyIcon({ size = 16 }: { size?: number }) {
  return icon(
    <>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </>,
    size,
  );
}

function RetryIcon({ size = 16 }: { size?: number }) {
  return icon(
    <>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </>,
    size,
  );
}

function CheckIcon({ size = 16 }: { size?: number }) {
  return icon(<path d="M20 6 9 17l-5-5" />, size);
}

function PaperclipIcon({ size = 20 }: { size?: number }) {
  return icon(
    <path d="M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l8.57-8.57a4 4 0 1 1 5.66 5.66l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />,
    size,
  );
}

function SendIcon({ size = 18 }: { size?: number }) {
  // Points right on purpose: a 45° paper plane carries its visual mass at the
  // top-right tip and reads as off-centre inside a circle even when the
  // geometry is centred. A horizontally symmetric glyph centres cleanly.
  return icon(
    <>
      <path d="M3.5 3.5 21 12 3.5 20.5l3.2-8.5z" />
      <path d="M6.7 12H21" />
    </>,
    size,
  );
}

export const COMMAND_CENTER_BREAKPOINTS = {
  compactMax: 640,
  desktopMin: 1024,
} as const;

export type CommandCenterTier = "compact" | "tablet" | "desktop";

export function commandCenterTier(width: number): CommandCenterTier {
  if (width < COMMAND_CENTER_BREAKPOINTS.compactMax) return "compact";
  if (width < COMMAND_CENTER_BREAKPOINTS.desktopMin) return "tablet";
  return "desktop";
}

const stateLabels: Record<string, string> = {
  planning: "Preparando respuesta",
  executing: "Ejecutando herramienta",
  streaming: "Escribiendo respuesta",
  approval_pending: "Esperando aprobación",
  completed: "Completado",
  disconnected: "Desconectada",
  reconnecting: "Reconectando",
  connected: "Conectada",
};

/** Stage copy for the in-flight bubble, so a waiting turn never looks dead.
 *  Deliberately avoids the word "planificar": every turn runs the planner, and
 *  naming it that way collides with the opt-in Cortex planning session. */
const THINKING_LABELS: Record<string, string> = {
  planning: "Analizando tu solicitud…",
  executing: "Consultando herramientas…",
  streaming: "Redactando…",
  approval_pending: "Esperando aprobación…",
};

function relativeTime(value: string | null | undefined): string {
  if (!value) return "Sin fecha";
  const days = Math.floor((Date.now() - new Date(value).getTime()) / 86400000);
  if (days <= 0) return "Hoy";
  if (days < 7) return `Hace ${days} día${days === 1 ? "" : "s"}`;
  return new Intl.DateTimeFormat("es-CL", {
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}

function groupThreads(threads: InternalChatThreadSummary[]) {
  return threads.reduce<Record<string, InternalChatThreadSummary[]>>(
    (groups, item) => {
      const age = item.updated_at ?? item.created_at;
      const days = age
        ? Math.floor((Date.now() - new Date(age).getTime()) / 86400000)
        : 99;
      const key = days <= 0 ? "Hoy" : days < 7 ? "Últimos 7 días" : "Anteriores";
      (groups[key] ??= []).push(item);
      return groups;
    },
    {},
  );
}

function planningCommand(value: string) {
  const match = value.match(/^\/planning(?:\s+(.+))?$/);
  if (!match) return null;
  const topic = match[1]?.trim();
  return topic?.toLowerCase() === "close"
    ? { action: "close" as const }
    : { action: "open" as const, topic };
}

export function PlanCard({
  plan,
  approval,
  onApprove,
  onReject,
  busy = false,
}: {
  plan: AssistantPlan;
  approval?: AssistantApproval | null;
  onApprove?: () => void;
  onReject?: () => void;
  busy?: boolean;
}) {
  const pending = approval?.status === "pending" || plan.status === "pending";
  const label = {
    pending: "Pendiente",
    rejected: "Rechazado",
    consumed: "Aprobado",
    completed: "Completado",
  }[plan.status ?? ""] ?? "Propuesto";

  return (
    <Card title="Plan de acción" className="assistant-chat__plan-card">
      <dl>
        <dt>Herramienta</dt>
        <dd>{plan.tool || "Respuesta del asistente"}</dd>
        <dt>Argumentos</dt>
        <dd>
          <code>{JSON.stringify(plan.arguments ?? {})}</code>
        </dd>
      </dl>
      <Badge tone={pending ? "warning" : plan.status === "rejected" ? "danger" : "success"}>
        {label}
      </Badge>
      {pending && onApprove && onReject ? (
        <div className="assistant-chat__plan-actions">
          <Button onClick={onApprove} disabled={busy}>Aprobar</Button>
          <Button variant="secondary" onClick={onReject} disabled={busy}>Rechazar</Button>
        </div>
      ) : null}
    </Card>
  );
}

/**
 * One collapsed block per run holding the summarized action trail: what the
 * planner decided and which tools ran with what they returned. Renders nothing
 * when a turn was a plain answer with no tool work — a "plan" that plans
 * nothing is noise, not information.
 */
function AgentActivity({
  plan,
  evidence,
  includePlan = true,
}: {
  plan?: AssistantPlan | null;
  evidence: AssistantEvidence[];
  includePlan?: boolean;
}) {
  // Gate on a real tool: the backend's fallback plan carries the user's own
  // text as `summary`, so keying off the summary alone would render a
  // "Planificó <your message>" card for every plain answer.
  const planTool = plan?.tool?.trim() || "";
  const planDetail = includePlan && planTool ? plan?.summary?.trim() || planTool : "";
  const steps = (planDetail ? 1 : 0) + evidence.length;
  if (steps === 0) return null;

  return (
    <details className="assistant-chat__activity">
      <summary>
        Actividad del agente ({steps} {steps === 1 ? "paso" : "pasos"})
      </summary>
      <div className="assistant-chat__activity-body">
        {planDetail ? (
          <p className="assistant-chat__activity-step">
            <strong>Planificó</strong> {planDetail}
          </p>
        ) : null}
        {evidence.length > 0 ? (
          <>
            <p className="assistant-chat__activity-step">
              <strong>Evidencia de herramientas</strong>
            </p>
            {evidence.map((item, index) => (
              <div
                className="assistant-chat__evidence-item"
                key={`${item.tool ?? "asistente"}-${index}`}
              >
                <span>
                  {item.tool || "Asistente"}{" "}
                  <Badge
                    tone={
                      item.status === "error"
                        ? "danger"
                        : item.status === "completed"
                          ? "success"
                          : "neutral"
                    }
                  >
                    {stateLabels[item.status] ?? "En curso"}
                  </Badge>
                </span>
                {item.detail ? <p>{item.detail}</p> : null}
                {item.result !== undefined ? (
                  <code>{JSON.stringify(item.result)}</code>
                ) : null}
              </div>
            ))}
          </>
        ) : null}
      </div>
    </details>
  );
}

export interface AgentChatProps {
  threadId?: number;
  sectionTabs?: ReactNode;
}

export function AgentChat({ threadId, sectionTabs }: AgentChatProps = {}) {
  const requestedId =
    threadId ??
    (Number(new URLSearchParams(globalThis.location.search).get("thread_id")) || undefined);
  const [thread, setThread] = useState<InternalChatThread | null>(null);
  const [messages, setMessages] = useState<InternalChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [stream, setStream] = useState("");
  const [recoverable, setRecoverable] = useState(false);
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
  const [threads, setThreads] = useState<InternalChatThreadSummary[]>([]);
  const [navigatorError, setNavigatorError] = useState<string | null>(null);
  const [contextOpen, setContextOpen] = useState(false);
  const [capabilities, setCapabilities] = useState<AssistantCapabilities | null>(null);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(false);
  const [capabilitiesError, setCapabilitiesError] = useState(false);
  const capabilitiesRequested = useRef(false);
  const [planningOpen, setPlanningOpen] = useState(false);
  // Copy feedback: the icon that was just used swaps to a check and says so,
  // then reverts. Without it the click is silent and reads as a no-op.
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const copyTimer = useRef<number | null>(null);
  const [topic, setTopic] = useState("");
  const [topicError, setTopicError] = useState("");
  const [renameTarget, setRenameTarget] = useState<InternalChatThreadSummary | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<InternalChatThreadSummary | null>(null);
  const [renameTitle, setRenameTitle] = useState("");

  const loadThread = (result: InternalChatResponse, preserveArtifacts = false) => {
    const state = result.thread.assistant_state;
    setThread(result.thread);
    setMessages(result.messages ?? []);
    if (!preserveArtifacts) setPlan(result.thread.current_plan ?? null);
    setApproval(state?.approval ?? null);
    const persistedEvidence = (state?.events ?? []).flatMap((event) => event.evidence ?? []);
    if (!preserveArtifacts || persistedEvidence.length > 0) setEvidence(persistedEvidence);
    setLifecycle(state?.stage ?? null);
    setRunId(result.thread.active_run_id ?? null);
    setAttachments(result.attachments ?? []);
    setCortex(state?.cortex_session ?? null);
  };

  const refreshThreads = () =>
    listChatThreads(20)
      .then((result) => {
        setThreads(result.threads ?? []);
        setNavigatorError(null);
      })
      .catch((reason: unknown) =>
        setNavigatorError(
          reason instanceof ApiError ? reason.detail : "No pudimos cargar el historial",
        ),
      );

  useEffect(() => {
    const request = requestedId ? getChatThread(requestedId) : Promise.resolve(null);
    void request
      .then((result) => {
        if (result) loadThread(result);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof ApiError ? reason.detail : "No pudimos abrir el chat"),
      )
      .finally(() => setLoading(false));
    if (!requestedId) void refreshThreads();
  }, [requestedId]);

  useEffect(() => {
    if (!thread) return;
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.conversation_id !== thread.id) return;
      if (event.type === "token") {
        const token =
          typeof event.data === "string"
            ? event.data
            : String((event.data as { token?: unknown }).token ?? "");
        setStream((current) => current + token);
      }
      if (event.type === "message") {
        setStream("");
        setMessages((current) => [
          ...current.filter((item) => item.id !== (event.data as InternalChatMessage).id),
          event.data as InternalChatMessage,
        ]);
      }
    });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    realtimeClient.connect();
    return () => {
      unsubscribe();
      unsubscribeStatus();
    };
  }, [thread]);

  useEffect(() => {
    if (!contextOpen || capabilitiesRequested.current) return;
    capabilitiesRequested.current = true;
    setCapabilitiesLoading(true);
    void getAssistantCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilitiesError(true))
      .finally(() => setCapabilitiesLoading(false));
  }, [contextOpen]);

  const [settledStream, setSettledStream] = useState("");

  useEffect(() => {
    if (!stream) {
      setSettledStream("");
      return;
    }
    const timer = window.setTimeout(() => setSettledStream(stream), 200);
    return () => window.clearTimeout(timer);
  }, [stream]);

  const handleEvent = (event: AssistantEvent) => {
    if (event.type === "plan") setPlan(event.plan ?? null);
    if (event.type === "approval") {
      setApproval(event.approval ?? null);
      setLifecycle(event.status ?? null);
    }
    if (event.type === "tool" || event.type === "status") {
      setLifecycle(event.status ?? null);
    }
    if (event.type === "evidence") setEvidence(event.evidence ?? []);
    if (event.type === "response") setStream(event.content ?? "");
    if (event.type === "error") setError(event.error ?? "El stream del asistente falló");
  };

  const openStream = async (id: number, run: string) => {
    setRunId(run);
    try {
      await streamChatEvents(id, run, handleEvent);
      const persisted = await getChatThread(id);
       loadThread(persisted, true);
      setStream("");
      setRecoverable(false);
    } catch (reason: unknown) {
      setRecoverable(true);
      setError(
        reason instanceof ApiError
          ? `${reason.detail} La ejecución es recuperable.`
          : "El stream del asistente falló; la ejecución es recuperable.",
      );
    } finally {
      setProcessing(false);
    }
  };

  const selectThread = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      loadThread(await getChatThread(id));
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos abrir el chat");
    } finally {
      setLoading(false);
    }
  };

  const newChat = async () => {
    setError(null);
    setLoading(true);
    try {
      loadThread(await createChatThread());
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos crear el chat");
    } finally {
      setLoading(false);
    }
  };

  const resize = (element: HTMLTextAreaElement) => {
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
  };

  const closeSession = async () => {
    if (!cortex?.slug) return;
    try {
      const result = await closePlanningSession(cortex.slug);
      setCortex(result.session);
      setHandoff(result.handoff);
      setReport(result.report);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos cerrar la planificación");
    }
  };

  const send = async (value = content, preserveDraft = false) => {
    if (!thread || !value.trim() || processing) return;
    const submitted = value.trim();
    if (!preserveDraft) setContent("");
    setProcessing(true);
    setError(null);
    const command = planningCommand(submitted);
    if (command) {
      try {
        if (command.action === "open" && command.topic) {
          const result = await openPlanningSession(command.topic, thread.id);
          setCortex(result.session);
        } else if (command.action === "close") {
          await closeSession();
        }
      } catch (reason: unknown) {
        setError(reason instanceof ApiError ? reason.detail : "No pudimos actualizar la planificación");
      } finally {
        setProcessing(false);
      }
      return;
    }
    setLifecycle("planning");
    setPlan(null);
    setApproval(null);
    setEvidence([]);
    // The run is scheduled after the POST, so show the message immediately and
    // reconcile it with the persisted row when it lands. Negative ids never
    // collide with server ids.
    const optimisticId = -Date.now();
    setMessages((current) => [
      ...current,
      {
        id: optimisticId,
        thread_id: thread.id,
        author: "admin",
        content: submitted,
        status: "processing",
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const result = await sendChatMessage(
        thread.id,
        submitted,
        attachments.map((item) => item.id),
      );
      setMessages((current) => [
        ...current.filter((item) => item.id !== optimisticId),
        result.message,
      ]);
      const run = result.message.assistant_metadata?.run_id;
      if (run) {
        void openStream(thread.id, run);
      } else if (result.message.status !== "failed") {
        setProcessing(false);
        loadThread(await getChatThread(thread.id));
      } else {
        setProcessing(false);
      }
      if (result.message.status === "failed") {
        setError("No se pudo procesar el mensaje");
      }
    } catch (reason: unknown) {
      setProcessing(false);
      setError(reason instanceof ApiError ? reason.detail : "No pudimos enviar el mensaje");
      setMessages((current) => [
        ...current.filter((item) => item.id !== optimisticId),
        {
          id: Date.now(),
          thread_id: thread.id,
          author: "admin",
          content: submitted,
          status: "failed",
          error: "temporary",
          created_at: new Date().toISOString(),
        },
      ]);
    }
  };

  const copyMessage = (message: InternalChatMessage) => {
    void navigator.clipboard?.writeText(message.content);
    setCopiedId(message.id);
    if (copyTimer.current !== null) window.clearTimeout(copyTimer.current);
    copyTimer.current = window.setTimeout(() => setCopiedId(null), 1600);
  };

  useEffect(() => () => {
    if (copyTimer.current !== null) window.clearTimeout(copyTimer.current);
  }, []);

  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    } else if (event.key === "Enter" && event.shiftKey) {
      event.preventDefault();
      const start = event.currentTarget.selectionStart;
      const end = event.currentTarget.selectionEnd;
      setContent((value) => `${value.slice(0, start)}\n${value.slice(end)}`);
    }
  };

  const attach = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !thread) return;
    setUploading(true);
    try {
      const result = await uploadAssistantAttachment(thread.id, file);
      setAttachments((current) => [...current, result.attachment]);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos subir el archivo");
    } finally {
      setUploading(false);
    }
  };

  const planning = async () => {
    const trimmed = topic.trim();
    if (!trimmed) {
      setTopicError("Ingresa un tema para continuar.");
      return;
    }
    if (!thread) return;
    try {
      const result = await openPlanningSession(trimmed, thread.id);
      setCortex(result.session);
      setPlanningOpen(false);
      setTopic("");
      setTopicError("");
    } catch (reason: unknown) {
      setTopicError(reason instanceof ApiError ? reason.detail : "No pudimos iniciar la planificación");
    }
  };

  const approve = async (reject: boolean) => {
    if (!thread || !runId || !approval?.token) return;
    setProcessing(true);
    try {
      const result = await approveChatPlan(thread.id, runId, approval.token, reject);
      setApproval({ ...approval, status: result.status });
      setPlan((current) => (current ? { ...current, status: result.status } : current));
      setMessages((current) => [...current, result.message]);
      if (!reject) void openStream(thread.id, runId);
      else setProcessing(false);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos actualizar el plan");
      setProcessing(false);
    }
  };

  const rename = async () => {
    if (!renameTarget) return;
    const title = renameTitle.trim();
    if (!title) return;
    await renameChatThread(renameTarget.id, title);
    setRenameTarget(null);
    setRenameTitle("");
    await refreshThreads();
  };

  const remove = async () => {
    if (!deleteTarget) return;
    await deleteChatThread(deleteTarget.id);
    setThreads((current) => current.filter((item) => item.id !== deleteTarget.id));
    if (thread?.id === deleteTarget.id) {
      setThread(null);
      setMessages([]);
    }
    setDeleteTarget(null);
  };

  const groups = groupThreads(threads);
  const state = loading ? (
    <StateMessage tone="info" role="status" spinner title="Cargando chat" />
  ) : error ? (
    <StateMessage tone="danger" role="alert" title={error} />
  ) : null;

  // The backend stamps the same `run_id` on the message that STARTED a run and
  // on the agent's reply, so filtering events by run_id alone matched BOTH and
  // the plan card rendered twice per turn. A run's artifacts render exactly
  // once: on the agent's reply when one exists, otherwise on the message that
  // owns the run — the approval-pending case has no reply yet, and that message
  // is the only place the Aprobar/Rechazar actions can live.
  const runsWithReply = new Set(
    messages
      .filter((item) => item.author === "agent" && item.assistant_metadata?.run_id)
      .map((item) => item.assistant_metadata?.run_id as string),
  );

  return (
    <PageFrame
      title="Asistente Lumat"
      meta="Chat interno con el agente virtual."
      state={state}
      className="assistant-chat"
      actions={
        <div className="assistant-chat__header-actions">
          <Popover title="Historial" triggerLabel="Historial">
            <div className="assistant-chat__navigator">
              {navigatorError ? (
                <StateMessage
                  tone="danger"
                  role="alert"
                  title="No pudimos cargar el historial"
                  detail={navigatorError}
                />
              ) : null}
              {Object.entries(groups).map(([label, items]) => (
                <section key={label}>
                  <h3>{label}</h3>
                  {items.map((item) => (
                    <div className="assistant-chat__navigator-row" key={item.id}>
                      <button
                        type="button"
                        onClick={() => void selectThread(item.id)}
                        aria-current={thread?.id === item.id ? "page" : undefined}
                      >
                        <strong>{item.title || "Sin título"}</strong>
                        <small>{relativeTime(item.updated_at ?? item.created_at)}</small>
                      </button>
                      <span aria-label={thread?.id === item.id ? "Conversación activa" : undefined}>
                        {thread?.id === item.id ? "●" : ""}
                      </span>
                      <button
                        type="button"
                        aria-label={`Renombrar ${item.title || "conversación"}`}
                        onClick={() => {
                          setRenameTarget(item);
                          setRenameTitle(item.title ?? "");
                        }}
                      >
                        Renombrar
                      </button>
                      <button
                        type="button"
                        aria-label={`Eliminar ${item.title || "conversación"}`}
                        onClick={() => setDeleteTarget(item)}
                      >
                        Eliminar
                      </button>
                    </div>
                  ))}
                </section>
              ))}
            </div>
          </Popover>
          <Button variant="secondary" onClick={() => setContextOpen(true)}>Contexto</Button>
          <Button variant="secondary" onClick={() => setPlanningOpen(true)} disabled={!thread}>
            Planificar
          </Button>
          <Button onClick={() => void newChat()}>Nuevo chat</Button>
        </div>
      }
    >
      {sectionTabs}
      <Dialog
        open={planningOpen}
        onClose={() => {
          setPlanningOpen(false);
          setTopicError("");
        }}
        title="Tema de planificación"
      >
        <div className="assistant-chat__planning-form">
          <label htmlFor="planning-topic">Tema de planificación</label>
          <input
            id="planning-topic"
            autoFocus
            required
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            aria-invalid={topicError ? true : undefined}
          />
          {topicError ? <p role="alert">{topicError}</p> : null}
          <div>
            <Button variant="secondary" onClick={() => setPlanningOpen(false)}>Cancelar</Button>
            <Button onClick={() => void planning()}>Iniciar planificación</Button>
          </div>
        </div>
      </Dialog>
      <Dialog
        open={renameTarget !== null}
        onClose={() => setRenameTarget(null)}
        title="Renombrar conversación"
      >
        <div className="assistant-chat__planning-form">
          <label htmlFor="rename-title">Nuevo nombre de la conversación</label>
          <input
            id="rename-title"
            autoFocus
            value={renameTitle}
            onChange={(event) => setRenameTitle(event.target.value)}
          />
          <div>
            <Button variant="secondary" onClick={() => setRenameTarget(null)}>Cancelar</Button>
            <Button onClick={() => void rename()}>Guardar nombre</Button>
          </div>
        </div>
      </Dialog>
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar conversación"
      >
        <div className="assistant-chat__planning-form">
          <p>
            ¿Eliminar la conversación “{deleteTarget?.title || "Sin título"}”? Esta acción no se puede deshacer.
          </p>
          <div>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancelar</Button>
            <Button onClick={() => void remove()}>Eliminar conversación</Button>
          </div>
        </div>
      </Dialog>
      {contextOpen ? (
        <aside className="assistant-chat__context" role="complementary" aria-label="Contexto">
          <div>
            <h2>Contexto operativo</h2>
            <Button variant="secondary" onClick={() => setContextOpen(false)}>Cerrar</Button>
          </div>
          <p>Solo lectura. La aprobación se realiza en el flujo de conversación.</p>
          {capabilitiesLoading ? <p role="status">Cargando capacidades…</p> : null}
          {capabilitiesError ? (
            <p role="alert">No pudimos cargar las capacidades del asistente.</p>
          ) : null}
          {capabilities ? (
            <>
              <p>Herramientas disponibles: {capabilities.tools.length}</p>
              <p>
                Base de conocimientos: {capabilities.kb_available ? "Disponible" : "No disponible"}
              </p>
              <p>Memoria: {capabilities.memory_available ? "Disponible" : "No disponible"}</p>
              <p>
                Persona activa: {capabilities.personas.map((persona) => (
                  persona === "personas/assistant.md" ? "Asistente Lumat" : persona
                )).join(", ") || "No configurada"}
              </p>
            </>
          ) : null}
          {lifecycle ? (
            <p role="status">Ejecución: {stateLabels[lifecycle] ?? "En curso"}</p>
          ) : null}
        </aside>
      ) : null}
      <div className="assistant-chat__surface" data-tier={commandCenterTier(globalThis.innerWidth || 1024)}>
        <section className="assistant-chat__conversation" aria-label="Conversación">
          <div className="assistant-chat__messages" aria-live="polite">
            {!thread && !loading ? (
              <div className="assistant-chat__hero">
                <h2>Comienza una conversación</h2>
                <p>Escribe una consulta al asistente para iniciar un chat.</p>
              </div>
            ) : null}
            {thread && messages.length === 0 && !loading ? (
              <div className="assistant-chat__hero">
                <h2>¿En qué podemos ayudarte?</h2>
                <p>Describe una tarea o consulta para comenzar.</p>
              </div>
            ) : null}
            {messages.map((message) => {
              const outbound = message.author === "admin";
              const messageRunId = message.assistant_metadata?.run_id;
              // Outbound messages only render the run's artifacts when no agent
              // reply exists for that run (see `runsWithReply` above).
              const rendersRun =
                messageRunId !== undefined &&
                (outbound ? !runsWithReply.has(messageRunId) : true);
              const runEvents = rendersRun
                ? (thread?.assistant_state?.events ?? []).filter(
                    (event) => event.run_id === messageRunId,
                  )
                : [];
              const messagePlan = rendersRun
                ? runEvents.reduce<AssistantPlan | null>(
                    (current, event) => event.plan ?? current,
                    messageRunId === runId ? plan : null,
                  )
                : null;
              const messageEvidence =
                rendersRun && runEvents.length > 0
                  ? runEvents.flatMap((event) => event.evidence ?? [])
                  : rendersRun && messageRunId === runId
                    ? evidence
                    : [];
              const ownsLiveApproval =
                rendersRun &&
                messageRunId === runId &&
                Boolean(
                  approval &&
                    (approval.status === "pending" || messagePlan?.status === "pending"),
                );
              // A pending approval needs its Aprobar/Rechazar buttons, and a
              // rejected plan is a terminal outcome the operator must still be
              // able to read back. Every other turn is a plain answer whose
              // trail belongs in the collapsed activity block, not in a card.
              const showsPlanCard =
                messagePlan !== null &&
                (ownsLiveApproval || messagePlan.status === "rejected");
              return (
                <article
                  key={message.id}
                  className={`ai-agent-grammar__bubble-row${outbound ? " ai-agent-grammar__bubble-row--outbound" : ""}`}
                  aria-label={`Mensaje de ${outbound ? "administrador" : "agente"}`}
                >
                  <Avatar name={outbound ? "Administrador" : "Agente Lumat"} />
                  <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
                    <span className="ai-agent-grammar__message-meta">
                      {outbound ? "Administrador" : "Agente Lumat"}
                    </span>
                    {outbound ? (
                      <p className="assistant-chat__message-content">{message.content}</p>
                    ) : (
                      <Markdown
                        className="assistant-chat__message-content"
                        content={message.content}
                      />
                    )}
                    {message.status === "failed" ? (
                      <p className="assistant-chat__message-error" role="alert">
                        No se pudo procesar el mensaje
                      </p>
                    ) : null}
                    <time
                      className="ai-agent-grammar__message-time"
                      dateTime={message.created_at ?? undefined}
                    >
                      {message.created_at
                        ? new Intl.DateTimeFormat("es-CL", {
                            dateStyle: "short",
                            timeStyle: "short",
                          }).format(new Date(message.created_at))
                        : "Ahora"}
                    </time>
                    <div className="assistant-chat__message-actions">
                      <button
                        type="button"
                        className={`assistant-chat__icon-button${copiedId === message.id ? " assistant-chat__icon-button--done" : ""}`}
                        aria-label={
                          copiedId === message.id
                            ? "Mensaje copiado al portapapeles"
                            : "Copiar mensaje"
                        }
                        title={
                          copiedId === message.id
                            ? "Mensaje copiado al portapapeles"
                            : "Copiar mensaje"
                        }
                        onClick={() => copyMessage(message)}
                      >
                        {copiedId === message.id ? <CheckIcon /> : <CopyIcon />}
                      </button>
                      {copiedId === message.id ? (
                        <span className="assistant-chat__copy-done" role="status">
                          Copiado
                        </span>
                      ) : null}
                      {message.status === "failed" ? (
                        <button
                          type="button"
                          className="assistant-chat__icon-button"
                          aria-label="Reintentar mensaje"
                          title="Reintentar mensaje"
                          onClick={() => void send(message.content, true)}
                        >
                          <RetryIcon />
                        </button>
                      ) : null}
                    </div>
                    {messagePlan && showsPlanCard ? (
                      <PlanCard
                        plan={messagePlan}
                        approval={messageRunId === runId ? approval : undefined}
                        busy={processing}
                        onApprove={ownsLiveApproval ? () => void approve(false) : undefined}
                        onReject={ownsLiveApproval ? () => void approve(true) : undefined}
                      />
                    ) : null}
                    <AgentActivity
                      plan={messagePlan}
                      evidence={messageEvidence}
                      includePlan={!showsPlanCard}
                    />
                  </div>
                </article>
              );
            })}
            {processing || stream ? (
              <article
                className="ai-agent-grammar__bubble-row"
                aria-label={stream ? "Respuesta del agente en curso" : "El agente está trabajando"}
              >
                <Avatar name="Agente Lumat" />
                <div
                  className="ai-agent-grammar__bubble assistant-chat__thinking"
                  role="status"
                >
                  <span className="ai-agent-grammar__message-meta">Agente Lumat</span>
                  {stream ? (
                    // While tokens are still arriving the buffer is rendered as
                    // literal text, cursor included: partial markdown (an open
                    // fence, a half-written table) would re-lay-out the block on
                    // every chunk, and react-markdown re-parses the whole
                    // accumulated string each time. Once the buffer settles it is
                    // rendered as markdown, exactly like a persisted reply.
                    settledStream ? (
                      <Markdown
                        className="assistant-chat__message-content assistant-chat__stream"
                        content={settledStream}
                      />
                    ) : (
                      <p className="assistant-chat__message-content assistant-chat__stream">{stream}<span aria-hidden="true">▌</span></p>
                    )
                  ) : (
                    <span className="assistant-chat__thinking-row">
                      <span className="assistant-chat__thinking-dots" aria-hidden="true">
                        <i /><i /><i />
                      </span>
                      {THINKING_LABELS[lifecycle ?? ""] ?? "Pensando…"}
                    </span>
                  )}
                </div>
              </article>
            ) : null}
            {recoverable ? (
              <p role="status" aria-label="Ejecución recuperable">
                La ejecución no está confirmada; es recuperable desde el historial persistido.
              </p>
            ) : null}
          </div>
          <div className="assistant-chat__composer-wrap">
            <div className="assistant-chat__composer">
              <Textarea
                label="Mensaje"
                value={content}
                onChange={(event) => {
                  setContent(event.target.value);
                  resize(event.currentTarget);
                }}
                onKeyDown={keyDown}
                disabled={!thread || processing}
                placeholder="Escribe tu mensaje al asistente..."
                className="assistant-chat__textarea"
              />
              <div className="assistant-chat__composer-controls">
                <label className="assistant-chat__attach" title="Adjuntar archivo">
                  <PaperclipIcon />
                  <input
                    aria-label="Adjuntar archivo"
                    type="file"
                    accept="image/*,.pdf,.csv,.txt"
                    onChange={(event) => void attach(event)}
                    disabled={!thread || processing || uploading}
                  />
                </label>
                <button
                  type="button"
                  className="assistant-chat__send"
                  aria-label="Enviar"
                  title="Enviar"
                  onClick={() => void send()}
                  disabled={!thread || processing || !content.trim()}
                >
                  <SendIcon />
                </button>
              </div>
            </div>
            <div className="assistant-chat__status">
              <span>Conexión: {stateLabels[connection] ?? "No disponible"}</span>
              <span>{processing ? stateLabels[lifecycle ?? "planning"] ?? "Procesando" : "Listo"}</span>
              {uploading ? <span>Subiendo archivo…</span> : null}
              {attachments.map((item) => (
                <span className="assistant-chat__attachment" key={item.id}>{item.filename}</span>
              ))}
            </div>
          </div>
        </section>
      </div>
      {cortex?.status === "active" ? (
        <p role="status">
          Planificación activa: {cortex.topic}{" "}
          <Button variant="secondary" onClick={() => void closeSession()}>
            Cerrar planificación
          </Button>
        </p>
      ) : null}
      {handoff?.status === "pending" ? (
        <p role="status">
          El plan aprobado está listo para revisión. {report?.contenido}
        </p>
      ) : null}
    </PageFrame>
  );
}
