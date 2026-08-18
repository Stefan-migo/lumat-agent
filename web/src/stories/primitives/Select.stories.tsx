import type { Meta, StoryObj } from '@storybook/react';
import { Select } from '../../components/primitives/Select';

const options = [
  { value: 'nuevo', label: 'Nuevo' },
  { value: 'activo', label: 'Activo' },
  { value: 'finalizado', label: 'Finalizado' },
];

const meta = {
  title: 'primitives/Select',
  component: Select,
} satisfies Meta<typeof Select>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { label: 'Estado', options, defaultValue: 'nuevo' },
};

export const Small: Story = {
  args: { label: 'Estado', options, defaultValue: 'nuevo', size: 'sm' },
};

export const WithError: Story = {
  args: { label: 'Estado', options: [], defaultValue: '', error: 'Seleccione un estado' },
};

export const Disabled: Story = {
  args: { label: 'Estado', options, defaultValue: 'nuevo', disabled: true },
};
