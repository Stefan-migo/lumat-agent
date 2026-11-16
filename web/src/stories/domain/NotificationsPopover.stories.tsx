import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { PanelShell } from '../../components/domain/PanelShell';
import type { PanelNotification, User } from '../../types';

const user: User = { username: 'ana', role: 'admin' };
const notifications: PanelNotification[] = [
  { id: 1, user_id: 1, operation_id: 1, title: 'Emergencia detectada', content: 'Carla Núñez necesita atención prioritaria.', source: 'emergencia', source_entity: 'conversation', source_id: '44', channel: 'panel', status: 'sent', read_at: null, created_at: new Date(Date.now() - 5 * 60_000).toISOString() },
  { id: 2, user_id: 1, operation_id: 2, title: 'Nueva visita agendada', content: 'Pedro Soto · Visita de diagnóstico', source: 'appointment', source_entity: 'appointment', source_id: '7', channel: 'panel', status: 'sent', read_at: null, created_at: new Date(Date.now() - 20 * 60_000).toISOString() },
  { id: 3, user_id: 1, operation_id: 3, title: 'Alerta de costo', content: 'El gasto se acerca al límite configurado.', source: 'cost_alert', source_entity: null, source_id: null, channel: 'panel', status: 'sent', read_at: new Date().toISOString(), created_at: new Date(Date.now() - 60 * 60_000).toISOString() },
];

const meta = {
  title: 'domain/NotificationsPopover',
  parameters: { layout: 'fullscreen', panelShell: false },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

function NotificationsExample({ empty = false }: { empty?: boolean }) {
  const [items, setItems] = useState(empty ? [] : notifications);
  return <PanelShell user={user} notifications={items} notificationState={{ status: 'ready', unread: items.filter((item) => item.read_at === null).length }} onMarkAllNotificationsRead={() => setItems(items.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })))}><div style={{ minHeight: '70vh' }} /></PanelShell>;
}

const openPopover: Story['play'] = async ({ canvasElement }) => {
  canvasElement.querySelector<HTMLButtonElement>('.panel-shell__header-actions .panel-shell__header-action')?.click();
};

export const WithNotifications: Story = { render: () => <NotificationsExample />, play: openPopover };
export const Empty: Story = { render: () => <NotificationsExample empty />, play: openPopover };
