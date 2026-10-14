import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Icon } from "../primitives/Icon";

export interface PageHeaderProps {
  title: string;
  meta?: ReactNode;
  /** Optional leading icon tile rendered before the page title. */
  titleIcon?: LucideIcon;
  titleAdornment?: ReactNode;
  subtitle?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  hideCopy?: boolean;
  headerClassName?: string;
}

/** Page title block with muted meta and optional actions. */
export function PageHeader({ title, meta, titleIcon, titleAdornment, subtitle, eyebrow, actions, hideCopy, headerClassName }: PageHeaderProps) {
  return (
    <header className={`page-header${headerClassName ? ` ${headerClassName}` : ""}`}>
      {!hideCopy ? <div className="page-header__copy">
        {eyebrow ? <p className="page-header__eyebrow">{eyebrow}</p> : null}
        <div className="page-header__title-row">{titleIcon ? <span className="page-header__icon"><Icon icon={titleIcon} /></span> : null}<h1>{title}</h1>{titleAdornment}</div>
        {subtitle ? <p>{subtitle}</p> : null}
        {meta ? <p>{meta}</p> : null}
      </div> : null}
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
