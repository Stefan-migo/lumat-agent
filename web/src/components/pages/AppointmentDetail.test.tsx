import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { AppointmentDetail } from './AppointmentDetail';
import type { AppointmentDetail as AppointmentDetailData } from '../../types';
import { closeAppointment, fetchUsers, rescheduleAppointment } from '../../api';

vi.mock('../../api', () => ({ getAppointment: vi.fn(), closeAppointment: vi.fn(), fetchUsers: vi.fn(), rescheduleAppointment: vi.fn() }));

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
  it('offers confirmed outcomes for booked appointments and reports success', async () => {
    const user = userEvent.setup();
    vi.mocked(closeAppointment).mockResolvedValue({ ok: true, appointment: {} });
    render(<AppointmentDetail data={detail} />);
    await user.click(screen.getByRole('button', { name: 'Cerrar visita' }));
    await user.click(screen.getByRole('button', { name: 'Completar' }));
    await waitFor(() => expect(closeAppointment).toHaveBeenCalledWith(7, 'completed'));
    expect(await screen.findByRole('status')).toHaveTextContent('Visita completada');
  });

  it('supports no-show and surfaces failure; terminal visits have no outcome action', async () => {
    const user = userEvent.setup();
    vi.mocked(closeAppointment).mockRejectedValue(new Error('Intenta nuevamente'));
    render(<AppointmentDetail data={detail} />);
    await user.click(screen.getByRole('button', { name: 'Cerrar visita' }));
    await user.click(screen.getByRole('button', { name: 'No asistió' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Intenta nuevamente');
    expect(closeAppointment).toHaveBeenCalledWith(7, 'no_show');

    cleanup();
    render(<AppointmentDetail data={{ ...detail, appointment: { ...detail.appointment, status: 'completed' } }} />);
    expect(screen.queryByRole('button', { name: 'Cerrar visita' })).not.toBeInTheDocument();
  });

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

  it('offers rescheduling only for booked appointments', () => {
    render(<AppointmentDetail data={detail} />);
    expect(screen.getByRole('button', { name: 'Reprogramar' })).toBeInTheDocument();
  });

  it('defaults and submits a complete replacement slot', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchUsers).mockResolvedValue({ users: [{ id: 4, username: 'Tech', role: 'tecnico', active: true }] as never });
    vi.mocked(rescheduleAppointment).mockResolvedValue({ ok: true, appointment: {} });
    render(<AppointmentDetail data={detail} />);
    await user.click(screen.getByRole('button', { name: 'Reprogramar' }));
    const dialog = screen.getByRole('dialog', { name: 'Reprogramar visita' });
    expect(dialog.querySelector('input[type="date"]')).toHaveValue('2026-09-26');
    await user.click(screen.getByRole('button', { name: 'Confirmar reprogramación' }));
    await waitFor(() => expect(rescheduleAppointment).toHaveBeenCalledWith(7, {
      local_date: '2026-09-26', local_time: '10:00', duration_minutes: 60,
      technician_id: 4, timezone: 'America/Santiago',
    }));
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
