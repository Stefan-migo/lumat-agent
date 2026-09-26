import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AppointmentDetail } from './AppointmentDetail';
import type { AppointmentDetail as AppointmentDetailData } from '../../types';

const detail: AppointmentDetailData = {
  appointment: {
    id: 7, service: 'Reparación de calefón', customer_id: 2, case_id: 3, technician_id: 4,
    local_start: '2026-09-26T10:00:00', timezone: 'America/Santiago', starts_at: '2026-09-26T13:00:00Z',
    ends_at: '2026-09-26T14:00:00Z', duration_minutes: 60, status: 'booked',
    history: [{ id: 9, actor: 'ana', action: 'created', from_status: null, to_status: 'booked', details: { source: 'panel' }, created_at: '2026-09-25T12:00:00Z' }],
  },
  customer: { id: 2, name: 'Ana' },
  case: { id: 3, conversation_id: null },
  conversation_summary: null,
};

describe('AppointmentDetail', () => {
  it('renders appointment facts, customer link, and its audit trail without a conversation summary', () => {
    render(<AppointmentDetail data={detail} />);

    expect(screen.getByRole('link', { name: 'Ana' })).toHaveAttribute('href', '/panel/app/clients/2');
    expect(screen.getByText('Reparación de calefón')).toBeInTheDocument();
    expect(screen.getByText('Reservada')).toBeInTheDocument();
    expect(screen.queryByText('Resumen de la conversación')).not.toBeInTheDocument();
    const history = screen.getByRole('list', { name: 'Historial de la visita' });
    expect(history).toHaveTextContent('created');
    expect(history).toHaveTextContent('ana');
    expect(history).toHaveTextContent('booked');
    expect(history).toHaveTextContent('panel');
    expect(history.querySelector('time')).toHaveAttribute('dateTime', '2026-09-25T12:00:00Z');
  });

  it('shows a conversation summary only when present', () => {
    render(<AppointmentDetail data={{ ...detail, case: { id: 3, conversation_id: 44 }, conversation_summary: 'El cliente pide una reparación.' }} />);
    expect(screen.getByText('El cliente pide una reparación.')).toBeInTheDocument();
  });

  it('renders loading, denied, error, and retry states', () => {
    const onRetry = vi.fn();
    const { rerender } = render(<AppointmentDetail state="loading" />);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando visita');
    rerender(<AppointmentDetail state="denied" />);
    expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso');
    rerender(<AppointmentDetail state="error" onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar la visita');
    screen.getByRole('button', { name: 'Reintentar' }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
