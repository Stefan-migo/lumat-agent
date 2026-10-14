import { useCallback, useState } from "react";
import { getChatbotMetrics, getChatbotSignalConversations } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { ChatbotSignalConversations } from "../../types";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { Button } from "../primitives/Button";
import "./ChatbotMetrics.css";

const WINDOW_OPTIONS = [7, 30] as const;

const SIGNALS: ReadonlyArray<{ key: string; label: string }> = [
  { key: "unknown_intent", label: "Intención no reconocida" },
  { key: "kb_miss", label: "Sin respuesta en la base" },
  { key: "escalation", label: "Derivaciones" },
];

function percent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function decimal(value: number | null, digits = 1): string {
  return value === null ? "—" : value.toFixed(digits);
}

export interface ChatbotMetricsProps {
  /** Opens an existing conversation thread (wired to the conversations route). */
  onOpenConversation?: (conversationId: number) => void;
}

export function ChatbotMetrics({ onOpenConversation }: ChatbotMetricsProps) {
  const [windowDays, setWindowDays] = useState<number>(WINDOW_OPTIONS[0]);
  const [signal, setSignal] = useState<string | null>(null);

  const metricsFetcher = useCallback(() => getChatbotMetrics(windowDays), [windowDays]);
  // `useAsyncData` only refetches when `enabled`/`refreshKey` change, so the window
  // must be part of the key for the selector to reload the data.
  const metrics = useAsyncData(metricsFetcher, true, windowDays);

  const drilldownFetcher = useCallback(() => {
    if (!signal) return Promise.resolve<ChatbotSignalConversations | null>(null);
    return getChatbotSignalConversations(signal, windowDays);
  }, [signal, windowDays]);
  const signalIndex = signal === null ? 0 : SIGNALS.findIndex((item) => item.key === signal) + 1;
  const drilldown = useAsyncData(drilldownFetcher, signal !== null, windowDays * 10 + signalIndex);

  const data = metrics.data;
  const ready = metrics.state === "ready" && data !== null;

  const stateContent =
    metrics.state === "loading" ? (
      <StateMessage tone="info" role="status" spinner title="Cargando métricas del bot" />
    ) : metrics.state === "denied" ? (
      <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />
    ) : metrics.state === "error" ? (
      <StateMessage tone="danger" role="alert" title="No pudimos cargar las métricas del bot" />
    ) : undefined;

  return (
    <PageFrame
      title="Métricas del bot"
      meta={ready && data ? `Últimos ${data.window_days} días` : "Rendimiento del asistente"}
      state={stateContent}
    >
      {ready && data ? (
        <section className="chatbot-metrics" aria-label="Métricas del bot">
          <div className="chatbot-metrics__toolbar" role="group" aria-label="Ventana de tiempo">
            {WINDOW_OPTIONS.map((days) => (
              <Button
                key={days}
                variant={windowDays === days ? "primary" : "tertiary"}
                aria-pressed={windowDays === days}
                onClick={() => setWindowDays(days)}
              >
                {days} días
              </Button>
            ))}
          </div>

          <div className="chatbot-metrics__kpis">
            <figure className="chatbot-metrics__kpi">
              <figcaption>Conversaciones</figcaption>
              <strong>{data.conversations}</strong>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>Contención</figcaption>
              <strong>{percent(data.containment_rate)}</strong>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>Derivaciones a humano</figcaption>
              <strong>{data.handoffs}</strong>
              <span>{percent(data.handoff_rate)}</span>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>Intenciones no reconocidas</figcaption>
              <strong>{data.unknown_intents}</strong>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>KB hits</figcaption>
              <strong>{data.kb_hits}</strong>
              <span>{percent(data.kb_hit_rate)}</span>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>KB misses</figcaption>
              <strong>{data.kb_misses}</strong>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>Turnos hasta resolver</figcaption>
              <strong>{decimal(data.turns_to_resolve)}</strong>
            </figure>
            <figure className="chatbot-metrics__kpi">
              <figcaption>Costo por conversación</figcaption>
              <strong>
                {data.cost_per_conversation === null
                  ? "—"
                  : `$${data.cost_per_conversation.toFixed(2)}`}
              </strong>
            </figure>
          </div>

          <div className="chatbot-metrics__signals">
            <h3>Conversaciones por señal</h3>
            <div className="chatbot-metrics__signal-buttons" role="group" aria-label="Señales de falla">
              {SIGNALS.map(({ key, label }) => (
                <Button
                  key={key}
                  variant={signal === key ? "primary" : "tertiary"}
                  aria-pressed={signal === key}
                  onClick={() => setSignal((current) => (current === key ? null : key))}
                >
                  {label}
                </Button>
              ))}
            </div>

            {signal === null ? null : drilldown.state === "loading" ? (
              <StateMessage tone="info" role="status" spinner title="Cargando conversaciones" />
            ) : drilldown.state === "error" ? (
              <StateMessage tone="danger" role="alert" title="No pudimos cargar las conversaciones" />
            ) : (drilldown.data?.conversations.length ?? 0) === 0 ? (
              <p role="status">Sin conversaciones para esta señal en la ventana.</p>
            ) : (
              <table className="chatbot-metrics__table">
                <caption className="chatbot-metrics__caption">
                  {`Conversaciones con la señal "${
                    SIGNALS.find((item) => item.key === signal)?.label ?? signal
                  }"`}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Conversación</th>
                    <th scope="col">Cliente</th>
                    <th scope="col">Señales</th>
                    <th scope="col">Último mensaje</th>
                    <th scope="col">Abrir</th>
                  </tr>
                </thead>
                <tbody>
                  {drilldown.data?.conversations.map((row) => (
                    <tr key={row.conversation_id}>
                      <td>#{row.conversation_id}</td>
                      <td>{row.wa_phone ?? `Cliente #${row.customer_id}`}</td>
                      <td>{`${row.signals.escalation} / ${row.signals.unknown_intent} / ${row.signals.kb_miss}`}</td>
                      <td>{row.last_message_at ?? "—"}</td>
                      <td>
                        <Button
                          variant="tertiary"
                          onClick={() => onOpenConversation?.(row.conversation_id)}
                        >
                          Abrir
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      ) : null}
    </PageFrame>
  );
}
