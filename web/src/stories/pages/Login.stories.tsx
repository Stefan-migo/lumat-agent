import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "../../components/primitives/Button";
import { Card } from "../../components/primitives/Card";
import { Input } from "../../components/primitives/Input";

/** Login auth card (centered, mirroring Jinja login.html). Optional
 *  `error` renders the inline error line (T5.4). Exported for tests.
 *  @param error error message string or null for the default state */
export function LoginAuth({ error }: { error?: string | null }) {
  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: "3rem" }}>
      <Card title="Lumat Panel">
        <div
          style={{
            maxWidth: "24rem",
            display: "grid",
            gap: "var(--space-3)",
          }}
        >
          {error ? (
            <p style={{ color: "var(--danger, inherit)", margin: 0 }}>{error}</p>
          ) : null}
          <Input label="Username" type="text" autoComplete="username" />
          <Input label="Password" type="password" autoComplete="current-password" />
          <div>
            <Button>Login</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

/** Default login state: centered auth card, no error. */
export function LoginDefault() {
  return <LoginAuth error={null} />;
}

/** Error login state: auth card with an inline error message. */
export function LoginError() {
  return <LoginAuth error="invalid credentials" />;
}

const meta = {
  title: "pages/Login",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel login: centered "Lumat Panel" auth card with username + password + Login (T5.4; R-PRD-PG-1).\n\n' +
          "**When to use** — the unauthenticated entry point.\n" +
          "**Source** — page-first Storybook mock mirroring Jinja login.html; production wiring untouched.",
      },
    },
  },
  excludeStories: ["LoginAuth", "LoginDefault", "LoginError"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <LoginDefault />,
};

export const Error: Story = {
  render: () => <LoginError />,
};
