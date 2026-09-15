import { useCallback, useEffect, useState } from "react";
import { apiFetch, getAssistantCapabilities, postJson } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AssistantCapabilities, Settings as SettingsData } from "../../types";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { Textarea } from "../primitives/Textarea";
import { DataTable, tabularNum, type Column } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { PushSettings } from "./PushSettings";

export type SettingsState = AsyncDataState | "saved" | "saving" | "validation" | "server-error" | "stale";
export interface SettingsProps { data?: SettingsData | null; state?: SettingsState; onRetry?: () => void; capabilities?: AssistantCapabilities; }

function stateMessage(state: SettingsState) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando configuración" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title="No pudimos cargar la configuración" />;
  if (state === "saved") return <StateMessage tone="success" role="status" title="Configuración guardada" detail="Los cambios quedaron aplicados." />;
  if (state === "saving") return <StateMessage tone="info" role="status" spinner title="Guardando cambios" detail="Aplicando la configuración seleccionada." />;
  if (state === "validation") return <StateMessage tone="danger" role="alert" title="Sintaxis no válida" detail="Revisa las reglas avanzadas: cada línea debe tener categoría=mode con mode bot_resolve o always_escalate." />;
  if (state === "server-error") return <StateMessage tone="danger" role="alert" title="No pudimos guardar los cambios" detail="Ocurrió un error del servidor. Reintenta en unos minutos." />;
  if (state === "stale") return <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />;
  return null;
}

export function AssistantCapabilitiesView({ capabilities }: { capabilities: AssistantCapabilities }) {
  return (
    <Card title="Capacidades del asistente">
      <h3>Herramientas</h3>
      <ul>
        {capabilities.tools.map((tool) => (
          <li key={tool.name}>
            <strong>{tool.name}</strong>: {tool.description}{" "}
            <Badge tone={tool.read_only ? "neutral" : "warning"}>
              {tool.read_only ? "Solo lectura" : "Puede escribir"}
            </Badge>
          </li>
        ))}
      </ul>
      <h3>Configuración activa</h3>
      <p>Personas: {capabilities.personas.join(", ")}</p>
      <p>Prompts: {capabilities.prompts.join(", ")}</p>
      <p>
        {capabilities.kb_available ? "KB disponible" : "KB no disponible"} ·{" "}
        {capabilities.memory_available ? "Memoria disponible" : "Memoria no disponible"}
      </p>
    </Card>
  );
}

