import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Icon } from "./Icon";
import "./primitives.css";

export interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
  icon?: LucideIcon;
  description?: string;
  headerAction?: ReactNode;
  footer?: ReactNode;
}

export function Card({ title, children, className = "", icon, description, headerAction, footer }: CardProps) {
  return (
    <section className={`card ${className}`.trim()}>
      {title ? (
        <header className="card__header">
          {icon ? <span className="card__icon"><Icon icon={icon} /></span> : null}
          <div className="card__copy">
            <h2 className="card__title">{title}</h2>
            {description ? <p className="card__description">{description}</p> : null}
          </div>
          {headerAction ? <div className="card__header-action">{headerAction}</div> : null}
        </header>
      ) : null}
      {children}
      {footer ? <footer className="card__footer">{footer}</footer> : null}
    </section>
  );
}
