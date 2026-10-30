import { describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OverdueVisitsPanel } from './OverdueVisitsPanel';
import type { AgendaAppointment } from '../../types';

const visit = (id: number, customer_name: string): AgendaAppointment => ({
  id,
  service: `Servicio ${id}`,
  customer_id: id + 100,
  customer_name,
  customer_address: null,
  customer_comuna: null,
  case_id: id + 200,
  case_name: `Caso ${id}`,
  technician_id: id + 300,
  technician_name: 'Luis Pérez',
  local_start: '2026-09-01T10:00:00-04:00',
  timezone: 'America/Santiago',
  starts_at: '2026-09-01T14:00:00+00:00',
  ends_at: `2026-09-${String(id).padStart(2, '0')}T15:00:00+00:00`,
  duration_minutes: 60,
  status: 'booked',
  sync: { status: 'synced', error: null, retry: false },
});

function renderPanel(appointments: AgendaAppointment[], onCloseAppointment = vi.fn(), onBulkClose = vi.fn()) {
  return render(<OverdueVisitsPanel appointments={appointments} onCloseAppointment={onCloseAppointment} onBulkClose={onBulkClose} />);
}

describe('OverdueVisitsPanel', () => {
  it('renders no section when there are no overdue visits', () => {
    const { container } = renderPanel([]);

    expect(container).toBeEmptyDOMElement();
  });

  it('shows each customer and service and offers per-row close', async () => {
    const user = userEvent.setup();
    const onCloseAppointment = vi.fn();
    renderPanel([visit(1, 'Camila Soto'), visit(2, 'Diego Rojas')], onCloseAppointment);

    expect(screen.getByText('Camila Soto')).toBeInTheDocument();
    expect(screen.getByText('Servicio 1')).toBeInTheDocument();
    expect(screen.getByText('Diego Rojas')).toBeInTheDocument();
    expect(screen.getByText('Servicio 2')).toBeInTheDocument();
    expect(screen.getAllByText(/Martes 1 de septiembre/)).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Cerrar visita de Camila Soto' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Cerrar visita de Camila Soto' }));
    const dialog = screen.getByRole('dialog', { name: 'Cerrar visita' });
    await user.click(within(dialog).getByRole('radio', { name: /No completada/ }));
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar cierre' }));
    expect(onCloseAppointment).toHaveBeenCalledWith(1, 'no_show');
  });

  it('keeps bulk confirmation disabled until one outcome is chosen and previews customers', async () => {
    const user = userEvent.setup();
    const onBulkClose = vi.fn();
    renderPanel([visit(1, 'Camila Soto'), visit(2, 'Diego Rojas')], vi.fn(), onBulkClose);

    await user.click(screen.getByRole('checkbox', { name: 'Seleccionar visita de Camila Soto' }));
    await user.click(screen.getByRole('checkbox', { name: 'Seleccionar visita de Diego Rojas' }));
    await user.click(screen.getByRole('button', { name: 'Cerrar visitas seleccionadas' }));

    const dialog = screen.getByRole('dialog', { name: 'Cerrar 2 visitas' });
    expect(dialog).toHaveTextContent('Camila Soto');
    expect(dialog).toHaveTextContent('Diego Rojas');
    expect(within(dialog).getByRole('button', { name: 'Confirmar cierre' })).toBeDisabled();
    expect(within(dialog).getByRole('radio', { name: /Completada/ })).not.toBeChecked();
    expect(within(dialog).getByRole('radio', { name: /No completada/ })).not.toBeChecked();

    await user.click(within(dialog).getByRole('radio', { name: /Completada/ }));
    expect(within(dialog).getByRole('button', { name: 'Confirmar cierre' })).toBeEnabled();
  });

  it('reports successful and failed rows separately with the backend error', async () => {
    const user = userEvent.setup();
    const onBulkClose = vi.fn().mockResolvedValue({
      closed: 1,
      failed: 1,
      results: [
        { id: 1, ok: true, outcome: 'completed', error: null },
        { id: 2, ok: false, outcome: 'completed', error: 'only booked appointments can be closed' },
      ],
    });
    renderPanel([visit(1, 'Camila Soto'), visit(2, 'Diego Rojas')], vi.fn(), onBulkClose);

    await user.click(screen.getByRole('checkbox', { name: 'Seleccionar visita de Camila Soto' }));
    await user.click(screen.getByRole('checkbox', { name: 'Seleccionar visita de Diego Rojas' }));
    await user.click(screen.getByRole('button', { name: 'Cerrar visitas seleccionadas' }));
    const dialog = screen.getByRole('dialog', { name: 'Cerrar 2 visitas' });
    await user.click(within(dialog).getByRole('radio', { name: /Completada/ }));
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar cierre' }));

    expect(await screen.findByText('Cierre registrado')).toBeInTheDocument();
    expect(screen.getByText('only booked appointments can be closed')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Diego Rojas');
    expect(onBulkClose).toHaveBeenCalledWith([1, 2], 'completed');
  });

  it('does not allow selecting more than 100 visits', async () => {
    const visits = Array.from({ length: 101 }, (_, index) => visit(index + 1, `Cliente ${index + 1}`));
    renderPanel(visits);
    const checkboxes = screen.getAllByRole('checkbox');

    act(() => {
      for (let index = 0; index < 100; index += 1) fireEvent.click(checkboxes[index]);
    });

    expect(screen.getByRole('checkbox', { name: 'Seleccionar visita de Cliente 101' })).toBeDisabled();
  }, 60000);
});
