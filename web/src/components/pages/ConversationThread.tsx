import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Bot, CheckCheck, CircleCheck, Clock, Copy, Info, Lock, Paperclip, SendHorizonal, ShieldAlert, UserRound, UserRoundPlus, WifiOff, Mic, Square, X } from "lucide-react";
import { ApiError, acknowledgeCase, changeConversationState, getConversation, listActiveConversations, listConversations, retryMessage, sendMedia, sendMessage } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { ConversationThread as ThreadData, Message } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Dialog } from "../primitives/Dialog";
import { Icon } from "../primitives/Icon";
import { Menu, type MenuItem } from "../primitives/Menu";
import { StatusBadge } from "../primitives/StatusBadge";
import { Textarea } from "../primitives/Textarea";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { Markdown } from "../shared/Markdown";
import { CollapsibleMessages } from "../shared/CollapsibleMessages";
import { caseStatusLabel, caseStatusTone, conversationLabel } from "../shared/toneMaps";
import { pathForRoute } from "../domain/panelRoutes";
import { realtimeClient, type ConnectionStatus } from "../../realtime";
import "./ConversationThread.css";

export interface ConversationThreadProps { conversationId?: number; data?: ThreadData | null; state?: AsyncDataState | "stale"; customerName?: (id: number) => string; refreshKey?: number; onMutate?: () => void; onBack?: () => void; interactive?: boolean; }
export function NoReplyNote() { return <StateMessage tone="info" role="status" title="Canal automático" detail="Este es un canal automático — no respondas a este mensaje (HH-5)." />; }
function messageAuthor(message: Message, customerId: number, customerName?: (id: number) => string) {
  return message.direction === "inbound"
    ? customerName?.(customerId) ?? `Cliente #${customerId}`
    : "Lumat";
}

function MessageBubble({ message, customerId, customerName }: { message: Message; customerId: number; customerName?: (id: number) => string }) {
  const author = messageAuthor(message, customerId, customerName);
  const outbound = message.direction === "outbound";
  const isText = message.msg_type === "text";
  const hasMedia = !isText && (Boolean(message.media_url || message.media_download_url) || ["image", "video", "audio", "document"].includes(message.msg_type));
  const mediaUrl = message.media_download_url;
  const mediaLabel = message.caption || message.filename || "Archivo adjunto";
  const unavailable = hasMedia && message.media_available === false;
  const mediaContent = !hasMedia ? null : unavailable ? <p className="conversation-thread__media-unavailable" role="status">Este archivo no está disponible.</p> : mediaUrl ? (() => {
    switch (message.msg_type) {
      case "image":
        return <a className="conversation-thread__image-link" href={mediaUrl} target="_blank" rel="noopener noreferrer" aria-label={`Abrir imagen: ${mediaLabel}`}><img className="conversation-thread__image" src={mediaUrl} alt={message.caption || "Imagen adjunta"} /></a>;
      case "video":
        return <video className="conversation-thread__video" src={mediaUrl} controls aria-label={message.caption || "Video adjunto"} />;
      case "audio":
        return <div className="conversation-thread__audio"><span>Audio adjunto</span><audio src={mediaUrl} controls aria-label={message.caption || "Audio adjunto"} /></div>;
      case "document":
        return <a className="conversation-thread__document" href={mediaUrl} download={message.filename || true}>{message.filename || message.caption || "Descargar documento"}</a>;
      default:
        return <a className="conversation-thread__document" href={mediaUrl} download>{message.caption || "Archivo adjunto"}</a>;
    }
  })() : <p className="conversation-thread__media-unavailable" role="status">Este archivo no está disponible.</p>;
  return <div className={`ai-agent-grammar__bubble-row${outbound ? " ai-agent-grammar__bubble-row--outbound" : ""}`} data-bubble aria-label={`Mensaje ${outbound ? "saliente" : "entrante"} de ${author}`}>
    <div className="ai-agent-grammar__bubble-stack">
      {/* One author label, above the outgoing bubble only: the mockup drops the per-message avatars
          that used to sit on both sides and keeps the speaker as text. */}
      {outbound ? <span className="ai-agent-grammar__message-meta">{author}</span> : null}
      <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
        {isText ? <span>{message.text ?? "—"}{message.media_url ? " 📎" : null}</span> : <>
          {message.text ? <span>{message.text}</span> : null}
          {mediaContent}
          {hasMedia && message.caption ? <p className="conversation-thread__media-caption">{message.caption}</p> : null}
        </>}
        {message.delivery_status === "failed" ? <span className="ai-agent-grammar__message-error" role="alert">Entrega fallida{message.delivery_error ? `: ${message.delivery_error}` : ""}</span> : null}
        <span className="conversation-thread__bubble-meta">
          <span>{message.created_at?.slice(11, 16) ?? "—"}</span>
          {outbound && message.delivery_status === "sent" ? <span className="conversation-thread__bubble-check" role="img" aria-label="Entregado"><Icon icon={CheckCheck} size="sm" /></span> : null}
        </span>
      </div>
    </div>
  </div>;
}

