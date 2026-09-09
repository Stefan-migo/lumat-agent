import type { ReactNode } from 'react';
import type { User } from '../../types';

export interface TechnicianShellProps {
  user: User;
  onLogout?: () => void | Promise<void>;
  children: ReactNode;
}

const STYLES = `.technician-shell{min-height:100vh;background:var(--brand-bg);color:var(--text)}.technician-shell__header{display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);padding:var(--space-4);border-bottom:1px solid var(--border)}.technician-shell__brand{display:grid;gap:var(--space-1)}.technician-shell__brand img{width:7rem}.technician-shell__content{width:min(100% - 2rem,64rem);margin:0 auto;padding:var(--space-5) 0}.technician-shell__logout{border:1px solid var(--border);border-radius:var(--radius-md);background:transparent;color:inherit;padding:var(--space-2) var(--space-3);cursor:pointer}@media(max-width:40rem){.technician-shell__header{align-items:flex-start}.technician-shell__logout{min-height:2.75rem}}`;

export function TechnicianShell({ user, onLogout, children }: TechnicianShellProps) {
  return (
    <div className="technician-shell">
      <style>{STYLES}</style>
      <header className="technician-shell__header">
        <div className="technician-shell__brand">
          <img src="/panel/app/brand/lumat-logo.png" alt="Lumat" />
          <h1>Agenda técnica</h1>
          <span>{user.username}</span>
        </div>
        {onLogout ? <button type="button" className="technician-shell__logout" onClick={() => void onLogout()}>Cerrar sesión</button> : null}
      </header>
      <div className="technician-shell__content">{children}</div>
    </div>
  );
}
