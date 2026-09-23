import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgendaPage } from './AgendaPage';
import type { AgendaAppointment } from '../../types';
import { cancelAppointment, listAppointments, retryCalendarSync } from '../../api';
import { appointmentStatusLabel, appointmentSyncLabel } from '../shared/toneMaps';

vi.mock('../../api', () => ({
  listAppointments: vi.fn(),
  cancelAppointment: vi.fn(),
  retryCalendarSync: vi.fn(),
}));

const appointment = (overrides: Partial<AgendaAppointment> = {}): AgendaAppointment => ({
  id: 1,
  service: 'Mantención',
  customer_id: 10,
  customer_name: 'Camila Soto',
  case_id: 20,
  case_name: 'Caso #20',
  technician_id: 30,
  technician_name: 'Luis Pérez',
  local_start: '2026-09-05T10:00:00-04:00',
  timezone: 'America/Santiago',
  starts_at: '2026-09-05T14:00:00+00:00',
  ends_at: '2026-09-05T15:00:00+00:00',
  status: 'booked',
  sync: { status: 'synced', error: null, retry: false },
  ...overrides,
});

beforeEach(() => vi.setSystemTime(new Date('2026-09-05T12:00:00-04:00')));
afterEach(() => vi.useRealTimers());

describe('AgendaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });
  });

  it('renders loading, forbidden, error, and stale recovery states', () => {
    const retry = vi.fn();
    const { rerender } = render(<AgendaPage state="loading" data={null} onRetry={retry} />);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando agenda');

    rerender(<AgendaPage state="denied" data={null} onRetry={retry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso');
    rerender(<AgendaPage state="error" data={null} onRetry={retry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar la agenda');
    rerender(<AgendaPage state="stale" data={[appointment()]} onRetry={retry} />);
    expect(screen.getByRole('status')).toHaveTextContent('desactualizados');
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
  });

  it('groups chronological visits into Hoy and Próximas in a semantic table', () => {
    render(<AgendaPage data={[appointment(), appointment({ id: 2, service: 'Instalación', local_start: '2026-09-06T09:00:00-04:00' })]} state="ready" />);
    expect(screen.getByRole('heading', { name: 'Hoy', level: 2 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Próximas', level: 2 })).toBeInTheDocument();
    expect(screen.getAllByRole('table')).toHaveLength(2);
    expect(screen.getAllByText('Camila Soto')).toHaveLength(2);
    expect(screen.getByText('Instalación')).toBeInTheDocument();
    expect(screen.getByText('Mantención')).toBeInTheDocument();
  });

  it('uses singular and plural visit counts', () => {
    const { rerender } = render(<AgendaPage data={[appointment()]} state="ready" />);
    expect(screen.getByText('1 visita')).toBeInTheDocument();

    rerender(<AgendaPage data={[appointment(), appointment({ id: 2 })]} state="ready" />);
    expect(screen.getByText('2 visitas')).toBeInTheDocument();
  });

  it('renders appointment slots in 24-hour time', () => {
    render(<AgendaPage data={[appointment({ starts_at: '2026-09-05T18:00:00+00:00' })]} state="ready" />);
    expect(screen.getByText('14:00')).toBeInTheDocument();
    expect(screen.queryByText(/a\. m\.|p\. m\./i)).not.toBeInTheDocument();
  });

  it('does not render an empty surface for a section without rows', () => {
    render(<AgendaPage data={[appointment({ local_start: '2026-09-06T09:00:00-04:00' })]} state="ready" />);
    const today = screen.getByRole('heading', { name: 'Hoy', level: 2 }).closest('section');
    expect(today).not.toBeNull();
    expect(today?.querySelector('.empty-state')).not.toBeInTheDocument();
    expect(today).not.toHaveTextContent('No hay visitas');
  });

  it('shows a labelled empty state and keeps the table wrapper mobile-safe', () => {
    const { container } = render(<AgendaPage data={[]} state="empty" />);
    expect(screen.getByText('No hay visitas')).toBeInTheDocument();
    expect(container.querySelector('.agenda-page__table-wrap')).toBeInTheDocument();
    expect(screen.queryByText(/disponibilidad|crear|editar|reagendar/i)).not.toBeInTheDocument();
  });

  it('offers cancellation only for booked rows and refreshes after confirming a reason', async () => {
    const user = userEvent.setup();
    const cancelled = appointment({ status: 'cancelled' });
    vi.mocked(cancelAppointment).mockResolvedValue({ ok: true, appointment: cancelled });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [cancelled] });

    render(<AgendaPage data={[appointment()]} state="ready" />);
    await user.click(screen.getByRole('button', { name: 'Cancelar visita' }));
    expect(screen.getByRole('dialog', { name: 'Cancelar visita' })).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveTextContent('La visita no podrá volver a reservarse');
    expect(screen.getByLabelText('Motivo de cancelación')).toHaveClass('field__control');
    await user.type(screen.getByLabelText('Motivo de cancelación'), 'Cliente avisó');
    await user.click(screen.getByRole('button', { name: 'Confirmar cancelación' }));

    await waitFor(() => expect(cancelAppointment).toHaveBeenCalledWith(1, 'Cliente avisó'));
    await waitFor(() => expect(listAppointments).toHaveBeenCalled());
    expect(await screen.findByText('Cancelada')).toBeInTheDocument();
  });

  it('does not offer cancellation or issue a request for non-booked rows', () => {
    render(<AgendaPage data={[appointment({ status: 'completed' }), appointment({ id: 2, status: 'no_show' }), appointment({ id: 3, status: 'cancelled' })]} state="ready" />);
    expect(screen.queryByRole('button', { name: 'Cancelar visita' })).not.toBeInTheDocument();
    expect(cancelAppointment).not.toHaveBeenCalled();
  });

  it('retries pending and failed calendar sync from keyboard-operable actions', async () => {
    const user = userEvent.setup();
    vi.mocked(retryCalendarSync).mockResolvedValue({ ok: true, calendar: { status: 'synced', error: null } });
    render(<AgendaPage data={[appointment({ sync: { status: 'failed', error: 'Proveedor no disponible', retry: true } }), appointment({ id: 2, sync: { status: 'pending', error: null, retry: true } }), appointment({ id: 3 })]} state="ready" />);

    expect(screen.getAllByText(appointmentStatusLabel('booked'))).toHaveLength(3);
    expect(screen.getByText(appointmentSyncLabel('failed'))).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Reintentar calendario' })).toHaveLength(2);
    const retry = screen.getAllByRole('button', { name: 'Reintentar calendario' })[0];
    retry.focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(retryCalendarSync).toHaveBeenCalledWith(1));
    await waitFor(() => expect(listAppointments).toHaveBeenCalled());
  });

  it('shows actionable inline mutation failures without changing the row', async () => {
    const user = userEvent.setup();
    vi.mocked(cancelAppointment).mockRejectedValue(new Error('No se pudo cancelar'));
    render(<AgendaPage data={[appointment()]} state="ready" />);
    await user.click(screen.getByRole('button', { name: 'Cancelar visita' }));
    await user.click(screen.getByRole('button', { name: 'Confirmar cancelación' }));

    expect(await screen.findByRole('dialog')).toHaveTextContent('No se pudo cancelar');
    expect(screen.getByText(appointmentStatusLabel('booked'))).toBeInTheDocument();
  });

  it('shows sync retry failures beside the row action', async () => {
    const user = userEvent.setup();
    vi.mocked(retryCalendarSync).mockRejectedValue(new Error('Calendario no disponible'));
    render(<AgendaPage data={[appointment({ sync: { status: 'failed', error: null, retry: true } })]} state="ready" />);

    await user.click(screen.getByRole('button', { name: 'Reintentar calendario' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Calendario no disponible');
    expect(screen.getByRole('row', { name: /Mantención/ })).toHaveTextContent('Calendario no disponible');
  });
});
