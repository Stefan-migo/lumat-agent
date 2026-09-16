import { Tabs } from "../primitives/Tabs";

export type AssistantView = "chat" | "projects" | "planning-sessions";

export interface AssistantTabsProps {
  active: AssistantView;
  onSelect: (view: AssistantView) => void;
}

const tabs = [
  { id: "chat", label: "Chat" },
  { id: "projects", label: "Proyectos" },
  { id: "planning-sessions", label: "Sesiones de planning" },
];

export function AssistantTabs({ active, onSelect }: AssistantTabsProps) {
  return (
    <Tabs
      tabs={tabs}
      activeTab={active}
      onTabChange={(id) => onSelect(id as AssistantView)}
      ariaLabel="Secciones del asistente"
    >
      {() => null}
    </Tabs>
  );
}
