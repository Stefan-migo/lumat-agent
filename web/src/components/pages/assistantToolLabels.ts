export interface AssistantToolLabel {
  label: string;
  description?: string;
  group: string;
}

const labels: Record<string, AssistantToolLabel> = {
  "web.search": { label: "Buscar en la web", description: "Consulta información actualizada", group: "Consultar información" },
  "web.fetch": { label: "Consultar una URL", description: "Lee el contenido de un enlace", group: "Consultar información" },
  "automation.create_rule": { label: "Crear automatización", description: "Automatiza tareas recurrentes", group: "Acciones del asistente" },
  "project.create": { label: "Crear proyecto", description: "Organiza tu trabajo en un nuevo proyecto", group: "Acciones del asistente" },
  "project.rename": { label: "Renombrar proyecto", description: "Cambia el nombre de un proyecto", group: "Acciones del asistente" },
  "project.archive": { label: "Archivar proyecto", description: "Archiva un proyecto", group: "Acciones del asistente" },
  "project.merge": { label: "Fusionar proyectos", description: "Combina dos proyectos", group: "Acciones del asistente" },
};

export function assistantToolLabel(name: string): AssistantToolLabel {
  return labels[name] ?? { label: name, group: "Otras" };
}