export function Settings({ data: controlledData, state: controlledState, onRetry, capabilities: controlledCapabilities }: SettingsProps = {}) {
  const fetchSettings = useCallback(() => apiFetch<SettingsData>("/panel/api/settings"), []);
  const fetched = useAsyncData(fetchSettings, controlledData === undefined);
  const fetchCapabilities = useCallback(() => getAssistantCapabilities(), []);
  const fetchedCapabilities = useAsyncData(fetchCapabilities, controlledCapabilities === undefined);
  const data = controlledData ?? fetched.data;
  const capabilities = controlledCapabilities ?? fetchedCapabilities.data;
  const capabilityData = capabilities && Array.isArray(capabilities.tools) && Array.isArray(capabilities.personas) && Array.isArray(capabilities.prompts)
    ? capabilities
    : null;
  const pageState = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const [scope, setScope] = useState(() => data ? Object.entries(data.scope_rules).sort(([a], [b]) => a.localeCompare(b)).map(([category, mode]) => `${category}=${mode}`).join("\n") : "");
  const [keywords, setKeywords] = useState(() => data?.keywords.join("\n") ?? "");
  const [tone, setTone] = useState(() => data?.tone ?? "");
  const [conversationLimit, setConversationLimit] = useState(() => String(data?.conversation_limit ?? ""));
  const [dailyLimit, setDailyLimit] = useState(() => String(data?.daily_limit ?? ""));
  const [metaCost, setMetaCost] = useState(() => String(data?.meta_cost ?? ""));
  const [saveState, setSaveState] = useState<SettingsState | null>(null);
  const save = async (path: string, body: unknown) => {
    setSaveState("saving");
    try { await postJson(path, body); setSaveState("saved"); }
    catch { setSaveState("server-error"); }
  };
  const saveScope = () => {
    const rules: Record<string, string> = {};
    for (const line of scope.split("\n").map((value) => value.trim()).filter(Boolean)) {
      const [category, mode] = line.split("=").map((value) => value.trim());
      if (!category || !["bot_resolve", "always_escalate"].includes(mode)) { setSaveState("validation"); return; }
      rules[category] = mode;
    }
    void save("/panel/api/settings/scope", { rules });
  };
  const snapshot = data?.snapshot;
  const columns: Column<{ label: string; value: string }>[] = [
    { key: "label", header: "Fecha", render: (row) => row.label },
    { key: "daily_spend", header: "Gasto diario", render: (row) => tabularNum(row.value), align: "right" },
  ];
  const spendRows = snapshot ? [
    { label: snapshot.date, value: `$${snapshot.daily_spend.toFixed(4)}` },
    { label: "Límite diario", value: `$${snapshot.daily_limit.toFixed(2)}` },
    { label: "% del límite", value: `${snapshot.daily_percent.toFixed(1)}%` },
  ] : [];
  const state = saveState ?? pageState;
  const retry = onRetry ?? fetched.retry;
  const capabilityState = controlledCapabilities ? "ready" : fetchedCapabilities.state;
  const capabilityHost = capabilityState === "loading"
    ? <Card title="Capacidades del asistente"><StateMessage tone="info" role="status" spinner title="Cargando capacidades del asistente" /></Card>
    : capabilityState === "error" || capabilityState === "denied"
      ? <Card title="Capacidades del asistente"><StateMessage tone="danger" role="alert" title="No pudimos cargar las capacidades del asistente" /></Card>
      : capabilityData ? <AssistantCapabilitiesView capabilities={capabilityData} /> : null;
  useEffect(() => {
    if (!data) return;
    setScope(Object.entries(data.scope_rules).sort(([a], [b]) => a.localeCompare(b)).map(([category, mode]) => `${category}=${mode}`).join("\n"));
    setKeywords(data.keywords.join("\n"));
    setTone(data.tone);
    setConversationLimit(String(data.conversation_limit));
    setDailyLimit(String(data.daily_limit));
    setMetaCost(String(data.meta_cost));
  }, [data]);
  if (!data || state === "loading" || state === "error" || state === "denied") return <PageFrame title="Configuración" meta="Preferencias globales del asistente" state={stateMessage(state)}>{null}</PageFrame>;
  return <PageFrame title="Configuración" meta="Preferencias globales del asistente" state={stateMessage(state)}>
    <Card title="Alcance del agente"><p>Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona.</p><details><summary>Sintaxis avanzada · categoría=mode</summary><p>Formato técnico: una regla por línea con categoría=mode, donde mode es bot_resolve o always_escalate. No lo cambies sin conocer el efecto en las respuestas.</p></details><Textarea label="Reglas de alcance" rows={4} value={scope} onChange={(event) => setScope(event.target.value)} /><Button variant="secondary" onClick={saveScope}>Guardar alcance</Button></Card>
    <Card title="Detección de emergencias"><p>Palabras que activan un aviso de emergencia. Se detectan en el próximo mensaje entrante.</p><Textarea label="Palabras clave de emergencia" rows={6} value={keywords} onChange={(event) => setKeywords(event.target.value)} /><Button variant="secondary" onClick={() => void save("/panel/api/settings/keywords", { keywords: keywords.split("\n").map((value) => value.trim()).filter(Boolean) })}>Guardar palabras clave</Button></Card>
    <Card title="Tono"><p>Define cómo suenan las respuestas del agente en cada conversación.</p><Input label="Tono" value={tone} onChange={(event) => setTone(event.target.value)} /><Button variant="secondary" onClick={() => void save("/panel/api/settings/tone", { tone })}>Guardar tono</Button></Card>
    <Card title="Límites de gasto"><p>Topes de gasto por conversación y por día. Al 80% el agente se vuelve más conservador; al 100% se detienen las llamadas de pago y la conversación pasa a una persona.</p><Input label="Límite por conversación (USD)" type="number" value={conversationLimit} onChange={(event) => setConversationLimit(event.target.value)} /><Input label="Límite diario (USD)" type="number" value={dailyLimit} onChange={(event) => setDailyLimit(event.target.value)} /><Button variant="secondary" onClick={() => void save("/panel/api/settings/limits", { conversation_limit: Number(conversationLimit), daily_limit: Number(dailyLimit) })}>Guardar límites</Button></Card>
    <Card title="Precio Meta"><p>Costo por mensaje de servicio (USD), vigente desde 2026-10-01.</p><Input label="Costo por mensaje (USD)" type="number" value={metaCost} onChange={(event) => setMetaCost(event.target.value)} /><Button variant="secondary" onClick={() => void save("/panel/api/settings/meta", { service_message_cost: Number(metaCost) })}>Guardar precio</Button></Card>
     <Card title="Gasto actual"><DataTable columns={columns} rows={spendRows} rowKey={(row) => row.label} />{snapshot?.conversation_percent !== null ? <p>Conversación {snapshot?.conversation_percent}% de ${snapshot?.conversation_limit.toFixed(2)}</p> : null}</Card>
     <Card title="Notificaciones push"><PushSettings embedded /></Card>
     {capabilityHost}
    {state === "empty" ? <Button onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
