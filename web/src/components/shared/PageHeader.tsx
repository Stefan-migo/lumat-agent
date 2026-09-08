import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
}

/** Page title block with muted meta and optional actions. */
export function PageHeader({ title, meta, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header__copy">
        <h1>{title}</h1>
        {meta ? <p>{meta}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
