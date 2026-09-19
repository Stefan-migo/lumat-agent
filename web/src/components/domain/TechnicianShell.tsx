import type { ReactNode } from 'react';
import { Button } from '../primitives/Button';
import type { User } from '../../types';

export interface TechnicianShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
  children: ReactNode;
}

/** Session chrome for the `tecnico` role.
 *
 * The page name belongs to the page (`PageFrame`), not to the shell: rendering
 * it here as well produced two `<h1>`s on one screen and pushed the agenda down
 * on a phone. The header keeps the brand and the session controls, and shares
 * the content's centred gutter so chrome and content line up at ≥64rem.
 *
 * Styles live in `primitives.css` under the technician shell section — the same
 * tokenized boundary the panel shell uses (DS-SHELL-3), not an injected block. */
export function TechnicianShell({ user, onLogout, children }: TechnicianShellProps) {
  return (
    <div className="technician-shell">
      <header className="technician-shell__header">
        <div className="technician-shell__header-inner">
          <div className="technician-shell__brand">
            <img src="/panel/app/brand/lumat-logo.png" alt="Lumat" />
            <span>{user.username}</span>
          </div>
          {onLogout ? <Button variant="secondary" onClick={() => void onLogout()}>Cerrar sesión</Button> : null}
        </div>
      </header>
      <div className="technician-shell__content">{children}</div>
    </div>
  );
}
