import type { Meta, StoryObj } from "@storybook/react";
import { Avatar } from "../../components/primitives/Avatar";
import { Button } from "../../components/primitives/Button";
import { StatusBadge } from "../../components/primitives/StatusBadge";
import { Textarea } from "../../components/primitives/Textarea";

type Scenario = "emergencia" | "visita";
type ComposerState = "enabled" | "streaming" | "disabled_window" | "disabled_not_taken";

const navItems = ["Panel", "Clientes", "Conversaciones", "Casos", "Notificaciones", "Asistente Lumat"];
const adminItems = ["Base de conocimientos", "Configuración"];
const activeThreads = [
  { name: "María González", status: "human" as const, label: "Atención humana" },
  { name: "Pedro Soto", status: "bot" as const, label: "Agente atendiendo" },
  { name: "Casa López", status: "bot" as const, label: "Agente atendiendo" },
];

const styles = `
  .ai-agent-grammar { min-height: 100vh; background: var(--bg); color: var(--text); font-family: var(--font-sans); }
  .ai-agent-grammar *, .ai-agent-grammar *::before, .ai-agent-grammar *::after { box-sizing: border-box; }
  .ai-agent-grammar__shell { display: grid; grid-template-columns: 15rem minmax(0, 1fr) 18rem; min-height: 100vh; }
  .ai-agent-grammar__shell--compact { grid-template-columns: 4rem minmax(0, 1fr) 18rem; }
  .ai-agent-grammar__shell--wide { grid-template-columns: 15rem minmax(0, 1fr); }
  .ai-agent-grammar__rail { display: flex; flex-direction: column; gap: var(--space-5); padding: var(--space-4) var(--space-3); background: var(--primary-800); color: var(--surface); }
  .ai-agent-grammar__brand { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-lg); font-weight: var(--weight-bold); }
  .ai-agent-grammar__facet { width: var(--space-2); height: var(--space-8); background: var(--brand-lime); border-radius: var(--radius-sm); }
  .ai-agent-grammar__nav { display: grid; gap: var(--space-1); }
  .ai-agent-grammar__nav a { display: block; padding: var(--space-2); color: var(--surface); border-radius: var(--radius-sm); text-decoration: none; font-size: var(--text-sm); }
  .ai-agent-grammar__nav a[aria-current="page"] { border-left: var(--space-1) solid var(--brand-lime); padding-left: var(--space-1); background: var(--primary-100); color: var(--primary-800); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__admin { padding-top: var(--space-3); border-top: 1px solid var(--primary-700); }
  .ai-agent-grammar__section-label { margin: 0 0 var(--space-2); color: var(--primary-200); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__thread-list { display: grid; gap: var(--space-1); }
  .ai-agent-grammar__thread { display: grid; gap: var(--space-1); padding: var(--space-2); border: 1px solid transparent; border-radius: var(--radius-sm); color: var(--surface); text-align: left; }
  .ai-agent-grammar__thread--active { border-left: var(--space-1) solid var(--brand-lime); background: var(--primary-700); }
  .ai-agent-grammar__thread-name { font-size: var(--text-sm); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__thread-status { color: var(--primary-200); font-size: var(--text-xs); }
  .ai-agent-grammar__footer { display: grid; gap: var(--space-2); margin-top: auto; padding-top: var(--space-3); border-top: 1px solid var(--primary-700); font-size: var(--text-xs); }
  .ai-agent-grammar__main { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; min-width: 0; }
  .ai-agent-grammar__header { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--border); background: var(--surface); }
  .ai-agent-grammar__title { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__freshness { color: var(--text-muted); font-size: var(--text-xs); }
  .ai-agent-grammar__window { margin-left: auto; color: var(--success); font-size: var(--text-sm); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__window--closed { color: var(--danger); }
  .ai-agent-grammar__composer-hint--muted { color: var(--text-muted); }
  .ai-agent-grammar__thread-area { display: grid; align-content: start; gap: var(--space-4); max-width: 52rem; width: 100%; margin: 0 auto; padding: var(--space-5); }
  .ai-agent-grammar__bubble-row { display: flex; gap: var(--space-2); }
  .ai-agent-grammar__bubble-row--outbound { justify-content: flex-end; }
  .ai-agent-grammar__bubble { max-width: 75%; padding: var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface); }
  .ai-agent-grammar__bubble--outbound { border-color: var(--primary-800); background: var(--primary-800); color: var(--surface); }
  .ai-agent-grammar__message-meta { display: block; margin-bottom: var(--space-1); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__message-time { display: block; margin-top: var(--space-2); font-size: var(--text-xs); opacity: .8; }
  .ai-agent-grammar__activity { display: flex; align-items: center; justify-content: center; gap: var(--space-2); color: var(--info); font-size: var(--text-xs); text-align: center; }
  .ai-agent-grammar__activity-chip { padding: var(--space-1) var(--space-2); border: 1px solid var(--brand-aqua); border-radius: var(--radius-sm); background: var(--info-tint); }
  .ai-agent-grammar__handoff { padding: var(--space-2); border-top: 1px solid var(--warning-border); border-bottom: 1px solid var(--warning-border); color: var(--warning); font-size: var(--text-xs); text-align: center; }
  .ai-agent-grammar__streaming { display: flex; justify-content: center; color: var(--info); font-size: var(--text-sm); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__composer { display: grid; gap: var(--space-2); padding: var(--space-4) var(--space-5); border-top: 1px solid var(--border); background: var(--surface); }
  .ai-agent-grammar__composer-hint { color: var(--success); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__composer-actions { display: flex; align-items: center; gap: var(--space-3); }
  .ai-agent-grammar__reason { color: var(--text-muted); font-size: var(--text-sm); }
  .ai-agent-grammar__inspector { display: grid; align-content: start; gap: var(--space-4); padding: var(--space-4); border-left: 1px solid var(--border); background: var(--surface); }
  .ai-agent-grammar__inspector section { display: grid; gap: var(--space-2); padding-bottom: var(--space-4); border-bottom: 1px solid var(--border); }
  .ai-agent-grammar__inspector h2 { margin: 0; font-size: var(--text-md); font-weight: var(--weight-semibold); }
  .ai-agent-grammar__detail { display: flex; justify-content: space-between; gap: var(--space-2); font-size: var(--text-sm); }
  .ai-agent-grammar__detail dt { color: var(--text-muted); }
  .ai-agent-grammar__detail dd { margin: 0; text-align: right; }
  .ai-agent-grammar__chips { display: flex; flex-wrap: wrap; gap: var(--space-1); }
  .ai-agent-grammar__chip { padding: var(--space-1) var(--space-2); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-muted); font-size: var(--text-xs); }
  .ai-agent-grammar__actions { display: grid; gap: var(--space-2); }
  .ai-agent-grammar .emergency-action { color: var(--danger); border-color: var(--danger-border); }
  @media (max-width: 64rem) { .ai-agent-grammar__shell, .ai-agent-grammar__shell--compact { grid-template-columns: 4rem minmax(0, 1fr); } .ai-agent-grammar__inspector { display: none; } .ai-agent-grammar__brand-label, .ai-agent-grammar__rail .ai-agent-grammar__section-label, .ai-agent-grammar__rail .ai-agent-grammar__thread-list, .ai-agent-grammar__footer { display: none; } .ai-agent-grammar__nav a { text-align: center; } }
  @media (max-width: 40rem) { .ai-agent-grammar__shell, .ai-agent-grammar__shell--compact { display: block; } .ai-agent-grammar__rail { min-height: auto; } .ai-agent-grammar__nav { display: flex; overflow-x: auto; } .ai-agent-grammar__nav a { white-space: nowrap; } .ai-agent-grammar__thread-area, .ai-agent-grammar__composer { padding: var(--space-3); } .ai-agent-grammar__bubble { max-width: 90%; } }
`;

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
  const reason = composerState === "streaming" ? "Esperando respuesta del agente" : composerState === "disabled_window" ? "Fuera de la ventana de 24 horas" : composerState === "disabled_not_taken" ? "Toma la conversación para responder" : undefined;
  return <div className="ai-agent-grammar">
    <style>{styles}</style>
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
          {composerState === "streaming" ? <div className="ai-agent-grammar__streaming" role="status">Lumat está escribiendo…</div> : null}
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

const meta = { title: "Concepto/Gramática AI Agent", component: AiAgentGrammarView, parameters: { layout: "fullscreen" }, argTypes: {
  railExpanded: { control: "boolean" }, inspectorVisible: { control: "boolean" }, scenario: { control: "select", options: ["emergencia", "visita"] }, composerState: { control: "select", options: ["enabled", "streaming", "disabled_window", "disabled_not_taken"] },
} } satisfies Meta<typeof AiAgentGrammarView>;

export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = { args: { railExpanded: true, inspectorVisible: true, scenario: "emergencia", composerState: "enabled" } };
