import { useEffect, useState } from "react";
import { ApiError, createChatThread, getChatThread, sendChatMessage } from "../../api";
import type { InternalChatMessage, InternalChatThread } from "../../types";
import { Button } from "../primitives/Button";
import { Textarea } from "../primitives/Textarea";
import { PageFrame } from "../../stories/pages/_shared/PageFrame";
import { StateMessage } from "../../stories/pages/_shared/StateMessage";

export function AgentChat() {
  const [thread, setThread] = useState<InternalChatThread | null>(null);
  const [messages, setMessages] = useState<InternalChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void createChatThread().then((result) => {
      setThread(result.thread);
      setMessages(result.messages);
    }).catch((reason: unknown) => setError(reason instanceof ApiError ? reason.detail : "No pudimos abrir el chat")).finally(() => setLoading(false));
  }, []);

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
  return <PageFrame title="Asistente Lumat" meta="Chat interno con el agente virtual." state={state}>
    <div aria-live="polite">
      {messages.length === 0 && !loading ? <p>No hay mensajes todavía</p> : messages.map((message) => <article key={message.id} aria-label={`Mensaje de ${message.author === "agent" ? "agente" : "administrador"}`}>
        <strong>{message.author === "agent" ? "Agente Lumat" : "Administrador"}</strong>
        <p>{message.content}</p>
        {message.status === "failed" ? <button type="button" onClick={() => setContent(message.content)}>Reintentar</button> : null}
      </article>)}
    </div>
    <Textarea label="Mensaje" value={content} onChange={(event) => setContent(event.target.value)} disabled={loading || processing} placeholder="Escribe tu mensaje al asistente..." />
    <Button onClick={() => void send()} disabled={loading || processing || !content.trim()}>Enviar</Button>
  </PageFrame>;
}
