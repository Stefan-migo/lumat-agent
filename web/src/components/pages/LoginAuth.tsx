import { useState, type FormEvent } from 'react';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Input } from '../primitives/Input';

export interface LoginAuthProps {
  error?: string | null;
  username?: string;
  isLoading?: boolean;
  onSubmit?: (credentials: { username: string; password: string }) => void | Promise<void>;
}

export function LoginAuth({ error, username = '', isLoading = false, onSubmit }: LoginAuthProps) {
  const [currentUsername, setCurrentUsername] = useState(username);
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = onSubmit?.({ username: currentUsername, password });
    if (result) {
      setSubmitting(true);
      void result.finally(() => setSubmitting(false));
    }
  };

  return (
    <main>
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '3rem' }}>
        <Card className="card--auth">
          <style>{LOGIN_BRAND_STYLES}</style>
          <div className="login-brand">
            <span className="login-brand__name">Lumat</span>
            <span className="login-brand__context">Panel operativo</span>
          </div>
          <form onSubmit={submit} style={{ maxWidth: '24rem', display: 'grid', gap: 'var(--space-3)' }}>
            {error ? <p role="alert" style={{ color: 'var(--danger, inherit)', margin: 0 }}>{error}</p> : null}
            <Input
              label="Usuario"
              type="text"
              value={currentUsername}
              onChange={(event) => setCurrentUsername(event.target.value)}
              autoComplete="username"
            />
            <Input
              label="Contraseña"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
            <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
              <Button type="submit" disabled={isLoading || submitting}>Iniciar sesión</Button>
              {isLoading || submitting ? <p role="status" style={{ margin: 0, color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Iniciando sesión…</p> : null}
            </div>
          </form>
        </Card>
      </div>
    </main>
  );
}

const LOGIN_BRAND_STYLES = `
  .login-brand { display: grid; gap: var(--space-1); padding: var(--space-4); border-left: var(--space-1) solid var(--brand-lime); border-radius: var(--radius-md); background: var(--primary-800); color: var(--surface); }
  .login-brand__name { font-size: var(--text-lg); font-weight: var(--weight-bold); line-height: var(--leading-tight); letter-spacing: -0.02em; }
  .login-brand__context { color: var(--brand-aqua); font-size: var(--text-xs); font-weight: var(--weight-medium); }
`;
