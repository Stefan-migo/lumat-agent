import { useEffect, useState } from "react";
import { ApiError, createChatThread, getChatThread, listActiveConversations, listConversations, sendChatMessage } from "../../api";
import type { InternalChatMessage, InternalChatThread } from "../../types";
import { Avatar } from "../primitives/Avatar";
import { Button } from "../primitives/Button";
import { Textarea } from "../primitives/Textarea";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { realtimeClient, type ConnectionStatus } from "../../realtime";

export function AgentChat() {
  const [thread, setThread] = useState<InternalChatThread | null>(null);
  const [messages, setMessages] = useState<InternalChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [stream, setStream] = useState("");

  useEffect(() => {
    void createChatThread().then((result) => {
      setThread(result.thread);
      setMessages(result.messages);
    }).catch((reason: unknown) => setError(reason instanceof ApiError ? reason.detail : "No pudimos abrir el chat")).finally(() => setLoading(false));
  }, []);

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
    setProcessing(true);
    setError(null);
    try {
      const result = await sendChatMessage(thread.id, submitted);
      setMessages((current) => [...current, result.message]);
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
    } finally {
      setProcessing(false);
    }
  };

  const state = loading ? <StateMessage tone="info" role="status" spinner title="Cargando chat" /> : error ? <StateMessage tone="danger" role="alert" title={error} /> : null;
  const canRenderThread = !loading && thread !== null;
  const composerDisabled = loading || processing || thread === null;
  return <PageFrame title="Asistente Lumat" meta="Chat interno con el agente virtual." state={state}>
     <div className="ai-agent-grammar__thread-area" aria-label="Mensajes del chat interno" aria-live="polite">
       {connection !== "connected" && <p role="status">Conexión en tiempo real: {connection === "reconnecting" ? "reconectando" : "desconectada"}.</p>}
      {canRenderThread && messages.length === 0 && !error ? <StateMessage tone="info" role="status" title="Chat interno vacío" detail="Escribe un mensaje para iniciar la conversación." /> : null}
       {canRenderThread && processing ? <StateMessage tone="info" role="status" title="Procesando respuesta" /> : null}
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
      <div className="ai-agent-grammar__composer-actions">
        <Button onClick={() => void send()} disabled={composerDisabled || !content.trim()}>Enviar</Button>
      </div>
    </div>
  </PageFrame>;
}
