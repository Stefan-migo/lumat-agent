import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import {
  ApiError,
  approveChatPlan,
  closePlanningSession,
  createChatThread,
  getChatThread,
  getThreadToolPolicy,
  listProjectFiles,
  listProjects,
  openPlanningSession,
  resetThreadToolPolicy,
  sendChatMessage,
  stopChatThread,
  streamChatEvents,
  setChatThreadProject,
  attachProjectFileToThread,
  updateThreadToolPolicy,
  uploadAssistantAttachment,
} from "../../api";
import { ArrowUp, Check, ChevronDown, Copy, Folder, Paperclip, RotateCcw, Square, Workflow, Wrench } from "lucide-react";
import { roleLabels } from "../../roleLabels";
import type {
  AssistantApproval,
  AssistantArtifact,
  AssistantAttachment,
  AssistantEvidence,
  AssistantEvent,
  AssistantPlan,
  CortexArtifact,
  InternalChatMessage,
  InternalChatResponse,
  InternalChatThread,
  ThreadToolPolicy,
  PlanningSession,
  ProjectFile,
  Role,
} from "../../types";
import { realtimeClient } from "../../realtime";
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
import { CollapsibleMessages } from "../shared/CollapsibleMessages";
import { Icon } from "../primitives/Icon";
import { SearchInput } from "../primitives/SearchInput";
import { AssistantWorkspace } from "./AssistantWorkspace";
import { assistantToolLabel } from "./assistantToolLabels";
import { assistantFileIcon } from "./assistantFileIcon";
import "./AgentChat.css";

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
  cancelled: "Cancelado",
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

const RUN_WATCH_INTERVAL_MS = 3_000;
const RUN_WATCH_TIMEOUT_MS = 30 * 60 * 1_000;

const runStillProcessing = (result: InternalChatResponse, run: string) =>
  (result.messages ?? []).some(
    (message) =>
      message.author !== "agent" &&
      message.assistant_metadata?.run_id === run &&
      message.status === "processing",
  );

function planningCommand(value: string) {
  const match = value.match(/^\/planning(?:\s+(.+))?$/);
  if (!match) return null;
  const topic = match[1]?.trim();
  return topic?.toLowerCase() === "close"
    ? { action: "close" as const }
    : { action: "open" as const, topic };
}

/** Arguments are shown to the operator approving the plan, so values read as
 * text; a nested value falls back to JSON rather than [object Object]. */
function displayArgumentValue(value: unknown) {
  return typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "—");
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
  const argumentEntries = Object.entries(plan.arguments ?? {});
  const label = {
    pending: "Pendiente",
    rejected: "Rechazado",
    consumed: "Aprobado",
    completed: "Completado",
  }[plan.status ?? ""] ?? "Propuesto";
  const skillProposal = plan.tool === "skill.propose" ? plan.arguments ?? {} : null;

  return (
    <Card title="Plan de acción" className="assistant-chat__plan-card">
      {skillProposal ? (
        <section aria-label="Propuesta de habilidad">
          <h3>Propuesta de habilidad</h3>
          <dl>
            <dt>Nombre</dt><dd>{displayArgumentValue(skillProposal.name)}</dd>
            <dt>Descripción</dt><dd>{displayArgumentValue(skillProposal.description)}</dd>
            <dt>Vista previa</dt><dd>{displayArgumentValue(skillProposal.body)}</dd>
          </dl>
        </section>
      ) : <dl>
        <dt>Herramienta</dt>
        <dd>{plan.tool || "Respuesta del asistente"}</dd>
        <dt>Argumentos</dt>
        <dd>
          {argumentEntries.length > 0 ? (
            <dl>
              {argumentEntries.map(([key, value]) => (
                <Fragment key={key}>
                  <dt>{key}</dt>
                  <dd>{displayArgumentValue(value)}</dd>
                </Fragment>
              ))}
            </dl>
          ) : (
            "—"
          )}
        </dd>
      </dl>}
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
 * planner decided and which tools ran with their bounded detail. Renders
 * nothing when a turn was a plain answer with no tool work — a "plan" that
 * plans nothing is noise, not information.
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
              </div>
            ))}
          </>
        ) : null}
      </div>
    </details>
  );
}

