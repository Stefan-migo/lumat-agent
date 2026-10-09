import { useId, useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { Badge } from "./Badge";
import "./primitives.css";

export interface AccordionProps {
  title: string;
  count: number;
  children: ReactNode;
  defaultExpanded?: boolean;
}

export function Accordion({ title, count, children, defaultExpanded = false }: AccordionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const id = useId();
  const triggerId = `${id}-trigger`;
  const panelId = `${id}-panel`;

  return (
    <section className="accordion">
      <button
        id={triggerId}
        className="accordion__trigger"
        type="button"
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={() => setExpanded((open) => !open)}
      >
        <ChevronRight className="accordion__chevron" aria-hidden="true" />
        <span className="accordion__title">{title}</span>
        <Badge>{count}</Badge>
      </button>
      <div id={panelId} className="accordion__panel" role="region" aria-labelledby={triggerId} hidden={!expanded}>
        {children}
      </div>
    </section>
  );
}
