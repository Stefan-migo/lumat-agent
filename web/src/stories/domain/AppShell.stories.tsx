import type { Meta, StoryObj } from '@storybook/react';
import { AppShell } from '../../components/domain/AppShell';

const meta = {
  title: 'domain/AppShell',
  component: AppShell,
  parameters: { layout: 'fullscreen' },
} satisfies Meta<typeof AppShell>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Admin: Story = {
  args: { user: { username: 'ana', role: 'admin' } },
};

export const Operador: Story = {
  args: { user: { username: 'vero', role: 'operador' } },
};
