import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  meta?: ReactNode;
  titleAdornment?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  headerClassName?: string;
}

/** Page title block with muted meta and optional actions. */
export function PageHeader({ title, meta, titleAdornment, subtitle, actions, headerClassName }: PageHeaderProps) {
  return (
    <header className={`page-header${headerClassName ? ` ${headerClassName}` : ""}`}>
      <div className="page-header__copy">
        <div className="page-header__title-row"><h1>{title}</h1>{titleAdornment}</div>
        {subtitle ? <p>{subtitle}</p> : null}
        {meta ? <p>{meta}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