function displayCapturedValue(value: unknown) {
  return typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "—");
}
// Captured data is free-form and can carry internal markers (e.g. `_pending`); hide those and
// humanize the key so the operator never reads a raw snake_case identifier.
const CAPTURED_LABELS: Record<string, string> = { name: "Nombre", comuna: "Comuna", urgencia: "Urgencia informada", urgencia_informada: "Urgencia informada", tipo_equipo: "Tipo de equipo", direccion: "Dirección", telefono: "Teléfono" };
const capturedLabel = (key: string) => CAPTURED_LABELS[key] ?? key.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
const capturedEntries = (data: Record<string, unknown>) => Object.entries(data).filter(([key]) => !key.startsWith("_"));
// Activity rows are persisted with a technical vocabulary (`classified` + `intent:<intent>`,
// `kb_retrieved` + `chunks:<n>`, `escalation` + `handoff:<reason>` — see app/services/realtime.py).
// Translate them into operator-facing Spanish so the chip is not raw machine text.
const ACTIVITY_LABELS: Record<string, string> = { classified: "Intención detectada", kb_retrieved: "Se consultó la base de conocimiento", escalation: "Derivado a atención humana" };
const INTENT_LABELS: Record<string, string> = { calefont: "calefón", caldera: "caldera", calefaccion: "calefacción", solicitar_visita: "solicitar una visita", valores: "valores", postventa: "postventa", consulta: "consulta", unknown: "sin determinar" };
function activityText(activity: { event: string; cause?: string | null }) {
  const base = ACTIVITY_LABELS[activity.event] ?? activity.event;
  const cause = activity.cause ?? "";
  if (activity.event === "classified" && cause.startsWith("intent:")) return `${base}: ${INTENT_LABELS[cause.slice(7)] ?? cause.slice(7)}`;
  if (activity.event === "kb_retrieved" && cause.startsWith("chunks:")) return `${base} (${cause.slice(7)} resultados)`;
  return base;
}
const MESSAGE_PREVIEW = 10;
/** Day separator label, e.g. "9 de octubre de 2026", the shape the mockup uses above each day. */
const formatDay = (isoDay: string) => new Intl.DateTimeFormat("es-CL", { dateStyle: "long" }).format(new Date(`${isoDay}T12:00:00`));
// Case priority arrives as either the API's English enum or the domain's Spanish value.
const PRIORITY_LABELS: Record<string, string> = { high: "Prioridad alta", alta: "Prioridad alta", medium: "Prioridad normal", media: "Prioridad normal", normal: "Prioridad normal", low: "Prioridad baja", baja: "Prioridad baja" };
const priorityLabel = (value: string) => PRIORITY_LABELS[value] ?? `Prioridad ${value}`;
const priorityTone = (value: string) => value === "high" || value === "alta" ? "warning" as const : "neutral" as const;

