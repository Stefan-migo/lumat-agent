import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { PanelShell } from '../../components/domain/PanelShell';
import type { PanelNotification, User } from '../../types';

const user: User = { username: 'ana', role: 'admin' };
const notifications: PanelNotification[] = [
  { id: 1, user_id: 1, operation_id: 1, title: 'Atención humana requerida', content: 'Carla Núñez necesita hablar con una persona.', source: 'case', channel: 'whatsapp', status: 'sent', read_at: null, created_at: new Date(Date.now() - 5 * 60_000).toISOString() },
  { id: 2, user_id: 1, operation_id: 2, title: 'Nueva visita agendada', content: 'Pedro Soto · Visita de diagnóstico', source: 'appointment', channel: 'whatsapp', status: 'sent', read_at: null, created_at: new Date(Date.now() - 20 * 60_000).toISOString() },
  { id: 3, user_id: 1, operation_id: 3, title: 'Documento procesado', content: 'El manual de servicios ya está disponible.', source: 'document', channel: 'email', status: 'sent', read_at: new Date().toISOString(), created_at: new Date(Date.now() - 60 * 60_000).toISOString() },
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
