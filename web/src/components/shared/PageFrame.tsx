import type { ReactNode } from "react";
import { PageHeader } from "./PageHeader";

export interface PageFrameProps {
  title: string;
  meta?: ReactNode;
  titleAdornment?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  state?: ReactNode;
  headerClassName?: string;
  className?: string;
  children: ReactNode;
}

export function PageFrame({ title, meta, titleAdornment, subtitle, actions, state, headerClassName, className, children }: PageFrameProps) {
  return (
    <main className={`page-frame${className ? ` ${className}` : ""}`}>
      <div className="page-frame__titlebar">
        <PageHeader
          title={title}
          meta={meta}
          titleAdornment={titleAdornment}
          subtitle={subtitle}
          actions={actions}
          headerClassName={headerClassName}
        />
      </div>
      {state ? <div className="page-frame__banner">{state}</div> : null}
      <div className="page-frame__content">{children}</div>
    </main>
  );
}
