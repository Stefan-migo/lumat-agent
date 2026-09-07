import type { Meta, StoryObj } from "@storybook/react";
import { Avatar } from "../../components/primitives/Avatar";
import { Button } from "../../components/primitives/Button";
import { StatusBadge } from "../../components/primitives/StatusBadge";
import { Textarea } from "../../components/primitives/Textarea";

type Scenario = "emergencia" | "visita";
type ComposerState = "enabled" | "processing" | "disabled_window" | "disabled_not_taken";

const navItems = ["Panel", "Clientes", "Conversaciones", "Casos", "Notificaciones", "Asistente Lumat"];
const adminItems = ["Base de conocimientos", "Configuración"];
const activeThreads = [
  { name: "María González", status: "human" as const, label: "Atención humana" },
  { name: "Pedro Soto", status: "bot" as const, label: "Agente atendiendo" },
  { name: "Casa López", status: "bot" as const, label: "Agente atendiendo" },
];

function Activity({ children }: { children: string }) {
  return <div className="ai-agent-grammar__activity" role="status"><span aria-hidden="true">✦</span><span className="ai-agent-grammar__activity-chip">{children}</span></div>;
}

function Message({ outbound, name, time, children }: { outbound?: boolean; name: string; time: string; children: string }) {
  return <div className={`ai-agent-grammar__bubble-row${outbound ? " ai-agent-grammar__bubble-row--outbound" : ""}`} data-bubble aria-label={`Mensaje de ${name}`}>
    {!outbound ? <Avatar name={name} /> : null}
    <div className={`ai-agent-grammar__bubble${outbound ? " ai-agent-grammar__bubble--outbound" : ""}`}>
      <span className="ai-agent-grammar__message-meta">{name}</span>{children}<span className="ai-agent-grammar__message-time">{time}</span>
    </div>
    {outbound ? <Avatar name={name} /> : null}
  </div>;
}

