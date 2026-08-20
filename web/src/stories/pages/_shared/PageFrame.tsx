import type { ReactNode } from "react";
import { PageHeader } from "./PageHeader";

/** Shared page shell (design D2; DS-UI-FRAME). Owns the titlebar (lime leading
 *  rail over a soft forest `--primary-100` tint, echoing the `panel-shell` brand
 *  block and the active navigation item), an optional banner slot (`state`)
 *  for StateMessage banners, and the content region. One contract for every
 *  page story instead of nine copies of the shell (the drift this redesign
 *  exists to remove). */
const PAGE_FRAME_STYLES = `
  .page-frame {
    display: grid;
    gap: var(--space-5);
    font-family: var(--font-sans);
  }

  .page-frame__titlebar {
    padding: var(--space-4) var(--space-4) 0;
    border: 1px solid var(--border);
    border-left: var(--space-1) solid var(--brand-lime);
    border-radius: var(--radius-md);
    background: var(--primary-100);
  }

  .page-frame__banner {
    display: grid;
    gap: var(--space-3);
  }

  .page-frame__content {
    display: grid;
    gap: var(--space-5);
    min-width: 0;
  }
`;

export interface PageFrameProps {
  title: string;
  /** Subtitle / meta line (e.g. window caption), muted and small. */
  meta?: ReactNode;
  /** Header actions (e.g. Export CSV button). */
  actions?: ReactNode;
  /** Banner slot: StateMessage / loading / stale / error surfaces. */
  state?: ReactNode;
  children: ReactNode;
}

export function PageFrame({ title, meta, actions, state, children }: PageFrameProps) {
  return (
    <main className="page-frame">
      <style>{PAGE_FRAME_STYLES}</style>

      <div className="page-frame__titlebar">
        <PageHeader title={title} meta={meta} actions={actions} />
      </div>

      {state ? <div className="page-frame__banner">{state}</div> : null}

      <div className="page-frame__content">{children}</div>
    </main>
  );
}
