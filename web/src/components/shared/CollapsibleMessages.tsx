import type { ReactNode } from "react";
import { Button } from "../primitives/Button";

export interface CollapsibleMessagesProps {
  total: number;
  previewCount?: number;
  expanded: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export function CollapsibleMessages({ total, previewCount = 10, expanded, onToggle, children }: CollapsibleMessagesProps) {
  if (total <= previewCount) return <>{children}</>;
  return (
    <>
      {children}
      <Button variant="secondary" onClick={onToggle}>
        {expanded ? "Ver menos" : `Ver todos (${total})`}
      </Button>
    </>
  );
}
