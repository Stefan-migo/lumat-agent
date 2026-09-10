import type { ReactNode } from "react";
import { PageHeader } from "./PageHeader";

const PAGE_FRAME_STYLES = `
  .page-frame {
    display: grid;
    gap: var(--space-5);
    font-family: var(--font-sans);
  }

  .page-frame__titlebar {
    padding: var(--space-2) 0 var(--space-4);
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
  meta?: ReactNode;
  actions?: ReactNode;
  state?: ReactNode;
  headerClassName?: string;
  className?: string;
  children: ReactNode;
}

export function PageFrame({ title, meta, actions, state, headerClassName, className, children }: PageFrameProps) {
  return (
    <main className={`page-frame${className ? ` ${className}` : ""}`}>
      <style>{PAGE_FRAME_STYLES}</style>
      <div className="page-frame__titlebar">
        <PageHeader title={title} meta={meta} actions={actions} headerClassName={headerClassName} />
      </div>
      {state ? <div className="page-frame__banner">{state}</div> : null}
      <div className="page-frame__content">{children}</div>
    </main>
  );
}
