import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  headerClassName?: string;
}

/** Page title block with muted meta and optional actions. */
export function PageHeader({ title, meta, actions, headerClassName }: PageHeaderProps) {
  return (
    <header className={`page-header${headerClassName ? ` ${headerClassName}` : ""}`}>
      <div className="page-header__copy">
        <h1>{title}</h1>
        {meta ? <p>{meta}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
