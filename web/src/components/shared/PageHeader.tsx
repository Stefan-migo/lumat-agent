import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  meta?: ReactNode;
  titleAdornment?: ReactNode;
  subtitle?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  headerClassName?: string;
}

/** Page title block with muted meta and optional actions. */
export function PageHeader({ title, meta, titleAdornment, subtitle, eyebrow, actions, headerClassName }: PageHeaderProps) {
  return (
    <header className={`page-header${headerClassName ? ` ${headerClassName}` : ""}`}>
      <div className="page-header__copy">
        {eyebrow ? <p className="page-header__eyebrow">{eyebrow}</p> : null}
        <div className="page-header__title-row"><h1>{title}</h1>{titleAdornment}</div>
        {subtitle ? <p>{subtitle}</p> : null}
        {meta ? <p>{meta}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
