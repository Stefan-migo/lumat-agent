import type { ReactNode } from "react";

export interface CollapsibleMessagesProps {
  total: number;
  previewCount?: number;
  expanded: boolean;
  onToggle: () => void;
  children: ReactNode;
}

/** Collapses an old conversation to its last `previewCount` rows. The control
 *  sits above the rows — that is where the hidden messages are — and reads as a
 *  quiet line instead of a button bar, so it never competes with the composer. */
export function CollapsibleMessages({ total, previewCount = 10, expanded, onToggle, children }: CollapsibleMessagesProps) {
  if (total <= previewCount) return <>{children}</>;
  const hidden = total - previewCount;
  return (
    <>
      <button
        type="button"
        className="collapsible-messages__toggle"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        {expanded ? "Ver menos" : `${hidden} mensajes anteriores · Ver todos`}
      </button>
      {children}
    </>
  );
}
