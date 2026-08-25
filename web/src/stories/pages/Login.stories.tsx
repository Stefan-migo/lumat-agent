import type { Meta, StoryObj } from "@storybook/react";
import { LoginAuth } from "../../components/pages/LoginAuth";
export { LoginAuth } from "../../components/pages/LoginAuth";

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
