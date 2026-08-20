import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Input } from "../../components/primitives/Input";

/** Login auth card (centered, mirroring Jinja login.html). Optional `error`
 *  renders the inline error line — non-destructive: the username value is
 *  preserved via `username` so a failed attempt can be retried without
 *  retyping, and it is a generic auth error that never reveals whether a
 *  username exists (DS-UI-LOGIN). `isLoading` shows a saving state that
 *  disables submit and announces "Iniciando sesión…".
 *
 *  The lockup is typographic (design D8): no production logo asset exists, so
 *  it reuses the `panel-shell` brand-block language ("Lumat" + "Panel
 *  operativo") as styled text.
 *  Exported for tests. @param error error message string or null for default */
export function LoginAuth({
  error,
  username = "",
  isLoading = false,
}: {
  error?: string | null;
  username?: string;
  isLoading?: boolean;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: "3rem" }}>
      <Card className="card--auth">
        <style>{LOGIN_BRAND_STYLES}</style>
        <div className="login-brand">
          <span className="login-brand__name">Lumat</span>
          <span className="login-brand__context">Panel operativo</span>
        </div>
        <div
          style={{
            maxWidth: "24rem",
            display: "grid",
            gap: "var(--space-3)",
          }}
        >
          {error ? (
            <p role="alert" style={{ color: "var(--danger, inherit)", margin: 0 }}>
              {error}
            </p>
          ) : null}
          <Input
            label="Usuario"
            type="text"
            defaultValue={username}
            autoComplete="username"
          />
          <Input label="Contraseña" type="password" autoComplete="current-password" />
          <div style={{ display: "grid", gap: "var(--space-2)" }}>
            <Button disabled={isLoading}>Iniciar sesión</Button>
            {isLoading ? (
              <p
                role="status"
                style={{
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-2)",
                  color: "var(--text-muted)",
                  fontSize: "var(--text-sm)",
                }}
              >
                <span className="spinner__indicator" aria-hidden="true" />
                Iniciando sesión…
              </p>
            ) : null}
          </div>
        </div>
      </Card>
    </div>
  );
}

/** Typographic lockup styles echoing the `panel-shell` brand block: lime rail
 *  over a forest tint, bold "Lumat" + aqua "Panel operativo" context. No logo
 *  asset — type only (design D8). */
const LOGIN_BRAND_STYLES = `
  .login-brand {
    display: grid;
    gap: var(--space-1);
    padding: var(--space-4);
    border-left: var(--space-1) solid var(--brand-lime);
    border-radius: var(--radius-md);
    background: var(--primary-800);
    color: var(--surface);
  }
  .login-brand__name {
    font-size: var(--text-lg);
    font-weight: var(--weight-bold);
    line-height: var(--leading-tight);
    letter-spacing: -0.02em;
  }
  .login-brand__context {
    color: var(--brand-aqua);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
  }
`;

/** Default login state: centered auth card, no error. */
export function LoginDefault() {
  return <LoginAuth error={null} />;
}

/** Error login state: auth card with a generic non-destructive inline error
 *  that preserves the typed username (DS-UI-LOGIN). */
export function LoginError() {
  return <LoginAuth error="Credenciales inválidas" username="marcela" />;
}

/** Loading login state: submit is disabled and "Iniciando sesión…" announces
 *  the async request while the fields stay editable (DS-UI-STATES). */
export function LoginLoading() {
  return <LoginAuth error={null} username="marcela" isLoading />;
}

const meta = {
  title: "pages/Login",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Login del panel: marca tipográfica Lumat, tarjeta compacta con Usuario/Contraseña/Iniciar sesión y estados por defecto, error genérico (que preserva el usuario) y carga (DS-UI-LOGIN; T5.4; R-PRD-PG-1).\n\n' +
          "**Cuándo usar** — el punto de entrada sin autenticar.\n" +
          "**Por qué tipográfica** — no existe un logo de producción (design D8); la marca reutiliza el lenguaje de marca del panel-shell.\n" +
          "**Fuente** — mock de Storybook que refleja login.html de Jinja; el cableado de producción no se toca.",
      },
    },
  },
  excludeStories: ["LoginAuth", "LoginDefault", "LoginError", "LoginLoading"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <LoginDefault />,
};

export const Error: Story = {
  render: () => <LoginError />,
};

export const Loading: Story = {
  render: () => <LoginLoading />,
};