export function AiAgentGrammarView({ railExpanded, inspectorVisible, scenario, composerState }: {
  railExpanded: boolean; inspectorVisible: boolean; scenario: Scenario; composerState: ComposerState;
}) {
  const emergency = scenario === "emergencia";
  const disabled = composerState !== "enabled";
  const reason = composerState === "processing" ? "Procesando respuesta" : composerState === "disabled_window" ? "Fuera de la ventana de 24 horas" : composerState === "disabled_not_taken" ? "Toma la conversación para responder" : undefined;
  return <div className="ai-agent-grammar">
    <div className={`ai-agent-grammar__shell${railExpanded ? "" : " ai-agent-grammar__shell--compact"}${inspectorVisible ? "" : " ai-agent-grammar__shell--wide"}`}>
      <aside className="ai-agent-grammar__rail" aria-label="Navegación principal">
        <div className="ai-agent-grammar__brand"><span className="ai-agent-grammar__facet" aria-hidden="true" /><span className="ai-agent-grammar__brand-label">Lumat</span></div>
        <nav className="ai-agent-grammar__nav" aria-label="Secciones del panel">{navItems.map((item) => <a key={item} href="#" aria-current={item === "Conversaciones" ? "page" : undefined}>{railExpanded ? item : item.slice(0, 1)}</a>)}</nav>
        {railExpanded ? <>
          <section aria-labelledby="active-conversations"><h2 id="active-conversations" className="ai-agent-grammar__section-label">Conversaciones activas</h2><div className="ai-agent-grammar__thread-list">{activeThreads.map((thread, index) => <div key={thread.name} className={`ai-agent-grammar__thread${index === 0 ? " ai-agent-grammar__thread--active" : ""}`} aria-current={index === 0 ? "page" : undefined}><span className="ai-agent-grammar__thread-name">{thread.name}</span><StatusBadge status={thread.status} label={thread.label} /></div>)}</div></section>
          <nav className="ai-agent-grammar__nav ai-agent-grammar__admin" aria-label="Administración">{adminItems.map((item) => <a key={item} href="#">{item}</a>)}</nav>
          <footer className="ai-agent-grammar__footer"><strong>Dueño (admin)</strong><span>Cerrar sesión</span></footer>
        </> : null}
      </aside>
      <main className="ai-agent-grammar__main" aria-label="Conversación con María González">
        <header className="ai-agent-grammar__header"><h1 className="ai-agent-grammar__title">Conversación · María González</h1><StatusBadge status="human" label="Atención humana" /><span className="ai-agent-grammar__freshness">Actualizado hace 30 s</span><span className={`ai-agent-grammar__window${composerState === "disabled_window" ? " ai-agent-grammar__window--closed" : ""}`}>{composerState === "disabled_window" ? "Fuera de la ventana de 24 horas" : "Respuesta disponible"}</span></header>
        <section className="ai-agent-grammar__thread-area" aria-label="Mensajes de la conversación">
          <Message name="María González" time="14:32">{emergency ? "Hola, tengo una fuga de agua bajo el lavaplatos y está saliendo bastante. ¿Me pueden ayudar?" : "Hola, necesito solicitar una visita para revisar la calefacción. ¿Qué disponibilidad tienen?"}</Message>
          {emergency ? <><Activity>Lumat clasificó la solicitud</Activity><Activity>Detectó emergencia probable</Activity><Activity>Consultó la base de conocimientos</Activity><Activity>Derivó a atención humana</Activity></> : <Activity>Lumat consultó la base de conocimientos · Creó una solicitud de visita</Activity>}
          <Message outbound name="Lumat" time="14:32">{emergency ? "María, lamento la situación. Ya avisamos al equipo para que te contacten a la brevedad. Si puedes hacerlo de forma segura, cierra la llave de paso del agua." : "María, podemos coordinar una visita desde $35.000. Hay disponibilidad esta semana; dejaré creada la solicitud para confirmar el horario."}</Message>
          {emergency ? <><div className="ai-agent-grammar__handoff">Rodrigo tomó la conversación · 14:40</div><Message outbound name="Rodrigo" time="14:40">María, soy Rodrigo del equipo técnico. ¿Pudiste cerrar la llave de paso? Así coordinamos la visita.</Message><Message name="María González" time="14:41">Sí, ya la cerré. ¿Cuándo podría venir alguien?</Message></> : <Message name="María González" time="14:35">Perfecto, gracias. Ojalá pueda ser durante la tarde.</Message>}
          {composerState === "processing" ? <div className="ai-agent-grammar__processing" role="status" aria-label="Procesando respuesta">Procesando respuesta</div> : null}
        </section>
        <form className="ai-agent-grammar__composer" aria-label="Responder a la conversación"><span className={`ai-agent-grammar__composer-hint${disabled ? " ai-agent-grammar__composer-hint--muted" : ""}`}>{composerState === "enabled" ? "Respuesta disponible · Ventana de 24 h abierta" : reason}</span><Textarea label="Respuesta" disabled={disabled} placeholder="Escribe una respuesta…" /><div className="ai-agent-grammar__composer-actions"><Button disabled={disabled}>Enviar respuesta</Button>{reason ? <span className="ai-agent-grammar__reason">{reason}</span> : null}</div></form>
      </main>
      {inspectorVisible ? <aside className="ai-agent-grammar__inspector" aria-label="Inspector operacional">
        <section><h2>Cliente</h2><strong>María González</strong><dl><div className="ai-agent-grammar__detail"><dt>Teléfono</dt><dd>+56 9 …</dd></div><div className="ai-agent-grammar__detail"><dt>Estado</dt><dd>Activo</dd></div><div className="ai-agent-grammar__detail"><dt>Consentimiento</dt><dd>Consentimiento registrado</dd></div></dl></section>
        <section><h2>Caso activo</h2><dl>
            <div className="ai-agent-grammar__detail"><dt>Servicio</dt><dd>{emergency ? "Urgencia gasfitería" : "Revisión de calefacción"}</dd></div>
            <div className="ai-agent-grammar__detail"><dt>Prioridad</dt><dd>{emergency ? <StatusBadge status="escalated" label="Alta" /> : "Normal"}</dd></div>
            <div className="ai-agent-grammar__detail"><dt>Estado</dt><dd>{emergency ? "Escalado" : "Abierto"}</dd></div>
            <div className="ai-agent-grammar__detail"><dt>Responsable</dt><dd>Rodrigo T.</dd></div>
          </dl>{emergency ? <Button variant="secondary" className="emergency-action">Reconocer emergencia</Button> : <span className="ai-agent-grammar__composer-hint">Solicitud de visita creada</span>}</section>
        <section><h2>Memoria</h2><div className="ai-agent-grammar__chips"><span className="ai-agent-grammar__chip">Cliente frecuente</span><span className="ai-agent-grammar__chip">Prefiere horario tarde</span><span className="ai-agent-grammar__chip">Fuga de agua en 2025</span></div></section>
        <section><h2>Acciones</h2><div className="ai-agent-grammar__actions"><Button>Tomar conversación</Button><Button variant="secondary">Devolver al agente</Button><Button variant="secondary">Cerrar conversación</Button></div></section>
      </aside> : null}
    </div>
  </div>;
}

const meta = { title: "Concepto/Gramática AI Agent", component: AiAgentGrammarView, parameters: { layout: "fullscreen", viewport: { defaultViewport: "responsive" } }, argTypes: {
  railExpanded: { control: "boolean" }, inspectorVisible: { control: "boolean" }, scenario: { control: "select", options: ["emergencia", "visita"] }, composerState: { control: "select", options: ["enabled", "processing", "disabled_window", "disabled_not_taken"] },
} } satisfies Meta<typeof AiAgentGrammarView>;

export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = { args: { railExpanded: true, inspectorVisible: true, scenario: "emergencia", composerState: "enabled" } };
