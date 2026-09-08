import { useState, type FormEvent } from 'react';
import { Button } from '../primitives/Button';
import { Input } from '../primitives/Input';
import { PageFrame } from '../shared/PageFrame';

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
    <PageFrame title="Bienvenido">
      <div className="login-frame">
        <section className="login-frame__brand" aria-labelledby="login-brand-name">
          <div className="login-brand">
            <span className="login-brand__name" id="login-brand-name">Lumat</span>
            <span className="login-brand__context">Panel operativo</span>
          </div>
          <p className="login-frame__welcome">Gestioná tus conversaciones y operaciones desde un solo lugar.</p>
        </section>
        <section className="login-frame__form" aria-labelledby="login-form-title">
          <h2 id="login-form-title">Acceso al panel</h2>
          <form onSubmit={submit} aria-label="Formulario de acceso">
            {error ? <p className="login-frame__error" role="alert">{error}</p> : null}
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
            <div className="login-frame__submit">
              <Button type="submit" disabled={isLoading || submitting}>Iniciar sesión</Button>
              {isLoading || submitting ? <p className="login-frame__status" role="status">Iniciando sesión…</p> : null}
            </div>
          </form>
        </section>
      </div>
    </PageFrame>
  );
}
