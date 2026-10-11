import { Archive, FolderPlus, GitMerge, Globe, Link2, Pencil, Wrench, Zap, type LucideIcon } from "lucide-react";

export interface AssistantToolLabel {
  label: string;
  description?: string;
  group: string;
  icon: LucideIcon;
}

const labels: Record<string, AssistantToolLabel> = {
  "web.search": { label: "Buscar en la web", description: "Consulta información actualizada", group: "Consultar información", icon: Globe },
  "web.fetch": { label: "Consultar una URL", description: "Lee el contenido de un enlace", group: "Consultar información", icon: Link2 },
  "automation.create_rule": { label: "Crear automatización", description: "Automatiza tareas recurrentes", group: "Acciones del asistente", icon: Zap },
  "project.create": { label: "Crear proyecto", description: "Organiza tu trabajo en un nuevo proyecto", group: "Acciones del asistente", icon: FolderPlus },
  "project.rename": { label: "Renombrar proyecto", description: "Cambia el nombre de un proyecto", group: "Acciones del asistente", icon: Pencil },
  "project.archive": { label: "Archivar proyecto", description: "Archiva un proyecto", group: "Acciones del asistente", icon: Archive },
  "project.merge": { label: "Fusionar proyectos", description: "Combina dos proyectos", group: "Acciones del asistente", icon: GitMerge },
};

export function assistantToolLabel(name: string): AssistantToolLabel {
  return labels[name] ?? { label: name, group: "Otras", icon: Wrench };
}