export interface AgentChatProps {
  role: Role;
  userName?: string;
  threadId?: number;
  onThreadOpened?: (id: number) => void;
}

export function AgentChat({ role, threadId, onThreadOpened, userName }: AgentChatProps) {
  const requestedProject = new URLSearchParams(globalThis.location.search).get("proyecto") || undefined;
  const requestedId =
    threadId ??
    (Number(new URLSearchParams(globalThis.location.search).get("thread_id")) || undefined);
  const humanAuthorLabel = roleLabels[role];
  const [thread, setThread] = useState<InternalChatThread | null>(null);
  const [messages, setMessages] = useState<InternalChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState("");
  const [recoverable, setRecoverable] = useState(false);
  const [plan, setPlan] = useState<AssistantPlan | null>(null);
  const [approval, setApproval] = useState<AssistantApproval | null>(null);
  const [evidence, setEvidence] = useState<AssistantEvidence[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<AssistantAttachment[]>([]);
  const [artifacts, setArtifacts] = useState<AssistantArtifact[]>([]);
  const [uploading, setUploading] = useState(false);
  const [cortex, setCortex] = useState<PlanningSession | null>(null);
  const [report, setReport] = useState<CortexArtifact | null>(null);
  const [toolPolicy, setToolPolicy] = useState<ThreadToolPolicy | null>(null);
  const [toolPolicyLoading, setToolPolicyLoading] = useState(false);
  const [toolPolicyError, setToolPolicyError] = useState<string | null>(null);
  const [toolPolicySaving, setToolPolicySaving] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [stopMessage, setStopMessage] = useState<string | null>(null);
  const [planningOpen, setPlanningOpen] = useState(false);
  // Copy feedback: the icon that was just used swaps to a check and says so,
  // then reverts. Without it the click is silent and reads as a no-op.
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [messagesExpanded, setMessagesExpanded] = useState(false);
  const copyTimer = useRef<number | null>(null);
  const [topic, setTopic] = useState("");
  const [topicError, setTopicError] = useState("");
  const [projectChoices, setProjectChoices] = useState<{ slug: string; name: string }[]>([]);
  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [projectFiles, setProjectFiles] = useState<ProjectFile[]>([]);
  const [projectFilesLoading, setProjectFilesLoading] = useState(false);
  const [projectFilesError, setProjectFilesError] = useState<string | null>(null);
  const [projectActionLoading, setProjectActionLoading] = useState(false);
  const [projectActionError, setProjectActionError] = useState<string | null>(null);
  const [projectSearch, setProjectSearch] = useState("");
  const [fileSearch, setFileSearch] = useState("");
  const watchCancelledRef = useRef(false);
  const watchedRunRef = useRef<string | null>(null);

  const loadThread = (result: InternalChatResponse, preserveArtifacts = false) => {
    const state = result.thread.assistant_state;
    setThread(result.thread);
    setMessages(result.messages ?? []);
    if (
      state?.execution_status === "cancelled" ||
      (result.messages ?? []).some(
        (message) => message.status === "cancelled" && message.assistant_metadata?.run_id === result.thread.active_run_id,
      ) ||
      ((result.messages ?? []).some(
        (message) =>
          message.assistant_metadata?.run_id === result.thread.active_run_id &&
          (message.status === "processed" || message.status === "failed"),
      ) && state?.execution_status !== "running")
    ) setStopping(false);
    if (!preserveArtifacts) setPlan(result.thread.current_plan ?? null);
    setApproval(state?.approval ?? null);
    const persistedEvidence = (state?.events ?? []).flatMap((event) => event.evidence ?? []);
    if (!preserveArtifacts || persistedEvidence.length > 0) setEvidence(persistedEvidence);
    setLifecycle(state?.stage ?? null);
    setRunId(result.thread.active_run_id ?? null);
    setAttachments(result.attachments ?? []);
    setArtifacts(result.artifacts ?? []);
    setCortex(state?.cortex_session ?? null);
  };

  useEffect(() => {
    const request = requestedId
      ? getChatThread(requestedId)
      : requestedProject
        ? createChatThread(requestedProject)
        : Promise.resolve(null);
    void request
      .then((result) => {
        if (result) {
          loadThread(result);
          if (!requestedId && requestedProject) onThreadOpened?.(result.thread.id);
        } else {
          setThread(null);
          setMessages([]);
        }
      })
      .catch((reason: unknown) =>
        setError(reason instanceof ApiError ? reason.detail : "No pudimos abrir el chat"),
      )
      .finally(() => setLoading(false));
  }, [requestedId, requestedProject]);

  useEffect(() => {
    if (!thread) return;
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.conversation_id !== thread.id) return;
      if (event.type === "message") {
        setStream("");
        setMessages((current) => [
          ...current.filter((item) => item.id !== (event.data as InternalChatMessage).id),
          event.data as InternalChatMessage,
        ]);
      }
    });
    realtimeClient.connect();
    return () => {
      unsubscribe();
    };
  }, [thread]);

  useEffect(() => {
    if (!thread) {
      setToolPolicy(null);
      setToolPolicyLoading(false);
      setToolPolicyError(null);
      return;
    }
    let current = true;
    setToolPolicy(null);
    setToolPolicyLoading(true);
    setToolPolicyError(null);
    void getThreadToolPolicy(thread.id)
      .then((policy) => {
        if (!current) return;
        if (!Array.isArray(policy.available) || !Array.isArray(policy.opt_in_enabled) || typeof policy.inherited !== "boolean") {
          throw new Error("Invalid thread tool policy response");
        }
        setToolPolicy(policy);
      })
      .catch((reason: unknown) => {
        if (current) setToolPolicyError(reason instanceof ApiError ? reason.detail : "No pudimos cargar las herramientas");
      })
      .finally(() => {
        if (current) setToolPolicyLoading(false);
      });
    return () => { current = false; };
  }, [thread?.id]);

  const changeToolPolicy = async (next: () => Promise<ThreadToolPolicy>) => {
    setToolPolicySaving(true);
    setToolPolicyError(null);
    try {
      const policy = await next();
      setToolPolicy(policy);
    } catch (reason: unknown) {
      setToolPolicyError(reason instanceof ApiError && reason.status === 409
        ? "No puedes cambiar las herramientas mientras se ejecuta el asistente."
        : reason instanceof ApiError ? reason.detail : "No pudimos actualizar las herramientas");
    } finally {
      setToolPolicySaving(false);
    }
  };

  const stopRun = async () => {
    if (!thread) return;
    setStopping(true);
    setStopMessage(null);
    let waitingForSettlement = false;
    try {
      const result = await stopChatThread(thread.id, runId ?? undefined);
      waitingForSettlement = result.status === "stopping";
      if (result.status === "cancelled") {
        loadThread(await getChatThread(thread.id));
        setProcessing(false);
      }
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.status === 409) {
        try { loadThread(await getChatThread(thread.id)); } catch { /* Keep the current persisted view. */ }
        setStopMessage("La ejecución cambió o ya terminó. Actualizamos el estado del chat.");
      } else {
        setStopMessage(reason instanceof ApiError ? reason.detail : "No pudimos detener la ejecución.");
      }
    } finally {
      if (!waitingForSettlement) setStopping(false);
    }
  };

  // Reset on setup, not only on cleanup: StrictMode mounts, unmounts and
  // remounts every effect in dev, so a ref that is only ever set to `true`
  // stays `true` and the run watch below dies on its first tick — in dev only,
  // which is exactly where the panel is exercised.
  useEffect(() => {
    watchCancelledRef.current = false;
    return () => {
      watchCancelledRef.current = true;
    };
  }, []);

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

  const watchRunToSettle = async (id: number, run: string) => {
    if (watchedRunRef.current === run) return;
    watchedRunRef.current = run;
    try {
      const deadline = Date.now() + RUN_WATCH_TIMEOUT_MS;
      while (Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, RUN_WATCH_INTERVAL_MS));
        if (watchCancelledRef.current || watchedRunRef.current !== run) return;
        const snapshot = await getChatThread(id);
        if (!runStillProcessing(snapshot, run)) return;
      }
      setRecoverable(true);
    } finally {
      if (watchedRunRef.current === run) watchedRunRef.current = null;
    }
  };

  const openStream = async (id: number, run: string) => {
    setRunId(run);
    let gaveUp = false;
    try {
      await streamChatEvents(id, run, (event) => {
        if (event.type === "timeout") gaveUp = true;
        handleEvent(event);
      });
      if (gaveUp) await watchRunToSettle(id, run);
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

  const newChat = async () => {
    setError(null);
    let project = thread?.proyecto || requestedProject;
    if (!project && (role === "admin" || role === "operador")) {
      project = "default";
    }
    if (!project) {
      try {
        const result = await listProjects();
        if (result.projects.length === 0) {
          setError("Crea un proyecto primero para iniciar un chat.");
          return;
        }
        setProjectChoices(result.projects.map(({ slug, name }) => ({ slug, name })));
        setProjectPickerOpen(true);
      } catch (reason: unknown) {
        setError(reason instanceof ApiError ? reason.detail : "No pudimos cargar los proyectos");
      }
      return;
    }
    setLoading(true);
    try {
      const result = await createChatThread(project);
      loadThread(result);
      onThreadOpened?.(result.thread.id);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos crear el chat");
    } finally {
      setLoading(false);
    }
  };

  const createProjectChat = async (project: string) => {
    setProjectPickerOpen(false);
    setLoading(true);
    try {
      const result = await createChatThread(project);
      loadThread(result);
      onThreadOpened?.(result.thread.id);
    } catch (reason: unknown) {
      setError(reason instanceof ApiError ? reason.detail : "No pudimos crear el chat");
    } finally {
      setLoading(false);
    }
  };

  const createDefaultChat = async () => {
    if (role !== "admin" && role !== "operador") return;
    setError(null);
    setLoading(true);
    try {
      const result = await createChatThread("default");
      loadThread(result);
      onThreadOpened?.(result.thread.id);
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
        author: role,
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
          author: role,
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

  const attach = async (file: File | undefined) => {
    if (!file || !thread) return;
    setError(null);
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

  const handleAttachmentChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    void attach(file);
  };

  const changeProject = async (slug: string) => {
    if (!thread) return;
    setProjectActionLoading(true);
    setProjectActionError(null);
    try {
      const result = await setChatThreadProject(thread.id, slug);
      setThread(result.thread);
      setProjectPickerOpen(false);
    } catch (reason: unknown) {
      setProjectActionError(reason instanceof ApiError ? reason.detail : "No pudimos cambiar el proyecto.");
    } finally { setProjectActionLoading(false); }
  };

  const attachProjectFile = async (fileId: number) => {
    if (!thread) return;
    setProjectActionLoading(true);
    setProjectActionError(null);
    try {
      const result = await attachProjectFileToThread(thread.id, fileId);
      setAttachments((current) => [...current, result.attachment]);
    } catch (reason: unknown) {
      setProjectActionError(reason instanceof ApiError ? reason.detail : "No pudimos adjuntar el archivo del proyecto.");
    } finally { setProjectActionLoading(false); }
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

  const persistedActivity = (thread?.assistant_state?.events ?? [])
    .filter((event) => !runId || event.run_id === runId)
    .flatMap((event) => event.evidence ?? []);
  const activityEvidence = persistedActivity.length ? persistedActivity : evidence;
  const activeConversation = messages.length > 0;
  const isRunActive = processing || messages.some((message) => message?.status === "processing") || approval?.status === "pending";
  const toolControlsDisabled = isRunActive || toolPolicySaving;
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
      .filter((item) => item?.author === "agent" && item.assistant_metadata?.run_id)
      .map((item) => item.assistant_metadata?.run_id as string),
  );

  return (
    <AssistantWorkspace
      onCreateThread={() => void newChat()}
      onCreateDefaultThread={() => void createDefaultChat()}
      role={role}
      loadThreadTabs={Boolean(onThreadOpened)}
      attachments={attachments}
      artifacts={artifacts}
      evidence={activityEvidence}
      plan={plan}
      lifecycle={lifecycle}
      processing={processing}
    >
    <PageFrame
      title="Asistente Lumat"
      meta="Chat interno con el agente virtual."
      hideCopy
      state={state}
      className="assistant-chat"
    >
      <Dialog open={projectPickerOpen} onClose={() => setProjectPickerOpen(false)} title="Elegir proyecto">
        <div className="assistant-chat__planning-form">
          <p>Elige el proyecto para este chat.</p>
          {projectChoices.map((project) => <Button key={project.slug} variant="secondary" disabled={projectActionLoading} onClick={() => void (thread ? changeProject(project.slug) : createProjectChat(project.slug))}><Icon icon={Folder} size="sm" />{project.name}</Button>)}
          {projectActionError ? <p role="alert">{projectActionError}</p> : null}
        </div>
      </Dialog>
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
      <div className={`assistant-chat__surface${!processing && !stream && messages.length === 0 ? " assistant-chat__surface--empty" : ""}`} data-tier={commandCenterTier(globalThis.innerWidth || 1024)}>
        <section className="assistant-chat__conversation" aria-label="Conversación">
          <div className="assistant-chat__messages" aria-live="polite">
            {!thread && !loading ? (
              <div className="assistant-chat__hero">
                <h2>{`${new Date().getHours() < 12 ? "Buenos días" : new Date().getHours() < 20 ? "Buenas tardes" : "Buenas noches"}${userName ? `, ${userName}` : ""}`}</h2>
                <Button onClick={() => void newChat()} disabled={loading}>Iniciar conversación</Button>
              </div>
            ) : null}
            {thread && messages.length === 0 && !loading ? (
              <div className="assistant-chat__hero">
                <h2>¿En qué trabajamos hoy?</h2>
                <p>Consulta, planifica o trabaja en tus proyectos con el asistente Lumat.</p>
              </div>
            ) : null}
            <CollapsibleMessages total={messages.length} previewCount={10} expanded={messagesExpanded} onToggle={() => setMessagesExpanded((value) => !value)}>
            {(messages.length > 10 && !messagesExpanded ? messages.slice(-10) : messages).map((message) => {
              const outbound = message.author !== "agent";
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
                  aria-label={`Mensaje de ${outbound ? humanAuthorLabel.toLocaleLowerCase("es") : "agente"}`}
                >
                  <Avatar name={outbound ? humanAuthorLabel : "Agente Lumat"} />
                  <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
                    <span className="ai-agent-grammar__message-meta">
                      {outbound ? humanAuthorLabel : "Agente Lumat"}
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
                    {message.status === "cancelled" ? <p role="status">Cancelado</p> : null}
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
                        {copiedId === message.id ? <Icon icon={Check} size="sm" /> : <Icon icon={Copy} size="sm" />}
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
                          <Icon icon={RotateCcw} size="sm" />
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
            </CollapsibleMessages>
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
                    // accumulated string each time. Once the current buffer has
                    // settled it is rendered as markdown, exactly like a persisted reply.
                    settledStream === stream ? (
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
          {thread ? <div className={`assistant-chat__composer-stack${activeConversation ? " assistant-chat__composer-stack--active" : ""}`} onDragOver={(event) => { if (Array.from(event.dataTransfer.types).includes("Files")) event.preventDefault(); }} onDrop={(event) => { event.preventDefault(); const file = event.dataTransfer.files[0]; if (file) void attach(file); }}>
            {!activeConversation ? <div className="assistant-chat__composer-tray">
                <div className="assistant-chat__composer-bottom-row assistant-chat__composer-bottom-row--grouped">
                <div className="assistant-chat__project-popover" onClick={(event) => { if (!(event.target as HTMLElement).closest(".popover__trigger")) return; setProjectActionLoading(true); setProjectActionError(null); void listProjects().then((result) => setProjectChoices(result.projects.map(({ slug, name }) => ({ slug, name })))).catch((reason: unknown) => setProjectActionError(reason instanceof ApiError ? reason.detail : "No pudimos cargar los proyectos.")).finally(() => setProjectActionLoading(false)); }}><Popover title="Proyecto" triggerLabel={thread.proyecto === "default" ? "General" : projectChoices.find((project) => project.slug === thread.proyecto)?.name ?? thread.proyecto ?? "General"} trigger={<><Icon icon={Folder} size="sm" />{thread.proyecto === "default" ? "General" : projectChoices.find((project) => project.slug === thread.proyecto)?.name ?? thread.proyecto ?? "General"}<Icon icon={ChevronDown} size="sm" /></>} state={isRunActive ? "disabled" : "default"}>
                  {projectActionLoading ? <p role="status">Cargando proyectos…</p> : null}
                  {projectActionError ? <p role="alert">{projectActionError}</p> : null}
                  <SearchInput aria-label="Buscar proyecto" placeholder="Buscar proyecto…" onSearch={setProjectSearch} />
                  <button type="button" className="assistant-chat__project-option" disabled={isRunActive || projectActionLoading} aria-current={thread.proyecto === "default" ? "true" : undefined} onClick={() => void changeProject("default")}><Icon icon={Folder} size="sm" /><span className="assistant-chat__menu-label">General / Sin proyecto</span>{thread.proyecto === "default" ? "✓" : ""}</button>
                  {projectChoices.filter((project) => project.slug !== "default" && `${project.name} ${project.slug}`.toLocaleLowerCase("es-CL").includes(projectSearch.toLocaleLowerCase("es-CL"))).map((project) => <button type="button" className="assistant-chat__project-option" key={project.slug} disabled={isRunActive || projectActionLoading} aria-current={thread.proyecto === project.slug ? "true" : undefined} onClick={() => void changeProject(project.slug)}><Icon icon={Folder} size="sm" /><span className="assistant-chat__menu-label">{project.name}</span>{thread.proyecto === project.slug ? "✓" : ""}</button>)}
                  <p className="assistant-chat__popover-footer">El proyecto define el contexto de este hilo.</p>
                </Popover></div>
                <Popover title="Archivos de este hilo" triggerLabel={`Archivos ${attachments.length}`} trigger={<><Icon icon={Paperclip} size="sm" />Archivos <span>{attachments.length}</span></>}>
                  <SearchInput aria-label="Buscar archivo" placeholder="Buscar archivo…" onSearch={setFileSearch} />
                  {attachments.filter((item) => item.filename.toLocaleLowerCase("es-CL").includes(fileSearch.toLocaleLowerCase("es-CL"))).map((item) => <p className="assistant-chat__file-row" key={item.id}><Icon icon={assistantFileIcon(item.filename, item.content_type)} size="sm" /><span className="assistant-chat__menu-label">{item.filename}<small>{item.kind.toLocaleUpperCase("es-CL")} · Adjuntado</small></span></p>)}
                  {attachments.length === 0 ? <p role="status">Este hilo aún no tiene archivos adjuntos.</p> : null}
                  <div className="assistant-chat__file-actions"><label className="assistant-chat__tool-option" htmlFor="assistant-chat-file-picker"><strong>+ Adjuntar archivo</strong></label>
                  {thread.proyecto && thread.proyecto !== "default" ? <div className="assistant-chat__project-files-popover" onClick={(event) => { if (!(event.target as HTMLElement).closest(".popover__trigger")) return; setProjectFilesLoading(true); setProjectFilesError(null); void listProjectFiles(thread.proyecto!).then((result) => setProjectFiles(Array.isArray(result.files) ? result.files : [])).catch((reason: unknown) => setProjectFilesError(reason instanceof ApiError ? reason.detail : "No pudimos cargar los archivos del proyecto.")).finally(() => setProjectFilesLoading(false)); }}><Popover title="Archivos del proyecto" triggerLabel="Agregar del proyecto">{projectFilesLoading ? <p role="status">Cargando archivos…</p> : null}{projectFilesError ? <p role="alert">{projectFilesError}</p> : null}{projectFiles.filter((file) => file.filename.toLocaleLowerCase("es-CL").includes(fileSearch.toLocaleLowerCase("es-CL"))).map((file) => <button type="button" className="assistant-chat__project-option" key={file.id} disabled={projectActionLoading || isRunActive} onClick={() => void attachProjectFile(file.id)}><Icon icon={assistantFileIcon(file.filename, file.content_type)} size="sm" /><span className="assistant-chat__menu-label">{file.filename}<small>{file.content_type}</small></span></button>)}{!projectFilesLoading && !projectFilesError && projectFiles.length === 0 ? <p role="status">Este proyecto no tiene archivos disponibles.</p> : null}</Popover></div> : null}</div>
                </Popover>
                <span className="assistant-chat__tools-summary"><Icon icon={Wrench} size="sm" />Herramientas <span>{toolPolicy?.opt_in_enabled.length ?? 0}</span></span>
                {projectActionLoading ? <span role="status">Actualizando…</span> : null}
              </div>
            </div> : null}
            <div className="assistant-chat__composer-wrap">
            {stopMessage ? <p role="status">{stopMessage}</p> : null}
            <div className="assistant-chat__composer">
              <input className="assistant-chat__file-picker" id="assistant-chat-file-picker" aria-label="Adjuntar archivo" type="file" accept="image/*,.pdf,.csv,.txt" onChange={handleAttachmentChange} disabled={!thread || isRunActive || uploading} />
              {attachments.length > 0 || uploading ? (
                <div className="assistant-chat__attachment-list" aria-label="Archivos adjuntos">
                    {attachments.map((item) => (
                      <span className="assistant-chat__attachment" key={item.id}>
                      <Icon icon={assistantFileIcon(item.filename, item.content_type)} size="sm" /><span>{item.filename}</span><span>· {item.kind.toLocaleUpperCase("es-CL")} · Listo</span>
                    </span>
                  ))}
                  {uploading ? <span role="status">Subiendo archivo…</span> : null}
                </div>
              ) : null}
              <Textarea
                label="Mensaje"
                value={content}
                onChange={(event) => {
                  setContent(event.target.value);
                  resize(event.currentTarget);
                }}
                onKeyDown={keyDown}
                disabled={!thread || processing}
                placeholder="Escribe un mensaje al asistente…"
                className="assistant-chat__textarea"
              />
              <div className="assistant-chat__composer-controls">
                <div className="assistant-chat__add-popover"><Popover title="Herramientas del hilo" triggerLabel="+" dismissible titleAccessory={<span className="assistant-chat__tool-count">{toolPolicy?.opt_in_enabled.length ?? 0} de {toolPolicy?.available.length ?? 0} activadas</span>}>
                  <label className="assistant-chat__tool-option" htmlFor="assistant-chat-file-picker">
                    <Icon icon={Paperclip} size="sm" />
                    <span><strong>Adjuntar archivo</strong><small>Sube un documento o una imagen</small></span>
                  </label>
                  <hr className="assistant-chat__tool-divider" />
                  <div className="assistant-chat__tool-chips assistant-chat__tool-chips--stacked" aria-label="Herramientas disponibles">
                    {toolPolicyLoading ? <p role="status">Cargando herramientas…</p> : null}
                    {toolPolicyError ? <p role="alert">{toolPolicyError}</p> : null}
                    {toolPolicy && toolPolicy.available.length === 0 ? <p role="status">No hay herramientas opcionales disponibles.</p> : null}
                    {toolPolicy && toolPolicy.available.length > 0 ? <label className="assistant-chat__tool-row assistant-chat__tool-master"><Icon icon={Wrench} size="sm" /><span><strong>Todas las herramientas</strong><small>Activar o desactivar todas</small></span><input type="checkbox" aria-label="Todas las herramientas" checked={toolPolicy.available.every((name) => toolPolicy.opt_in_enabled.includes(name))} disabled={toolControlsDisabled || toolPolicyLoading} onChange={() => void changeToolPolicy(() => updateThreadToolPolicy(thread.id, toolPolicy.available.every((name) => toolPolicy.opt_in_enabled.includes(name)) ? [] : [...toolPolicy.available]))} /></label> : null}
                    {[...new Set(toolPolicy?.available.map((name) => assistantToolLabel(name).group) ?? [])].map((group) => <section key={group} className="assistant-chat__tool-group"><h3>{group}</h3>{toolPolicy?.available.filter((name) => assistantToolLabel(name).group === group).map((name) => {
                      const enabled = toolPolicy.opt_in_enabled.includes(name);
                      const tool = assistantToolLabel(name);
                      return <label key={name} className="assistant-chat__tool-row"><Icon icon={tool.icon} size="sm" /><strong>{tool.label}</strong><input type="checkbox" aria-label={tool.label} checked={enabled} disabled={toolControlsDisabled || toolPolicyLoading} onChange={() => {
                        const selected = new Set(toolPolicy.opt_in_enabled);
                        if (enabled) selected.delete(name); else selected.add(name);
                        void changeToolPolicy(() => updateThreadToolPolicy(thread.id, [...selected]));
                      }} /></label>;
                    })}</section>)}
                    {toolPolicy && !toolPolicy.inherited ? <><hr className="assistant-chat__tool-divider" /><button type="button" className="assistant-chat__tool-option assistant-chat__tool-reset" disabled={toolControlsDisabled} onClick={() => void changeToolPolicy(() => resetThreadToolPolicy(thread.id))}><Icon icon={RotateCcw} size="sm" /><span><strong>Usar la selección del proyecto</strong><small>Aplicar las herramientas definidas en el proyecto.</small></span></button></> : null}
                    {isRunActive ? <p role="status">Las herramientas están bloqueadas durante la ejecución.</p> : null}
                    <p className="assistant-chat__popover-footer">La selección se aplica a este hilo.</p>
                  </div>
                </Popover></div>
                <Button variant="tertiary" className={`assistant-chat__planning-pill${cortex?.status === "active" ? " assistant-chat__planning-active" : ""}`} onClick={() => setPlanningOpen(true)} disabled={!thread || processing}>
                  <Icon icon={Workflow} size="sm" />
                  Planificar
                </Button>
                <Button variant="tertiary" disabled title="Próximamente">@ Agente · Próximamente</Button>
                <button
                  type="button"
                  className="assistant-chat__send"
                  aria-label={isRunActive ? stopping ? "Deteniendo…" : "Detener ejecución" : "Enviar"}
                  title={isRunActive ? stopping ? "Deteniendo…" : "Detener ejecución" : "Enviar"}
                  onClick={() => isRunActive ? void stopRun() : void send()}
                  disabled={isRunActive ? stopping : !content.trim()}
                >
                  <Icon icon={isRunActive ? Square : ArrowUp} size="md" />
                </button>
              </div>
            </div>
            </div>
          </div>
          : null}
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
      {report ? (
        <p role="status">Informe de planificación: {report.contenido}</p>
      ) : null}
    </PageFrame>
    </AssistantWorkspace>
  );
}
