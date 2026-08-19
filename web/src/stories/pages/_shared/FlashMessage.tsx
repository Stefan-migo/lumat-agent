import type { ReactNode } from "react";
import type { BadgeTone } from "../../../components/primitives/Badge";

export interface FlashMessageProps {
  tone: BadgeTone;
  children: ReactNode;
}

/** Inline flash message emitting `.flash-message--{tone}` (design D6).
 *  `BadgeTone` is reused for the tone set: success/warning/danger/neutral. */
export function FlashMessage({ tone, children }: FlashMessageProps) {
  return <div className={`flash-message flash-message--${tone}`}>{children}</div>;
}
