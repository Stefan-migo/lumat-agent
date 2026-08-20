import type { Meta, StoryObj } from '@storybook/react';
import { Matrix as MatrixGrid } from '../helpers/matrix';
import { AppShell } from '../../components/domain/AppShell';

const meta = {
  title: 'domain/AppShell',
  component: AppShell,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Application shell: role-gated sidebar nav + view switch (DS-STORY-2).\n\n' +
          '**When to use** — the authenticated panel frame; every top-level view renders inside it.\n' +
          "**When not to use** — embedded widgets or drill-down details without nav (render the view content directly).\n\n" +
          '**Accessibility** — the active nav item carries `aria-current="page"`; the `<nav>` has `aria-label="Navegación principal"`. Admin-only views (Base de conocimientos, Configuración) are filtered out for `operador` so the nav never shows dead links. Nav buttons are real `<button>`s (focusable, keyboard-operable) and the focus indicator MUST use the design tokens: `--focus-ring`, `--focus-ring-width`, `--focus-ring-offset` (2px solid, 2px offset) on `--surface` (WCAG 2.4.11).',
      },
    },
  },
  argTypes: {
    'user.username': { control: 'text', description: 'Logged-in username, shown in the nav footer.' },
    'user.role': {
      control: 'select',
      options: ['admin', 'operador'],
      description: 'Role gates admin-only nav entries.',
    },
  } as Meta<typeof AppShell>['argTypes'],
} satisfies Meta<typeof AppShell>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Admin: Story = {
  args: { user: { username: 'ana', role: 'admin' } },
};

export const Operador: Story = {
  args: { user: { username: 'vero', role: 'operador' } },
};

export const Matrix: StoryObj = {
  render: () => (
    <MatrixGrid
      cells={[
        [
          'Admin nav',
          <div key="admin" style={{ maxHeight: 320, overflow: 'auto' }}>
            <AppShell user={{ username: 'ana', role: 'admin' }} />
          </div>,
        ],
        [
          'Operador nav',
          <div key="oper" style={{ maxHeight: 320, overflow: 'auto' }}>
            <AppShell user={{ username: 'vero', role: 'operador' }} />
          </div>,
        ],
      ]}
    />
  ),
};