function ConversationContext({ conversation }: { conversation: NonNullable<ThreadData["conversation"]> }) {
  const customer = conversation.customer;
  const caseData = conversation.case;
  const phone = customer?.phone_e164 ?? conversation.wa_phone ?? null;
  const caseStatus = conversation.case_status ?? caseData?.status ?? null;
  const casePriority = conversation.case_priority ?? caseData?.priority ?? null;
  const captured = conversation.captured_data ?? {};
  const capturedRows = capturedEntries(captured);
  // The capture flow can leave location unanswered while the customer's ficha already knows it.
  // Fall back to the profile so the operator never sees an empty section for known data.
  const capturedKeys = new Set(Object.keys(captured).map((key) => key.toLowerCase()));
  const profileRows: Array<[string, string]> = [];
  if (customer?.comuna && !capturedKeys.has("comuna")) profileRows.push(["Comuna", customer.comuna]);
  if (customer?.address && !capturedKeys.has("direccion") && !capturedKeys.has("address")) profileRows.push(["Dirección", customer.address]);
  return <aside className="ai-agent-grammar__inspector" aria-label="Inspector de conversación">
      {customer ? <section className="conversation-context__section" aria-labelledby="conversation-customer-heading">
        <h2 id="conversation-customer-heading">Cliente</h2>
        <div className="conversation-context__customer">
          <Avatar name={customer.name ?? phone ?? "Cliente"} />
          <div className="conversation-context__customer-body">
            <strong>{customer.name ?? "Sin nombre"}</strong>
            <span className="conversation-context__phone">{phone ?? "Sin teléfono"}{phone ? <button type="button" className="conversation-context__copy" aria-label="Copiar teléfono" onClick={() => void navigator.clipboard?.writeText(phone)}><Copy aria-hidden="true" /></button> : null}</span>
          </div>
        </div>
      </section> : null}
      {caseData ? <section className="conversation-context__section" aria-labelledby="conversation-case-heading">
        <div className="conversation-context__case-head"><h2 id="conversation-case-heading">Caso vinculado</h2>{conversation.case_id != null ? <a className="conversation-context__case-link" href={pathForRoute({ view: "clients", clientId: conversation.customer_id, clientTab: "cases" })}>Ver caso <span aria-hidden="true">→</span></a> : null}</div>
        <p className="conversation-context__case-title">{caseData.service}</p>
        <div className="conversation-context__badges">{caseStatus ? <Badge tone={caseStatusTone(caseStatus)}>{caseStatusLabel(caseStatus)}</Badge> : null}{casePriority ? <Badge tone={priorityTone(casePriority)}>{priorityLabel(casePriority)}</Badge> : null}</div>
        {caseData.summary ? <div className="conversation-context__case-summary"><Markdown content={caseData.summary} /></div> : null}
        <dl><div className="ai-agent-grammar__detail"><dt>Emergencia</dt><dd>{conversation.emergency ? "Sí" : "No"}</dd></div><div className="ai-agent-grammar__detail"><dt>Reconocimiento</dt><dd>{conversation.acknowledged_at ? "Reconocida" : "Pendiente"}</dd></div></dl>
      </section> : null}
      {capturedRows.length > 0 || profileRows.length > 0 ? <details open><summary>Datos capturados</summary><dl>{capturedRows.map(([key, value]) => <div className="ai-agent-grammar__detail" key={key}><dt>{capturedLabel(key)}</dt><dd>{displayCapturedValue(value)}</dd></div>)}{profileRows.map(([label, value]) => <div className="ai-agent-grammar__detail" key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></details> : null}
  </aside>;
}
export function ConversationThread({ conversationId, data: controlledData, state: controlledState, customerName, refreshKey = 0, onMutate, onBack, interactive = false }: ConversationThreadProps) {
  const [text, setText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const cancelRecordingRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [messagesExpanded, setMessagesExpanded] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [liveActivity, setLiveActivity] = useState<Array<{ event: string; cause?: string | null; actor?: string | null }>>([]);
  const fetchThread = useCallback(async () => { if (conversationId === undefined) throw new Error("conversation id is required"); return getConversation(conversationId, messagesExpanded ? undefined : MESSAGE_PREVIEW); }, [conversationId, messagesExpanded, refreshKey]);
  const fetched = useAsyncData(fetchThread, controlledData === undefined, refreshKey);
  const data = controlledData ?? fetched.data;
  const state = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const conversation = data?.conversation;
  const messages = data?.messages ?? [];
  const refresh = fetched.retry;
  const toggleMessages = () => { setMessagesExpanded((value) => !value); refresh(); };
  useEffect(() => {
    if (controlledData !== undefined || conversationId === undefined) return;
    const unsubscribe = realtimeClient.subscribe((event) => {
      if (event.type !== "snapshot" && event.conversation_id !== conversationId) return;
      if (event.type === "activity") setLiveActivity((current) => [...current, event.data as { event: string; cause?: string | null; actor?: string | null }]);
      if (event.type === "snapshot") {
        const activity = (event.data as { activity?: Array<{ conversation_id?: number; event: string; cause?: string | null; actor?: string | null }> }).activity ?? [];
        setLiveActivity(activity.filter((item) => item.conversation_id === conversationId));
      }
      if (event.type === "message" || event.type === "conversation" || event.type === "snapshot") refresh();
    });
    const unsubscribeStatus = realtimeClient.subscribeStatus(setConnection);
    const unregisterRecovery = realtimeClient.registerRecovery(async () => {
      await Promise.all([getConversation(conversationId), listConversations(), listActiveConversations()]);
      refresh();
    });
    realtimeClient.connect();
    return () => { unsubscribe(); unsubscribeStatus(); unregisterRecovery(); };
  }, [controlledData, conversationId, refresh]);
  const windowOpen = conversation?.reply_window_open === true;
  const releaseStream = () => { streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null; };
  useEffect(() => () => { cancelRecordingRef.current = true; recorderRef.current?.stop(); releaseStream(); }, []);
  // Formats Meta accepts come first so a browser that can produce one is left untouched by the
  // server. Chromium only offers webm, which Meta rejects: the api remuxes it to ogg/opus before
  // uploading, so the recording works everywhere instead of being disabled outside Firefox/Safari.
  const supportedRecordingMime = typeof MediaRecorder !== "undefined"
    ? ["audio/ogg;codecs=opus", "audio/mp4", "audio/aac", "audio/webm;codecs=opus", "audio/webm"].find((mime) => MediaRecorder.isTypeSupported(mime)) ?? null
    : null;
  const recordingExtension = (mime: string) => ["audio/ogg", "audio/mp4", "audio/webm", "audio/aac"]
    .find((container) => mime.startsWith(container))?.split("/")[1] ?? "ogg";
  const mutate = async (action: () => Promise<unknown>) => { setBusy(true); setMutationError(null); try { await action(); setText(""); onMutate?.(); refresh(); } catch (error) { setMutationError(error instanceof ApiError ? `${error.status}: ${error.detail}` : error && typeof error === "object" && "detail" in error ? String(error.detail) : "No se pudo completar la acción"); } finally { setBusy(false); } };
  const sendSelectedFile = (file: File, fileCaption = "") => {
    if (!conversationId || busy) return;
    void mutate(async () => { await sendMedia(conversationId, { file, requestId: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`, ...(fileCaption.trim() ? { caption: fileCaption.trim() } : {}) }); setSelectedFile(null); setCaption(""); });
  };
  const startRecording = async () => {
    if (!windowOpen || busy || !supportedRecordingMime) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      cancelRecordingRef.current = false;
      const recorder = new MediaRecorder(stream, { mimeType: supportedRecordingMime });
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = () => {
        releaseStream();
        recorderRef.current = null;
        setRecording(false);
        if (!cancelRecordingRef.current && chunksRef.current.length && conversationId) {
          const blob = new Blob(chunksRef.current, { type: supportedRecordingMime });
          const extension = recordingExtension(supportedRecordingMime);
          sendSelectedFile(new File([blob], `audio-${Date.now()}.${extension}`, { type: supportedRecordingMime }));
        }
      };
      recorder.start();
      setRecordingSeconds(0);
      setRecording(true);
    } catch (error) { setMutationError(error instanceof Error ? error.message : "No se pudo acceder al micrófono"); }
  };
  const stopRecording = (cancel = false) => { cancelRecordingRef.current = cancel; recorderRef.current?.stop(); if (cancel) { releaseStream(); setRecording(false); } };
  useEffect(() => { if (!recording) return; const timer = window.setInterval(() => setRecordingSeconds((value) => value + 1), 1000); return () => window.clearInterval(timer); }, [recording]);
  const acknowledgesEmergency = Boolean(conversation?.case && conversation?.emergency && !conversation.acknowledged_at && conversation.case_id != null);
  const conversationMenuItems = (options: { includeTake?: boolean; includeInfo?: boolean } = {}): MenuItem[] => conversation ? [
    ...(options.includeInfo ? [{ value: "info", label: "Información del chat", icon: Info }] : []),
    ...(options.includeTake ? [{ value: "human", label: "Tomar conversación", icon: UserRoundPlus, disabled: busy || conversation.state === "human" }] : []),
    { value: "bot", label: "Devolver al agente", icon: Bot, disabled: busy || conversation.state !== "human" },
    { value: "closed", label: "Cerrar conversación", icon: CircleCheck, disabled: busy || conversation.state !== "human" },
    ...(acknowledgesEmergency ? [{ value: "acknowledge", label: "Reconocer emergencia", icon: ShieldAlert, disabled: busy }] : []),
  ] : [];
  const runMenuAction = (value: string) => {
    if (value === "info") { setInfoOpen(true); return; }
    if (!conversation) return;
    if (value === "human") void mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0));
    else if (value === "bot") void mutate(() => changeConversationState(conversation.id, "bot", conversation.version ?? 0));
    else if (value === "closed") void mutate(() => changeConversationState(conversation.id, "closed", conversation.version ?? 0));
    else if (value === "acknowledge" && conversation.case_id != null) void mutate(() => acknowledgeCase(conversation.case_id!));
    // Any other value is deliberately ignored: an unknown menu action must never mutate state
    // (previously anything unexpected fell through to emergency acknowledgement).
  };
  const desktopActions = conversation ? <><Button disabled={busy || conversation.state === "human"} onClick={() => void mutate(() => changeConversationState(conversation.id, "human", conversation.version ?? 0))}><UserRoundPlus aria-hidden="true" />Tomar conversación</Button><Menu trigger="icon" align="end" collisionPadding={8} label="Acciones de la conversación" disabled={busy} items={conversationMenuItems()} onSelect={runMenuAction} /></> : null;
  const mobileActions = conversation ? <Menu trigger="icon" align="end" collisionPadding={8} label="Más acciones de la conversación" disabled={busy} items={conversationMenuItems({ includeTake: true, includeInfo: true })} onSelect={runMenuAction} /> : null;
  const loadError = fetched.error;
  const loadTitle = loadError instanceof ApiError && loadError.status === 401 ? "Sesión requerida" : loadError instanceof ApiError && loadError.status === 403 ? "No tienes permiso para ver este panel" : "No pudimos cargar la conversación";
  const displayName = conversation ? (conversation.customer?.name ?? customerName?.(conversation.customer_id) ?? `Cliente #${conversation.customer_id}`) : undefined;
  const phone = conversation?.customer?.phone_e164 ?? conversation?.wa_phone ?? null;
  // Collapsed when a conversation opens: the thread is what the operator came for, and the details
  // are one click away. Narrow screens hide the overlay entirely (ConversationThread.css) and use
  // the "Información del chat" sheet from the conversation menu instead.
  const [detailOpen, setDetailOpen] = useState(false);
  // Opening another conversation is a fresh start: the details collapse again instead of staying
  // open from the previous customer.
  useEffect(() => { setDetailOpen(false); }, [conversationId]);
  return <PageFrame className="conversations-page conversation-thread-page" title="" state={state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando conversación" /> : state === "error" ? <><StateMessage tone="danger" role="alert" title={loadTitle} /><Button variant="secondary" onClick={refresh}>Reintentar</Button></> : state === "stale" ? <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="Mostramos la información disponible." /> : null}>
      {conversation ? <header className="conversation-thread__header">
        {onBack ? <Button variant="tertiary" className="conversation-thread__back" aria-label="Volver a conversaciones" onClick={onBack}><ArrowLeft aria-hidden="true" /></Button> : null}
        <Avatar className="conversation-thread__hero-avatar" name={displayName ?? "Conversación"} />
        <h1>{displayName}</h1>
        {phone ? <span className="conversation-thread__phone"><span className="conversation-thread__online" aria-hidden="true" />{phone}</span> : null}
        <span className="conversation-thread__id">· #{conversation.id}</span>
        <span role="status" aria-label={conversationLabel(conversation.state)}><StatusBadge status={conversation.state as "bot" | "human" | "closed"} /></span>
        <div className="conversation-thread__header-actions">
          {interactive ? <><span className="conversation-thread__actions-desktop">{desktopActions}</span><span className="conversation-thread__actions-mobile">{mobileActions}</span></> : null}
          <Button variant="secondary" aria-label="Detalles del cliente" aria-pressed={detailOpen} onClick={() => setDetailOpen((open) => !open)}><Icon icon={Info} size="sm" /></Button>
          <Button variant="secondary" onClick={() => { window.location.href = pathForRoute({ view: "clients", clientId: conversation.customer_id }); }}><UserRound aria-hidden="true" />Cliente</Button>
        </div>
      </header> : null}
        {connection !== "connected" ? <p className="conversations-offline" role="status"><Icon icon={WifiOff} aria-hidden="true" /><strong>{connection === "reconnecting" ? "Reconectando la conexión en tiempo real." : "Sin conexión en tiempo real."}</strong><span>El histórico guardado sigue disponible.</span></p> : null}
       {state === "loading" ? null : !data || messages.length === 0 ? <EmptyState title="No hay registros" description="Esta conversación no tiene mensajes para mostrar." /> : <div className="conversation-workspace">
         <main className="ai-agent-grammar__main" aria-label="Conversación">
         <div className="conversation-thread__thread">
           <CollapsibleMessages total={data.messages_total ?? messages.length} expanded={messagesExpanded} onToggle={toggleMessages}>
         <section className="ai-agent-grammar__thread-area" aria-label="Mensajes de la conversación">
           <div className="ai-agent-grammar__bubbles">{messages.map((message, index) => {
             const day = message.created_at?.slice(0, 10) ?? null;
             const previousDay = index > 0 ? messages[index - 1]?.created_at?.slice(0, 10) ?? null : null;
             return <Fragment key={message.id}>
               {day && day !== previousDay ? <div className="conversation-thread__day" role="separator">{formatDay(day)}</div> : null}
               <MessageBubble message={message} customerId={conversation?.customer_id ?? 0} customerName={(id) => conversation?.customer?.name ?? customerName?.(id) ?? `Cliente #${id}`} />
             </Fragment>;
           })}</div>
          {liveActivity.length > 0 ? <div className="ai-agent-grammar__activity-list" aria-label="Actividad persistida">{liveActivity.map((activity, index) => <div className="ai-agent-grammar__activity" role="status" key={`${activity.event}-${index}`}><span aria-hidden="true">✦</span><span className="ai-agent-grammar__activity-chip">{activityText(activity)}</span></div>)}</div> : null}
         {!interactive ? <NoReplyNote /> : null}
         {conversation?.state === "human" ? <div className="ai-agent-grammar__handoff" aria-label="Traspaso a atención humana">La conversación está en atención humana.</div> : null}
         </section>
           </CollapsibleMessages>
         </div>
         {interactive ? <div className="ai-agent-grammar__composer-zone">
           {messages.filter((m) => m.delivery_status === "failed").map((m) => <Button key={m.id} variant="secondary" disabled={busy} onClick={() => void mutate(() => retryMessage(m.conversation_id, m.id))}>Reintentar entrega #{m.id}</Button>)}
           {conversation?.state === "human" ? <form className={`ai-agent-grammar__composer${windowOpen ? "" : " ai-agent-grammar__composer--locked"}`} aria-label="Responder a la conversación" onSubmit={(e) => { e.preventDefault(); if (conversationId && text.trim()) void mutate(() => sendMessage(conversationId, { text: text.trim() })); }}>
             {!windowOpen ? <p className="conversation-thread__window-note" role="status" aria-label="Fuera de la ventana de 24 horas"><Icon icon={Clock} aria-hidden="true" /> Fuera de la ventana de 24 horas · el envío no está disponible.</p> : null}
             <div className="ai-agent-grammar__composer-row"><div className="ai-agent-grammar__composer-field">{!windowOpen ? <Icon icon={Lock} aria-hidden="true" className="ai-agent-grammar__composer-lock" /> : null}<Textarea label="Respuesta" rows={windowOpen ? undefined : 1} placeholder={windowOpen ? undefined : "Respuesta no disponible"} value={text} disabled={!windowOpen || busy} onChange={(e) => setText(e.target.value)} /></div><Button type="submit" aria-label="Enviar respuesta" disabled={!windowOpen || busy || !text.trim()}><SendHorizonal aria-hidden="true" /></Button></div>
             <div className="conversation-thread__media-tools">
               <input ref={inputRef} className="conversation-thread__file-input" type="file" aria-label="Adjuntar archivo" accept="image/*,video/*,audio/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv" disabled={!windowOpen || busy} onChange={(event) => { setSelectedFile(event.target.files?.[0] ?? null); setCaption(""); event.currentTarget.value = ""; }} />
               <Button variant="secondary" aria-label="Adjuntar archivo" disabled={!windowOpen || busy} onClick={() => inputRef.current?.click()}><Paperclip aria-hidden="true" />Adjuntar</Button>
               {recording ? <><span role="timer" aria-label="Tiempo de grabación">{Math.floor(recordingSeconds / 60)}:{String(recordingSeconds % 60).padStart(2, "0")}</span><Button variant="secondary" aria-label="Cancelar grabación" disabled={busy} onClick={() => stopRecording(true)}>Cancelar</Button><Button aria-label="Detener y enviar audio" disabled={busy} onClick={() => stopRecording(false)}><Square aria-hidden="true" />Detener y enviar</Button></> : <Button variant="secondary" aria-label="Grabar audio" disabled={!windowOpen || busy || !supportedRecordingMime} title={!supportedRecordingMime ? "La grabación de audio no está disponible en este navegador." : undefined} onClick={() => void startRecording()}><Mic aria-hidden="true" />Grabar audio</Button>}
               {!supportedRecordingMime ? <span className="conversation-thread__recording-help">La grabación de audio no está disponible en este navegador.</span> : null}
             </div>
             {selectedFile ? <div className="conversation-thread__selected-file"><span>{selectedFile.name} · {(selectedFile.size / 1024).toFixed(1)} KB</span><Textarea label="Texto del archivo (opcional)" rows={2} value={caption} disabled={busy} onChange={(event) => setCaption(event.target.value)} /><Button disabled={!windowOpen || busy} onClick={() => sendSelectedFile(selectedFile, caption)}>Enviar archivo</Button></div> : null}
                        </form> : <div className="ai-agent-grammar__composer ai-agent-grammar__composer--locked">
             <p className="conversation-thread__window-note" role="status" aria-label="Fuera de la ventana de 24 horas"><Icon icon={Clock} aria-hidden="true" /> Fuera de la ventana de 24 horas · el envío no está disponible.</p>
             <div className="ai-agent-grammar__composer-row"><div className="ai-agent-grammar__composer-field"><Icon icon={Lock} aria-hidden="true" className="ai-agent-grammar__composer-lock" /><Textarea label="Respuesta" rows={1} placeholder="Respuesta no disponible" value="" disabled onChange={() => {}} /></div><Button aria-label="Enviar respuesta" disabled><SendHorizonal aria-hidden="true" /></Button></div>
             <p className="ai-agent-grammar__closed-note">{conversation?.state === "closed" ? "Conversación cerrada" : "Toma la conversación para responder."}</p>
           </div>}
           {mutationError && <p role="alert">La entrega falló: {mutationError}</p>}
         </div> : null}
           </main>{conversation ? <>
             {detailOpen ? <div className="conversation-thread__detail" role="dialog" aria-label="Detalles del cliente">
               <div className="conversation-thread__detail-head"><h2>Detalles del cliente</h2><Button variant="tertiary" aria-label="Cerrar detalles del cliente" onClick={() => setDetailOpen(false)}><X aria-hidden="true" /></Button></div>
               <ConversationContext conversation={conversation} />
             </div> : null}
           </> : null}</div>}
      {interactive && conversation && infoOpen ? <Dialog open onClose={() => setInfoOpen(false)} title="Información del chat" variant="sheet"><ConversationContext conversation={conversation} /></Dialog> : null}
    </PageFrame>;
}
