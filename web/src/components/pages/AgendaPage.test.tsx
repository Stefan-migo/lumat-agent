import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgendaPage } from './AgendaPage';
import type { AgendaAppointment } from '../../types';

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

  it('shows a labelled empty state and keeps the table wrapper mobile-safe', () => {
    const { container } = render(<AgendaPage data={[]} state="empty" />);
    expect(screen.getByText('No hay visitas')).toBeInTheDocument();
    expect(container.querySelector('.agenda-page__table-wrap')).toBeInTheDocument();
    expect(screen.queryByText(/disponibilidad|crear|editar|reagendar/i)).not.toBeInTheDocument();
  });
});
