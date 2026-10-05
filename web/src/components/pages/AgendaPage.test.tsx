import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgendaPage } from './AgendaPage';
import type { AgendaAppointment } from '../../types';
import { cancelAppointment, closeAppointment, createAppointment, createCase, fetchCases, fetchClients, fetchTechnicians, listAppointments, rescheduleAppointment, retryCalendarSync } from '../../api';
import { appointmentStatusLabel, appointmentSyncLabel } from '../shared/toneMaps';

vi.mock('../../api', () => ({
  listAppointments: vi.fn(),
  cancelAppointment: vi.fn(),
  closeAppointment: vi.fn(),
  rescheduleAppointment: vi.fn(),
  retryCalendarSync: vi.fn(),
  createAppointment: vi.fn(),
  createCase: vi.fn(),
  fetchClients: vi.fn(),
  fetchCases: vi.fn(),
  fetchTechnicians: vi.fn(),
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

async function openVisitActions(user: ReturnType<typeof userEvent.setup>, service = 'Mantención') {
  await user.click(screen.getAllByRole('button', { name: `Acciones para ${service}` })[0]);
}

describe('AgendaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });
  });

  it('renders loading, forbidden, error, and stale recovery states', () => {
    const retry = vi.fn();
    const { rerender } = render(<AgendaPage state="loading" data={null} onRetry={retry} />);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando agenda');
    expect(screen.getByText('Visitas de la agenda')).toBeInTheDocument();

    rerender(<AgendaPage state="denied" data={null} onRetry={retry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso');
    rerender(<AgendaPage state="error" data={null} onRetry={retry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar la agenda');
    expect(screen.getByRole('alert').parentElement).toHaveClass('agenda-recovery');
    expect(screen.getByRole('button', { name: 'Reintentar' })).toHaveClass('btn');
    rerender(<AgendaPage state="stale" data={[appointment()]} onRetry={retry} />);
    expect(screen.getByRole('status')).toHaveTextContent('desactualizados');
    expect(screen.getByRole('status').parentElement).toHaveClass('agenda-recovery');
    expect(screen.getByRole('button', { name: 'Reintentar' })).toHaveClass('btn');
  });

  it('renders chronological visits as stacked detail cards', () => {
    const { container } = render(<AgendaPage data={[appointment(), appointment({ id: 2, service: 'Instalación', local_start: '2026-09-06T09:00:00-04:00' })]} state="ready" />);
    const dayHeading = screen.getByRole('heading', { name: /Sábado 5 de septiembre Hoy/i, level: 2 });
    expect(dayHeading.querySelector('.badge')).toHaveTextContent('Hoy');
    expect(dayHeading).toHaveClass('agenda-page__section-heading');
    expect(document.querySelectorAll('.agenda-page__visit-card')).toHaveLength(2);
    expect(screen.queryByRole('table', { name: /Registro/i })).not.toBeInTheDocument();
    expect(screen.getAllByText('Camila Soto')).toHaveLength(2);
    expect(screen.getByText('Instalación')).toBeInTheDocument();
    expect(screen.getByText('Mantención')).toBeInTheDocument();
    expect(container.querySelector('.agenda-page__visit-heading time svg')).toHaveClass('icon');
  });

  it('links the register service to its appointment detail route', () => {
    render(<AgendaPage data={[appointment({ id: 42 })]} state="ready" />);
    const link = screen.getByRole('link', { name: 'Mantención' });
    expect(link).toHaveAttribute('href', '/panel/app/agenda/42');
    link.focus();
    expect(link).toHaveFocus();
  });

  it('shows icons alongside every scheduled visit quick action', async () => {
    const user = userEvent.setup();
    const { container } = render(<AgendaPage data={[appointment()]} state="ready" />);

    await openVisitActions(user);
    expect(screen.getByRole('menuitem', { name: 'Reprogramar' }).querySelector('svg')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Cancelar visita' }).querySelector('svg')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Cerrar visita' }).querySelector('svg')).toBeInTheDocument();
    expect(container.querySelector('.agenda-page__visit-card')).not.toHaveTextContent('Reprogramar');
    expect(container.querySelector('.agenda-page__visit-card')).not.toHaveTextContent('Cerrar visita');
  });

  it('does not underline the scheduled visit title link', () => {
    const stylesheet = readFileSync(join(__dirname, '../primitives/primitives.css'), 'utf8');
    const title = stylesheet.match(/\.agenda-page__visit-title a\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(title).toMatch(/text-decoration:\s*none/);
  });

  it('uses singular and plural visit counts', () => {
    const { rerender } = render(<AgendaPage data={[appointment()]} state="ready" />);
    expect(screen.getAllByText('1 visita').find((element) => element.classList.contains('badge'))).toBeInTheDocument();

    rerender(<AgendaPage data={[appointment(), appointment({ id: 2 })]} state="ready" />);
    expect(screen.getAllByText('2 visitas').find((element) => element.classList.contains('badge'))).toBeInTheDocument();
  });

  it('renders appointment slots in 24-hour time', () => {
    render(<AgendaPage data={[appointment({ starts_at: '2026-09-05T18:00:00+00:00' })]} state="ready" />);
    expect(screen.getByText('14:00')).toBeInTheDocument();
    expect(screen.queryByText(/a\. m\.|p\. m\./i)).not.toBeInTheDocument();
  });

  it('renders future visits in the card surface when today has no rows', () => {
    render(<AgendaPage data={[appointment({ service: 'Instalación', local_start: '2026-09-06T09:00:00-04:00' })]} state="ready" />);
    expect(screen.getByText('Instalación')).toBeInTheDocument();
  });

  it('names the register region and surfaces cards without a table wrapper', () => {
    const { rerender } = render(<AgendaPage data={[appointment(), appointment({ id: 2, local_start: '2026-09-06T09:00:00-04:00' })]} state="ready" />);
    expect(screen.getByRole('region', { name: 'Registro de agenda' })).toBeInTheDocument();
    expect(document.querySelectorAll('.agenda-page__visit-card')).toHaveLength(2);

    rerender(<AgendaPage data={[appointment({ local_start: '2026-09-06T09:00:00-04:00' })]} state="ready" />);
    expect(document.querySelectorAll('.agenda-page__visit-card')).toHaveLength(1);
  });

  it('places the primary create action in the page header', () => {
    render(<AgendaPage data={[]} state="empty" />);
    expect(screen.getByRole('banner').querySelector('.page-header__actions')).toContainElement(
      screen.getByRole('button', { name: 'Nueva visita' }),
    );
  });

  it('uses the reference sections, leading field icons, and primary create action', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[]} state="empty" />);

    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    const dialog = await screen.findByRole('dialog', { name: 'Nueva visita' });
    const form = dialog.querySelector('.agenda-create-form');
    const stylesheet = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    const identityRow = stylesheet.match(/\.agenda-create-form__row--identity\s*\{([^}]*)\}/)?.[1] ?? '';
    const leadingIcon = stylesheet.match(/\.agenda-create-form__leading-icon\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(dialog.querySelector('.dialog__icon svg')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('Completa los datos para agendar una visita.');
    expect(within(dialog).getByRole('heading', { name: 'Datos de la visita' })).toBeInTheDocument();
    expect(within(dialog).getByRole('heading', { name: 'Fecha y horario' })).toBeInTheDocument();
    for (const label of ['Cliente', 'Caso vinculado', 'Servicio', 'Técnico', 'Fecha', 'Hora local', 'Duración', 'Zona horaria']) {
      expect(within(dialog).getByLabelText(label)).toBeInTheDocument();
    }
    expect(form?.querySelectorAll('.agenda-create-form__leading-icon').length).toBeGreaterThanOrEqual(4);
    expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveClass('btn--secondary');
    expect(within(dialog).getByRole('button', { name: 'Crear visita' })).toHaveClass('btn--primary');
    expect(identityRow).toMatch(/grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
    expect(leadingIcon).toMatch(/position:\s*absolute/);
  });

  it('keeps calendar day and register surfaces aligned by CSS contract', () => {
    const stylesheet = readFileSync(join(__dirname, '../primitives/primitives.css'), 'utf8');
    const day = stylesheet.match(/\.agenda-calendar__day\s*\{([^}]*)\}/)?.[1] ?? '';
    const cell = stylesheet.match(/\.agenda-calendar__cell\s*,\s*\.agenda-calendar__empty\s*\{([^}]*)\}/)?.[1] ?? '';
    const calendar = stylesheet.match(/\.agenda-calendar\s*\{([^}]*)\}/)?.[1] ?? '';
    const register = stylesheet.match(/\.agenda-page__section\s*\{([^}]*)\}/)?.[1] ?? '';
    const count = stylesheet.match(/\.agenda-calendar__count\s*\{([^}]*)\}/)?.[1] ?? '';
    const today = stylesheet.match(/\.agenda-calendar__day\[aria-current="date"\]\s*\{([^}]*)\}/)?.[1] ?? '';
    expect(day).toMatch(/background:\s*var\(--(?!corp-surface\b)[\w-]+\)/);
    expect(day).toMatch(/height:\s*[^;]+/);
    expect(day).toMatch(/padding:\s*var\(--space-1\)/);
    expect(cell).toMatch(/height:\s*[^;]+/);
    expect(stylesheet).toMatch(/\.agenda-calendar\s*\{[^}]*background:\s*var\(--brand-bg-elevated\)/s);
    expect(today).toMatch(/outline|box-shadow|border/);
    expect(stylesheet).toMatch(/\.agenda-calendar__day\[aria-pressed="true"\]\s*\{[^}]*border-color:[^}]*box-shadow:\s*inset[^}]*var\(--brand-lime\)/s);
    expect(count).toMatch(/white-space:\s*normal/);
    expect(count).not.toMatch(/overflow:\s*hidden|text-overflow:\s*ellipsis/);
    expect(calendar).toMatch(/padding:\s*var\(--space-4\)/);
    expect(calendar).toMatch(/border-radius:\s*var\(--radius-lg\)/);
    expect(calendar).toMatch(/background:\s*var\(--brand-bg-elevated\)/);
    expect(calendar).not.toMatch(/box-shadow:/);
    expect(stylesheet).toMatch(/\.agenda-calendar__table\s*\{[^}]*min-width:\s*calc\(var\(--space-8\) \* 10\)/s);
    expect(register).toMatch(/padding:\s*var\(--space-4\)/);
    expect(register).toMatch(/border-radius:\s*var\(--radius-lg\)/);
    expect(register).toMatch(/background:\s*var\(--brand-bg-elevated\)/);
    expect(register).not.toMatch(/box-shadow:/);
    expect(stylesheet).toMatch(/\.agenda-page__visit-card\s*\{[^}]*background:\s*var\(--surface\)/s);
  });

  it('spaces the selected-day heading and today badge with a tokenized gap', () => {
    const stylesheet = readFileSync(join(__dirname, '../primitives/primitives.css'), 'utf8');
    const heading = stylesheet.match(/\.agenda-page__section-heading\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(heading).toMatch(/display:\s*flex/);
    expect(heading).toMatch(/gap:\s*var\(--space-3\)/);
  });

  it('shows a labelled empty state and keeps the table wrapper mobile-safe', () => {
    const { container } = render(<AgendaPage data={[]} state="empty" />);
    expect(screen.getByText('No hay visitas')).toBeInTheDocument();
    expect(container.querySelector('.agenda-page__table-wrap')).not.toBeInTheDocument();
    // Creation is an approved control since the agenda-booking unit. Edit, reschedule and
    // availability remain deliberately absent, so the guard keeps forbidding those.
    expect(screen.queryByText(/editar|reagendar/i)).not.toBeInTheDocument();
  });

  it('offers cancellation only for booked rows and refreshes after confirming a reason', async () => {
    const user = userEvent.setup();
    const cancelled = appointment({ status: 'cancelled' });
    vi.mocked(cancelAppointment).mockResolvedValue({ ok: true, appointment: cancelled });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [cancelled] });

    render(<AgendaPage data={[appointment()]} state="ready" />);
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Cancelar visita' }));
    expect(screen.getByRole('dialog', { name: 'Cancelar visita de Camila Soto — Mantención' })).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveTextContent('La visita se marcará como cancelada y esta agenda no ofrece volver a reservarla.');
    expect(screen.getByLabelText('Motivo de cancelación')).toHaveClass('field__control');
    await user.type(screen.getByLabelText('Motivo de cancelación'), 'Cliente avisó');
    await user.click(screen.getByRole('button', { name: 'Confirmar cancelación' }));

    await waitFor(() => expect(cancelAppointment).toHaveBeenCalledWith(1, 'Cliente avisó'));
    await waitFor(() => expect(listAppointments).toHaveBeenCalled());
    await user.click(screen.getByRole('tab', { name: 'No activas' }));
    expect(await screen.findByText('Cancelada')).toBeInTheDocument();
  });

  it('does not offer cancellation or issue a request for non-booked rows', async () => {
    render(<AgendaPage data={[appointment({ status: 'completed' }), appointment({ id: 2, status: 'no_show' }), appointment({ id: 3, status: 'cancelled' })]} state="ready" />);
    await userEvent.setup().click(screen.getByRole('tab', { name: 'No activas' }));
    expect(screen.getAllByText('Mantención')).toHaveLength(3);
    expect(screen.queryByRole('menuitem', { name: 'Cancelar visita' })).not.toBeInTheDocument();
    expect(cancelAppointment).not.toHaveBeenCalled();
  });

  it('closes booked visits with confirmation, feedback, and register refresh', async () => {
    const user = userEvent.setup();
    const completed = appointment({ status: 'completed' });
    vi.mocked(closeAppointment).mockResolvedValue({ ok: true, appointment: completed });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [completed] });
    render(<AgendaPage data={[appointment()]} state="ready" />);

    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Cerrar visita' }));
    await user.click(screen.getByRole('button', { name: 'Completar' }));
    await waitFor(() => expect(closeAppointment).toHaveBeenCalledWith(1, 'completed'));
    await waitFor(() => expect(listAppointments).toHaveBeenCalled());
    expect(await screen.findByText('Visita completada')).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'No activas' }));
    expect(screen.getByText('Completada')).toBeInTheDocument();
  });

  it('sends no-show outcome and shows actionable failure feedback', async () => {
    const user = userEvent.setup();
    vi.mocked(closeAppointment).mockRejectedValue(new Error('Intenta nuevamente'));
    render(<AgendaPage data={[appointment()]} state="ready" />);
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Cerrar visita' }));
    await user.click(screen.getByRole('button', { name: 'No asistió' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Intenta nuevamente');
    expect(closeAppointment).toHaveBeenCalledWith(1, 'no_show');
  });

  it('does not show close actions for terminal visits', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[appointment({ status: 'completed' })]} state="ready" />);
    await user.click(screen.getByRole('tab', { name: 'No activas' }));
    expect(screen.queryByRole('menuitem', { name: 'Cerrar visita' })).not.toBeInTheDocument();
    expect(closeAppointment).not.toHaveBeenCalled();
  });

  it('opens the reschedule dialog with the booked row slot and submits the complete replacement', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 30, username: 'Luis' }] });
    vi.mocked(rescheduleAppointment).mockResolvedValue({ ok: true, appointment: {} });
    render(<AgendaPage data={[appointment()]} state="ready" />);
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Reprogramar' }));
    await waitFor(() => expect(fetchTechnicians).toHaveBeenCalledOnce());
    const dialog = screen.getByRole('dialog', { name: 'Reprogramar visita' });
    expect(dialog.querySelector('.dialog__icon svg')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('Actualiza la fecha, el horario y el técnico asignado.');
    expect(within(dialog).getByRole('heading', { name: 'Programación actual' })).toBeInTheDocument();
    expect(dialog).toHaveTextContent('10:00');
    expect(dialog).toHaveTextContent('60 min');
    expect(dialog).toHaveTextContent('Luis Pérez');
    expect(within(dialog).getByRole('heading', { name: 'Nueva programación' })).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Fecha')).toHaveValue('2026-09-05');
    expect(within(dialog).getByLabelText('Hora local')).toHaveValue('10:00');
    expect(within(dialog).getByLabelText('Duración')).toHaveValue(60);
    expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toBeInTheDocument();
    expect(dialog).toHaveTextContent('La fecha y la hora corresponden al horario local de la agenda.');
    await user.click(screen.getByRole('button', { name: 'Confirmar reprogramación' }));
    await waitFor(() => expect(rescheduleAppointment).toHaveBeenCalledWith(1, { local_date: '2026-09-05', local_time: '10:00:00', timezone: 'America/Santiago', duration_minutes: 60, technician_id: 30 }));
  });

  it('refuses a replacement slot with no technician instead of sending an unlinked slot', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [] });
    render(<AgendaPage data={[appointment({ technician_id: null })]} state="ready" />);
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Reprogramar' }));
    await user.click(screen.getByRole('button', { name: 'Confirmar reprogramación' }));
    expect(rescheduleAppointment).not.toHaveBeenCalled();
    expect(within(screen.getByRole('dialog', { name: 'Reprogramar visita' })).getByRole('alert')).toHaveTextContent('Completa todos los campos');
  });

  it('tells the operator when the technician lookup fails while opening the reschedule dialog', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchTechnicians).mockRejectedValue(new Error('Sin conexión'));
    render(<AgendaPage data={[appointment()]} state="ready" />);
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Reprogramar' }));
    const dialog = screen.getByRole('dialog', { name: 'Reprogramar visita' });
    const alert = await within(dialog).findByRole('alert');
    expect(alert).toHaveTextContent('No pudimos cargar las opciones de la visita');
    expect(alert).toHaveTextContent('Sin conexión');
    expect(rescheduleAppointment).not.toHaveBeenCalled();
  });

  it('separates active and non-active visits in a keyboard-operable client-side register view', async () => {
    const user = userEvent.setup();
    const rows = [appointment(), appointment({ id: 2, status: 'cancelled', service: 'Cancelled service' }), appointment({ id: 3, status: 'completed', service: 'Completed service' }), appointment({ id: 4, status: 'no_show', service: 'No-show service' })];
    render(<AgendaPage data={rows} state="ready" />);

    expect(screen.getByRole('tab', { name: 'Activas' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Mantención')).toBeInTheDocument();
    expect(screen.queryByText('Cancelled service')).not.toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'Activas' }));
    await user.keyboard('{ArrowRight}');
    expect(screen.getByText('Cancelled service')).toBeInTheDocument();
    expect(screen.getByText('Completed service')).toBeInTheDocument();
    expect(screen.getByText('No-show service')).toBeInTheDocument();
    expect(screen.queryByText('Mantención')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Visitas no activas', level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Hoy' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Próximas' })).not.toBeInTheDocument();
  });

  it('does not issue a request when switching register views', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[appointment()]} state="ready" />);
    vi.mocked(listAppointments).mockClear();
    await user.click(screen.getByRole('tab', { name: 'No activas' }));
    expect(listAppointments).not.toHaveBeenCalled();
  });

  it('shows the labelled empty state when the selected register view has no rows', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[appointment()]} state="ready" />);
    await user.click(screen.getByRole('tab', { name: 'No activas' }));
    expect(screen.getByText('No hay visitas')).toBeInTheDocument();
  });

  it('does not offer cancellation for completed, no-show, or cancelled visits in the non-active view', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[appointment({ status: 'completed' }), appointment({ id: 2, status: 'no_show' }), appointment({ id: 3, status: 'cancelled' })]} state="ready" />);
    await user.click(screen.getByRole('tab', { name: 'No activas' }));
    expect(screen.getAllByText('Mantención')).toHaveLength(3);
    expect(screen.queryByRole('menuitem', { name: 'Cancelar visita' })).not.toBeInTheDocument();
    expect(cancelAppointment).not.toHaveBeenCalled();
    expect(screen.queryByRole('menuitem', { name: 'Reprogramar' })).not.toBeInTheDocument();
    expect(rescheduleAppointment).not.toHaveBeenCalled();
  });

  it('retries pending and failed calendar sync from keyboard-operable actions', async () => {
    const user = userEvent.setup();
    vi.mocked(retryCalendarSync).mockResolvedValue({ ok: true, calendar: { status: 'synced', error: null } });
    render(<AgendaPage data={[appointment({ sync: { status: 'failed', error: 'Proveedor no disponible', retry: true } }), appointment({ id: 2, sync: { status: 'pending', error: null, retry: true } }), appointment({ id: 3 })]} state="ready" />);

    expect(screen.getAllByText(appointmentStatusLabel('booked'))).toHaveLength(3);
    expect(screen.getByText(appointmentSyncLabel('failed'))).toBeInTheDocument();
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Reintentar calendario' }));
    await waitFor(() => expect(retryCalendarSync).toHaveBeenCalledWith(1));
    await waitFor(() => expect(listAppointments).toHaveBeenCalled());
  });

  it('shows actionable inline mutation failures without changing the row', async () => {
    const user = userEvent.setup();
    vi.mocked(cancelAppointment).mockRejectedValue(new Error('No se pudo cancelar'));
    render(<AgendaPage data={[appointment()]} state="ready" />);
    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Cancelar visita' }));
    await user.click(screen.getByRole('button', { name: 'Confirmar cancelación' }));

    expect(await screen.findByRole('dialog')).toHaveTextContent('No se pudo cancelar');
    expect(screen.getByText(appointmentStatusLabel('booked'))).toBeInTheDocument();
  });

  it('shows sync retry failures beside the row action', async () => {
    const user = userEvent.setup();
    vi.mocked(retryCalendarSync).mockRejectedValue(new Error('Calendario no disponible'));
    render(<AgendaPage data={[appointment({ sync: { status: 'failed', error: null, retry: true } })]} state="ready" />);

    await openVisitActions(user);
    await user.click(screen.getByRole('menuitem', { name: 'Reintentar calendario' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Calendario no disponible');
    expect(document.querySelector('.agenda-page__visit-card')).toHaveTextContent('Calendario no disponible');
    expect(screen.getByRole('alert').querySelector('h2')).not.toBeInTheDocument();
  });

  it('uses the visible month as the fetch window and navigates to the next month', async () => {
    const user = userEvent.setup();
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });
    render(<AgendaPage timezone="America/Santiago" />);

    await waitFor(() => expect(listAppointments).toHaveBeenCalledWith('2026-09-01', '2026-09-30', 'America/Santiago'));
    await user.click(screen.getByRole('button', { name: 'Período siguiente' }));
    await waitFor(() => expect(listAppointments).toHaveBeenCalledWith('2026-10-01', '2026-10-31', 'America/Santiago'));
  });

  it('filters the register by selected day and restores sections when cleared', async () => {
    const user = userEvent.setup();
    const tomorrow = appointment({ id: 2, service: 'Instalación', local_start: '2026-09-06T09:00:00-04:00' });
    render(<AgendaPage data={[appointment(), tomorrow]} state="ready" timezone="America/Santiago" />);

    await user.click(screen.getByRole('button', { name: /^Sábado 5 de septiembre,/ }));
    const selectedHeading = screen.getByRole('heading', { name: 'Sábado 5 de septiembre Hoy', level: 2 });
    expect(selectedHeading.querySelector('.badge')).toHaveTextContent('Hoy');
    expect(screen.getByText('Mantención')).toBeInTheDocument();
    expect(screen.queryByText('Instalación')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Sábado 5 de septiembre,/ }));
    const restoredHeading = screen.getByRole('heading', { name: /Sábado 5 de septiembre Hoy/i, level: 2 });
    expect(restoredHeading.querySelector('.badge')).toHaveTextContent('Hoy');
  });

  it('shows the explicit empty state when the selected day has no visits', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[appointment()]} state="ready" timezone="America/Santiago" />);

    await user.click(screen.getByRole('button', { name: /^Domingo 6 de septiembre,/ }));

    expect(screen.getByText('No hay visitas')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Calendario de Septiembre de 2026' })).toBeInTheDocument();
  });

  it('shows the explicit empty state when today has no current or upcoming visits', () => {
    render(<AgendaPage data={[appointment({ local_start: '2026-09-04T10:00:00-04:00' })]} state="ready" timezone="America/Santiago" />);

    expect(screen.getByText('No hay visitas')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Calendario de Septiembre de 2026' })).toBeInTheDocument();
  });

  it('uses a single period section after navigating outside the current day', async () => {
    const user = userEvent.setup();
    vi.mocked(listAppointments)
      .mockResolvedValueOnce({ appointments: [appointment()] })
      .mockResolvedValue({ appointments: [appointment({ id: 2, service: 'Instalación', local_start: '2026-10-06T09:00:00-03:00' })] });
    render(<AgendaPage timezone="America/Santiago" />);

    await waitFor(() => expect(screen.getByText('Mantención')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Período siguiente' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Visitas del período', level: 2 })).toBeInTheDocument());
    expect(screen.getByText('Instalación')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Hoy', level: 2 })).not.toBeInTheDocument();
  });

  it('shows the existing empty state when the visible period has no rows', async () => {
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });
    render(<AgendaPage timezone="America/Santiago" />);

    expect(await screen.findByText('No hay visitas')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Calendario de Septiembre de 2026' })).toBeInTheDocument();
  });

  it('creates an appointment from the agenda and refreshes the visible period', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ id: 10, name: 'Camila Soto' }] as never });
    vi.mocked(fetchCases).mockResolvedValue({ cases: [{ id: 20, service: 'Mantención', customer: { id: 10, name: 'Camila Soto' } }] as never, users: [] });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 30, username: 'Luis' }] });
    vi.mocked(createAppointment).mockResolvedValue({ ok: true, appointment: {} as never });
    vi.mocked(listAppointments).mockResolvedValue({ appointments: [] });

    render(<AgendaPage data={[]} state="empty" timezone="America/Santiago" />);
    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    await waitFor(() => expect(fetchTechnicians).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Nueva visita' })).toBeInTheDocument());
    expect(screen.getByRole('dialog')).toHaveTextContent('Completa los datos para agendar una visita.');
    expect(screen.getByRole('dialog')).toHaveTextContent('Datos de la visita');
    expect(screen.getByRole('dialog')).toHaveTextContent('Fecha y horario');
    expect(screen.getByRole('heading', { name: 'Datos de la visita', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Fecha y horario', level: 3 })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Cliente'), '10');
    await user.type(screen.getByLabelText('Caso vinculado'), 'Mantención');
    await user.click(screen.getByRole('option', { name: 'Mantención (#20)' }));
    await user.selectOptions(screen.getByLabelText('Técnico'), '30');
    await user.type(screen.getByLabelText('Servicio'), 'Maintenance');
    await user.clear(screen.getByLabelText('Fecha'));
    await user.type(screen.getByLabelText('Fecha'), '2026-09-05');
    await user.clear(screen.getByLabelText('Hora local'));
    await user.type(screen.getByLabelText('Hora local'), '10:00');
    await user.clear(screen.getByLabelText('Duración'));
    await user.type(screen.getByLabelText('Duración'), '60');
    await user.click(screen.getByRole('button', { name: 'Crear visita' }));

    await waitFor(() => expect(createAppointment).toHaveBeenCalledWith(expect.objectContaining({ customer_id: 10, case_id: 20, technician_id: 30, timezone: 'America/Santiago', local_time: '10:00:00' })));
    await waitFor(() => expect(listAppointments).toHaveBeenCalled());
  }, 15000);

  it('closes the new-visit dialog when cancelling', async () => {
    const user = userEvent.setup();
    render(<AgendaPage data={[]} state="empty" />);

    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    expect(await screen.findByRole('dialog', { name: 'Nueva visita' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(screen.queryByRole('dialog', { name: 'Nueva visita' })).not.toBeInTheDocument();
  });

  it('shows validation instead of throwing when the selected case has no service', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ id: 10, name: 'Camila Soto' }] as never });
    vi.mocked(fetchCases).mockResolvedValue({ cases: [{ id: 20, service: null, customer: { id: 10, name: 'Camila Soto' } }] as never, users: [] });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 30, username: 'Luis' }] });
    vi.mocked(createAppointment).mockResolvedValue({ ok: true, appointment: {} as never });

    render(<AgendaPage data={[]} state="empty" timezone="America/Santiago" />);
    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Nueva visita' })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText('Cliente'), '10');
    await user.type(screen.getByLabelText('Caso vinculado'), 'Caso sin servicio');
    await user.click(screen.getByRole('option', { name: 'Caso sin servicio (#20)' }));
    expect(screen.getByLabelText('Servicio')).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Caso vinculado' })).toHaveValue('Caso sin servicio (#20)');
    expect(screen.getByRole('combobox', { name: 'Caso vinculado' })).not.toHaveValue(expect.stringContaining('null'));
    const form = screen.getByLabelText('Cliente').closest('.agenda-create-form');
    expect(form).toBeInTheDocument();
    expect(form?.children.length).toBeGreaterThan(1);
    const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    expect(css).toMatch(/\.agenda-create-form\s*\{[^}]*display:\s*grid;[^}]*gap:\s*var\(--space-3\)/s);
    await user.selectOptions(screen.getByLabelText('Técnico'), '30');
    await user.clear(screen.getByLabelText('Fecha'));
    await user.type(screen.getByLabelText('Fecha'), '2026-09-05');
    await user.clear(screen.getByLabelText('Hora local'));
    await user.type(screen.getByLabelText('Hora local'), '10:00');
    await user.click(screen.getByRole('button', { name: 'Crear visita' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Completa todos los campos de la visita');
    expect(createAppointment).not.toHaveBeenCalled();
  });

  it('creates and selects a manual case inline, then uses it to create the visit', async () => {
    const user = userEvent.setup();
    const createdCase = { id: 21, service: 'Instalación', customer_id: 10 };
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ id: 10, name: 'Camila Soto' }] as never });
    vi.mocked(fetchCases).mockResolvedValue({ cases: [] as never, users: [] });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 30, username: 'Luis' }] });
    vi.mocked(createCase).mockResolvedValue({ ok: true, case: createdCase as never });
    vi.mocked(createAppointment).mockResolvedValue({ ok: true, appointment: {} as never });

    render(<AgendaPage data={[]} state="empty" timezone="America/Santiago" />);
    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Nueva visita' })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText('Cliente'), '10');
    const caseInput = screen.getByRole('combobox', { name: 'Caso vinculado' });
    await user.type(caseInput, 'Instalación');
    expect(screen.getByRole('option', { name: 'Crear «Instalación»' })).toBeInTheDocument();
    await user.click(screen.getByRole('option', { name: 'Crear «Instalación»' }));

    expect(createCase).toHaveBeenCalledWith({ customer_id: 10, service: 'Instalación' });
    await waitFor(() => expect(caseInput).toHaveValue('Instalación (#21)'));
    expect(screen.getByLabelText('Servicio')).toHaveValue('Instalación');
    await user.selectOptions(screen.getByLabelText('Técnico'), '30');
    await user.clear(screen.getByLabelText('Fecha'));
    await user.type(screen.getByLabelText('Fecha'), '2026-09-05');
    await user.click(screen.getByRole('button', { name: 'Crear visita' }));
    await waitFor(() => expect(createAppointment).toHaveBeenCalledWith(expect.objectContaining({ customer_id: 10, case_id: 21, service: 'Instalación' })));
  });

  it('does not create a manual case twice while the first request is pending', async () => {
    const user = userEvent.setup();
    let resolveCreateCase!: (value: { ok: true; case: never }) => void;
    vi.mocked(fetchClients).mockResolvedValue({ clients: [{ id: 10, name: 'Camila Soto' }] as never });
    vi.mocked(fetchCases).mockResolvedValue({ cases: [] as never, users: [] });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [] });
    vi.mocked(createCase).mockReturnValue(new Promise((resolve) => { resolveCreateCase = resolve; }) as never);

    render(<AgendaPage data={[]} state="empty" />);
    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Nueva visita' })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText('Cliente'), '10');
    const caseInput = screen.getByRole('combobox', { name: 'Caso vinculado' });
    await user.type(caseInput, 'Instalación');
    const createOption = screen.getByRole('option', { name: 'Crear «Instalación»' });
    await user.click(createOption);
    await waitFor(() => expect(createCase).toHaveBeenCalledTimes(1));
    await user.click(caseInput);
    const repeatedCreateOption = screen.queryByRole('option', { name: 'Crear «Instalación»' });
    if (repeatedCreateOption) await user.click(repeatedCreateOption);
    expect(createCase).toHaveBeenCalledTimes(1);

    resolveCreateCase({ ok: true, case: { id: 21, service: 'Instalación', customer_id: 10 } as never });
    await waitFor(() => expect(caseInput).toHaveValue('Instalación (#21)'));
  });

  it('requires a customer before creating a manual case', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchClients).mockResolvedValue({ clients: [] as never });
    vi.mocked(fetchCases).mockResolvedValue({ cases: [] as never, users: [] });
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [] });
    render(<AgendaPage data={[]} state="empty" />);
    await user.click(screen.getByRole('button', { name: 'Nueva visita' }));
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Nueva visita' })).toBeInTheDocument());
    await user.type(screen.getByRole('combobox', { name: 'Caso vinculado' }), 'Instalación');
    await user.click(screen.getByRole('option', { name: 'Crear «Instalación»' }));
    expect(createCase).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent(/cliente/i);
  });

  it('keeps the agenda calendar CSS contract aligned with the design system', () => {
    const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    expect(css).not.toMatch(/\.agenda-calendar__weekday\s*\{[^}]*text-transform:\s*uppercase/s);
    expect(css).toMatch(/\.agenda-calendar\s*\{[^}]*border-radius:\s*var\(--radius-lg\)/s);
  });

  it('keeps the agenda desktop track minimum in text-zoom-immune pixels', () => {
    const css = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    expect(css).toMatch(/@media\s*\(min-width:\s*64rem\)[\s\S]*?\.agenda-page__layout\s*\{[^}]*grid-template-columns:\s*minmax\(320px,\s*1fr\)\s+minmax\(0,\s*1\.35fr\)/s);
  });
});
