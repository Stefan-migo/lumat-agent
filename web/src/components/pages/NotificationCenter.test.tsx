import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { NotificationCenter } from './NotificationCenter';
import type { PanelNotification } from '../../types';

const notifications: PanelNotification[] = [
  { id: 1, user_id: 1, operation_id: 1, title: 'Nueva visita', content: 'Caso 9', source: 'appointment', source_entity: 'appointment', source_id: '9', channel: 'panel', status: 'sent', read_at: null, created_at: '2026-09-03T12:00:00Z' },
  { id: 2, user_id: 1, operation_id: 2, title: 'Emergencia', content: 'Revisar conversación', source: 'emergencia', source_entity: 'conversation', source_id: '22', channel: 'panel', status: 'sent', read_at: null, created_at: null },
  { id: 3, user_id: 1, operation_id: 3, title: 'Costo cercano', content: 'Límite próximo', source: 'cost_alert', source_entity: null, source_id: null, channel: 'panel', status: 'sent', read_at: null, created_at: null },
  { id: 4, user_id: 1, operation_id: 4, title: 'Falló el envío', content: 'Entrega permanente fallida', source: 'notification_failure', source_entity: null, source_id: null, channel: 'panel', status: 'sent', read_at: null, created_at: null },
];

function renderCenter(overrides: Partial<React.ComponentProps<typeof NotificationCenter>> = {}) {
  const props: React.ComponentProps<typeof NotificationCenter> = {
    notifications,
    state: { status: 'ready', unread: 4 },
    unreadOnly: false,
    onUnreadOnlyChange: vi.fn(),
    onMarkRead: vi.fn(),
    pendingReadIds: [],
    readErrors: {},
    onOpenNotification: vi.fn(),
    ...overrides,
  };
  return { ...render(<NotificationCenter {...props} />), props };
}

describe('NotificationCenter', () => {
  it('renders source labels and makes only known destination rows actionable', () => {
    const { props } = renderCenter();
    expect(screen.getByRole('heading', { name: 'Notificaciones' })).toBeInTheDocument();
    expect(screen.getByText('Origen: Agenda')).toBeInTheDocument();
    expect(screen.getByText('Origen: Emergencias')).toBeInTheDocument();
    expect(screen.getByText('Origen: Alertas de costo')).toBeInTheDocument();
    expect(screen.getByText('Origen: Fallos de notificación')).toBeInTheDocument();
    for (const icon of ['lucide-calendar-days', 'lucide-shield-alert', 'lucide-circle-dollar-sign', 'lucide-circle-alert']) {
      expect(document.querySelector(`.${icon}`)).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: /Nueva visita\. Ir a la visita/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Emergencia\. Ir a la conversación/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Costo cercano' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Falló el envío' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Nueva visita\. Ir a la visita/ }));
    expect(props.onOpenNotification).toHaveBeenCalledWith(notifications[0]);
  });

  it('uses the shared unread filter and exposes marking pending/error states', () => {
    const onUnreadOnlyChange = vi.fn();
    renderCenter({ onUnreadOnlyChange, pendingReadIds: [1], readErrors: { 1: 'No pudimos marcar la notificación como leída.' } });
    fireEvent.click(screen.getByLabelText('Solo no leídas'));
    expect(onUnreadOnlyChange).toHaveBeenCalledWith(true);
    expect(screen.getByRole('button', { name: 'Marcando…' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos marcar la notificación como leída');
  });

  it('renders loading and error states', () => {
    const { rerender } = renderCenter({ state: { status: 'loading' } });
    expect(screen.getByRole('status')).toHaveTextContent('Cargando notificaciones');
    rerender(<NotificationCenter notifications={[]} state={{ status: 'error' }} unreadOnly={false} onUnreadOnlyChange={vi.fn()} onMarkRead={vi.fn()} pendingReadIds={[]} readErrors={{}} onOpenNotification={vi.fn()} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar las notificaciones');
  });
});
