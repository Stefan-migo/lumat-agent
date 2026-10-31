import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { AppointmentDetail } from './AppointmentDetail';
import { ToastProvider } from '../primitives/Toast';
import type { AppointmentDetail as AppointmentDetailData } from '../../types';
import { closeAppointment, closeTechnicianAppointment, fetchTechnicians, fetchUsers, getAppointment, getTechnicianAppointment, rescheduleAppointment, sendTechnicianQuickAction } from '../../api';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// Spread the real module so `ApiError` (used for the quick-action error codes)
// stays a real class; only the network functions are stubbed.
vi.mock('../../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api')>()),
  getAppointment: vi.fn(),
  getTechnicianAppointment: vi.fn(),
  closeAppointment: vi.fn(),
  closeTechnicianAppointment: vi.fn(),
  sendTechnicianQuickAction: vi.fn(),
  fetchTechnicians: vi.fn(),
  fetchUsers: vi.fn(),
  rescheduleAppointment: vi.fn(),
}));

const detail: AppointmentDetailData = {
  appointment: {
    id: 7, service: 'Reparación de calefón', customer_id: 2, case_id: 3, technician_id: 4,
    local_start: '2026-09-26T10:00:00', timezone: 'America/Santiago', starts_at: '2026-09-26T13:00:00Z',
    ends_at: '2026-09-26T14:00:00Z', duration_minutes: 60, status: 'booked',
    history: [
      { id: 9, actor: 'ana', action: 'created', from_status: null, to_status: 'booked', details: { source: 'panel', reason: 'Cliente solicitó revisión' }, created_at: '2026-09-25T12:00:00Z' },
      { id: 10, actor: 'ana', action: 'rescheduled', from_status: 'booked', to_status: 'booked', details: { from_start: '2026-09-26T10:00:00', to_start: '2026-09-27T11:30:00', from_technician_id: 3, to_technician_id: 4 }, created_at: '2026-09-25T13:00:00Z' },
    ],
  },
  customer: { id: 2, name: 'Ana', address: 'Av. Los Pinos 55', comuna: 'Providencia' },
  case: { id: 3, conversation_id: null },
  conversation_summary: null,
};

describe('AppointmentDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [] });
  });

  it('offers confirmed outcomes for booked appointments and reports success', async () => {
    const user = userEvent.setup();
    vi.mocked(closeAppointment).mockResolvedValue({ ok: true, appointment: {} });
    render(<ToastProvider><AppointmentDetail data={detail} /></ToastProvider>);
    await user.click(screen.getByRole('button', { name: 'Cerrar visita' }));
    const dialog = screen.getByRole('dialog', { name: 'Cerrar visita' });
    expect(dialog.querySelector('.dialog__icon svg')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('Selecciona el resultado de la visita.');
    expect(dialog).toHaveTextContent('Ana');
    expect(dialog).toHaveTextContent('Visita seleccionada');
    expect(screen.getByRole('radio', { name: /Completada.*La visita se realizó/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /No completada.*La visita no se completó/ })).not.toBeChecked();
    expect(dialog).toHaveTextContent('Este cierre no se puede revertir desde la agenda.');
    await user.click(screen.getByRole('button', { name: 'Confirmar cierre' }));
    await waitFor(() => expect(closeAppointment).toHaveBeenCalledWith(7, 'completed'));
    expect(await screen.findByRole('status')).toHaveTextContent('Visita completada');
    expect(document.querySelector('.toast-region')).toHaveTextContent('Visita completada');
    expect(screen.queryByText('Visita completada', { selector: '.state-message__title' })).not.toBeInTheDocument();
  });

  it('supports no-show and surfaces failure; terminal visits have no outcome action', async () => {
    const user = userEvent.setup();
    vi.mocked(closeAppointment).mockRejectedValue(new Error('Intenta nuevamente'));
    render(<AppointmentDetail data={detail} />);
    await user.click(screen.getByRole('button', { name: 'Cerrar visita' }));
    await user.click(screen.getByRole('radio', { name: /No completada.*La visita no se completó/ }));
    await user.click(screen.getByRole('button', { name: 'Confirmar cierre' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Intenta nuevamente');
    expect(closeAppointment).toHaveBeenCalledWith(7, 'no_show');

    cleanup();
    render(<AppointmentDetail data={{ ...detail, appointment: { ...detail.appointment, status: 'completed' } }} />);
    expect(screen.queryByRole('button', { name: 'Cerrar visita' })).not.toBeInTheDocument();
  });

  it('renders the redesigned visit header, information cards, and event timeline', () => {
    render(<AppointmentDetail data={detail} />);

    expect(screen.getByRole('heading', { name: 'Reparación de calefón' })).toBeInTheDocument();
    expect(screen.queryByText('DETALLE DE VISITA')).not.toBeInTheDocument();
    expect(screen.getByText('Información y seguimiento de la visita.')).toBeInTheDocument();
    const backButton = screen.getByRole('button', { name: 'Volver a agenda' });
    expect(backButton).toHaveClass('btn', 'btn--secondary');
    expect(backButton.closest('.page-header__actions')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reprogramar' }).closest('.page-header__actions')).toBe(backButton.closest('.page-header__actions'));
    expect(screen.getByRole('link', { name: /Ver ficha del cliente/ })).toHaveAttribute('href', '/panel/app/clients/2');
    expect(screen.getByRole('heading', { name: 'Programación' })).toBeInTheDocument();
    const schedule = screen.getByRole('heading', { name: 'Programación' }).closest('.card');
    expect(within(schedule as HTMLElement).getByText('Dirección')).toBeInTheDocument();
    const addressLink = within(schedule as HTMLElement).getByRole('link', { name: 'Av. Los Pinos 55, Providencia' });
    expect(addressLink).toHaveAttribute('href', 'https://www.google.com/maps/search/?api=1&query=Av.%20Los%20Pinos%2055%2C%20Providencia');
    expect(addressLink).toHaveClass('address-link');
    expect(screen.getByRole('heading', { name: 'Técnico asignado' })).toBeInTheDocument();
    expect(screen.getByText('Técnico #4')).toBeInTheDocument();
    const peopleCard = screen.getByRole('heading', { name: 'Cliente' }).closest('.appointment-detail__people');
    expect(peopleCard).toBeInTheDocument();
    expect(peopleCard?.querySelectorAll('.appointment-detail__identity')).toHaveLength(2);
    expect(peopleCard?.querySelectorAll('.appointment-detail__summary-row')).toHaveLength(2);
    expect(document.querySelectorAll('.appointment-detail__summary.card')).toHaveLength(0);
    expect(peopleCard?.querySelector('.appointment-detail__summary h3')).toHaveTextContent('Resumen');
    expect(peopleCard?.querySelectorAll('.avatar')).toHaveLength(2);
    expect(screen.getAllByText('Reservada')).toHaveLength(2);
    expect(screen.queryByText('Resumen de la conversación')).not.toBeInTheDocument();
    const history = screen.getByRole('list', { name: 'Historial de la visita' });
    expect(history).toHaveTextContent('Visita reservada');
    expect(history).toHaveTextContent('Registro inicial');
    const disclosures = within(history).getAllByText('Ver detalles');
    expect(disclosures).toHaveLength(2);
    expect(history.querySelector('pre')).not.toBeInTheDocument();
    expect(history).toHaveTextContent('Origen');
    expect(history).toHaveTextContent('panel');
    expect(history).toHaveTextContent('Motivo');
    expect(history).toHaveTextContent('Cliente solicitó revisión');
    expect(history).toHaveTextContent('Responsable');
    expect(history).toHaveTextContent('Estado');
    expect(history).toHaveTextContent('Visita reprogramada');
    expect(history).toHaveTextContent('Hora anterior');
    expect(history).toHaveTextContent('Nueva hora');
    expect(history).toHaveTextContent('Técnico anterior (ID)');
    expect(history).toHaveTextContent('Técnico #3 (ID no resuelto)');
    expect(history).toHaveTextContent('Técnico #4 (ID no resuelto)');
    expect(history).not.toHaveTextContent('rescheduled');
    expect(history).not.toHaveTextContent('2026-09-26T10:00:00');
    expect(history).not.toHaveTextContent(/\bbooked\b/);
    expect(history.querySelector('time')).toHaveAttribute('dateTime', '2026-09-25T12:00:00Z');
  });

  it('shows the missing-address fallback in the schedule card', () => {
    render(<AppointmentDetail data={{ ...detail, customer: { ...detail.customer, address: null, comuna: null } }} />);
    expect(screen.getByText('Dirección no registrada')).toBeInTheDocument();
  });

  it('resolves the assigned technician username asynchronously and keeps the fallback on lookup failure', async () => {
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [{ id: 4, username: 'jperez' }] });
    const { unmount } = render(<AppointmentDetail data={detail} />);

    expect(screen.getByText('Técnico #4')).toBeInTheDocument();
    expect(await screen.findAllByText('jperez')).toHaveLength(2);
    expect(screen.queryByText('Técnico #4')).not.toBeInTheDocument();

    unmount();
    vi.mocked(fetchTechnicians).mockRejectedValue(new Error('Lookup unavailable'));
    render(<AppointmentDetail data={detail} />);
    expect(screen.getByText('Técnico #4')).toBeInTheDocument();
    await waitFor(() => expect(fetchTechnicians).toHaveBeenCalled());
    expect(screen.getByText('Técnico #4')).toBeInTheDocument();
  });

  it('resolves technician IDs in reschedule history details', async () => {
    vi.mocked(fetchTechnicians).mockResolvedValue({ technicians: [
      { id: 3, username: 'luis' },
      { id: 4, username: 'jperez' },
    ] });
    render(<AppointmentDetail data={detail} />);

    const history = screen.getByRole('list', { name: 'Historial de la visita' });
    expect(await within(history).findByText('luis')).toBeInTheDocument();
    expect(within(history).getByText('jperez')).toBeInTheDocument();
    expect(history).not.toHaveTextContent('ID no resuelto');
  });

  it('separates the history title and connects event icons with a timeline rule', () => {
    const stylesheet = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    const header = stylesheet.match(/\.appointment-detail__history \.card__header\s*\{([^}]*)\}/)?.[1] ?? '';
    const connector = stylesheet.match(/\.appointment-detail__history li:not\(:last-child\)::before\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(header).toMatch(/border-bottom:\s*1px solid var\(--border\)/);
    expect(header).toMatch(/padding-bottom:\s*var\(--space-3\)/);
    expect(connector).toMatch(/content:\s*""/);
    expect(connector).toMatch(/background:\s*var\(--border\)/);
  });

  it('places the schedule and history on the left with one sidebar card on the right', () => {
    const stylesheet = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    const desktopGrid = stylesheet.match(/\.appointment-detail-page \.detail-region\s*\{([^}]*)\}/)?.[1] ?? '';
    const schedule = stylesheet.match(/\.appointment-detail__schedule\s*\{([^}]*)\}/)?.[1] ?? '';
    const history = stylesheet.match(/\.appointment-detail__history\s*\{([^}]*)\}/)?.[1] ?? '';
    const people = stylesheet.match(/\.appointment-detail__people\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(desktopGrid).toMatch(/grid-template-columns:\s*minmax\(0,\s*2fr\)\s+minmax\(16rem,\s*1fr\)/);
    expect(desktopGrid).toMatch(/grid-template-areas:\s*"schedule people"\s+"history people"/);
    expect(schedule).toMatch(/grid-area:\s*schedule/);
    expect(history).toMatch(/grid-area:\s*history/);
    expect(people).toMatch(/grid-area:\s*people/);
    expect(stylesheet).toMatch(/@media \(max-width:\s*63\.99rem\)[\s\S]*?grid-template-areas:\s*"schedule"\s+"people"\s+"history"/);
  });

  it('uses larger token-sized avatars in the visit identity card', () => {
    const stylesheet = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    const identityAvatar = stylesheet.match(/\.appointment-detail__identity \.avatar\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(identityAvatar).toMatch(/width:\s*calc\(var\(--space-8\) \* 2\)/);
    expect(identityAvatar).toMatch(/height:\s*calc\(var\(--space-8\) \* 2\)/);
    expect(identityAvatar).toMatch(/font-size:\s*var\(--text-lg\)/);
  });

  it('keeps detail header copy and actions responsive on mobile', () => {
    const stylesheet = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    const mobileRules = stylesheet.split('@media (max-width: 767px)')[1]?.split('@media')[0] ?? '';
    const copy = mobileRules.match(/\.appointment-detail-page \.page-header__copy\s*\{([^}]*)\}/)?.[1] ?? '';
    const actions = mobileRules.match(/\.appointment-detail-page \.page-header__actions\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(copy).toMatch(/min-width:\s*0/);
    expect(actions).toMatch(/flex-wrap:\s*wrap/);
    expect(actions).toMatch(/width:\s*100%/);
  });

  it('stacks the mobile detail header without letting copy or actions stretch the flex rows', () => {
    const stylesheet = readFileSync(join(process.cwd(), 'src/components/primitives/primitives.css'), 'utf8');
    const mobileRules = stylesheet.split('@media (max-width: 767px)')[1]?.split('@media')[0] ?? '';
    const header = mobileRules.match(/\.appointment-detail-page \.page-header\s*\{([^}]*)\}/)?.[1] ?? '';
    const copy = mobileRules.match(/\.appointment-detail-page \.page-header__copy\s*\{([^}]*)\}/)?.[1] ?? '';
    const actions = mobileRules.match(/\.appointment-detail-page \.page-header__actions\s*\{([^}]*)\}/)?.[1] ?? '';

    expect(header).toMatch(/align-content:\s*flex-start/);
    expect(header).toMatch(/row-gap:\s*var\(--space-3\)/);
    expect(copy).toMatch(/flex:\s*0 1 auto/);
    expect(copy).toMatch(/width:\s*100%/);
    expect(actions).toMatch(/flex:\s*0 0 auto/);
  });

  it('shows a conversation summary only when present', () => {
    render(<AppointmentDetail data={{ ...detail, case: { id: 3, conversation_id: 44 }, conversation_summary: 'El cliente pide una reparación.' }} />);
    expect(screen.getByText('El cliente pide una reparación.')).toBeInTheDocument();
  });

  it('offers rescheduling only for booked appointments', () => {
    const { rerender } = render(<AppointmentDetail data={detail} />);
    expect(screen.getByRole('button', { name: 'Reprogramar' })).toBeInTheDocument();
    rerender(<AppointmentDetail data={{ ...detail, appointment: { ...detail.appointment, status: 'completed' } }} />);
    expect(screen.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument();
  });

  it('defaults and submits a complete replacement slot', async () => {
    const user = userEvent.setup();
    vi.mocked(fetchUsers).mockResolvedValue({ users: [{ id: 4, username: 'Tech', role: 'tecnico', active: true }] as never });
    vi.mocked(rescheduleAppointment).mockResolvedValue({ ok: true, appointment: {} });
    render(<AppointmentDetail data={detail} />);
    await user.click(screen.getByRole('button', { name: 'Reprogramar' }));
    const dialog = screen.getByRole('dialog', { name: 'Reprogramar visita' });
    expect(dialog.querySelector('.dialog__icon svg')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('Actualiza la fecha, el horario y el técnico asignado.');
    expect(within(dialog).getByRole('heading', { name: 'Programación actual' })).toBeInTheDocument();
    expect(dialog).toHaveTextContent('10:00');
    expect(dialog).toHaveTextContent('60 min');
    expect(dialog).toHaveTextContent('Técnico #4');
    expect(within(dialog).getByRole('heading', { name: 'Nueva programación' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument();
    expect(dialog).toHaveTextContent('La fecha y la hora corresponden al horario local de la agenda.');
    expect(dialog.querySelector('input[type="date"]')).toHaveValue('2026-09-26');
    await user.click(screen.getByRole('button', { name: 'Confirmar reprogramación' }));
    await waitFor(() => expect(rescheduleAppointment).toHaveBeenCalledWith(7, {
      local_date: '2026-09-26', local_time: '10:00:00', duration_minutes: 60,
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

describe('AppointmentDetail (technician)', () => {
  /** A fixed clock 5 minutes before `starts_at` (13:00Z): both quick actions are
   *  open (en_route from T-60, arrived from T-15) and the visit is not closed. */
  const FIELD_NOW = new Date('2026-09-26T12:55:00.000Z');
  const technicianDetail: AppointmentDetailData = {
    ...detail,
    appointment: { ...detail.appointment, history: [] },
    conversation_summary: null,
    quick_actions: { en_route: { resend_available_at: null }, arrived: { resend_available_at: null } },
  };
  const withState = (state: 'en_route' | 'arrived', quick_actions = technicianDetail.quick_actions, stateAt: string | null = null): AppointmentDetailData => ({
    ...technicianDetail,
    appointment: { ...technicianDetail.appointment, technician_state: state, technician_state_at: stateAt },
    quick_actions,
  });

  /** S2: the same page, with the operator-only affordances gated by role. */
  it('reads the visit without the operator-only affordances', () => {
    render(<AppointmentDetail data={{ ...technicianDetail, conversation_summary: 'El cliente pide una reparación.' }} role="tecnico" now={FIELD_NOW} />);

    expect(screen.getByRole('heading', { name: 'Reparación de calefón' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Programación' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Cliente' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Ver ficha del cliente/ })).not.toBeInTheDocument();
    expect(screen.queryByText('Resumen de la conversación')).not.toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Historial de la visita' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Volver a agenda' })).toBeInTheDocument();
  });

  it('loads the technician visit from the technician endpoint', async () => {
    vi.mocked(getTechnicianAppointment).mockResolvedValue(technicianDetail);

    render(<AppointmentDetail appointmentId={7} role="tecnico" now={FIELD_NOW} />);

    expect(await screen.findByRole('heading', { name: 'Reparación de calefón' })).toBeInTheDocument();
    expect(getTechnicianAppointment).toHaveBeenCalledWith(7);
    expect(getAppointment).not.toHaveBeenCalled();
    expect(fetchTechnicians).not.toHaveBeenCalled();
  });

  /** S4: the technician closes their own visit; the route is the technician one. */
  it('offers the close action and closes through the technician endpoint', async () => {
    const user = userEvent.setup();
    vi.mocked(closeTechnicianAppointment).mockResolvedValue({ ok: true });
    vi.mocked(getTechnicianAppointment).mockResolvedValue(technicianDetail);

    render(<AppointmentDetail appointmentId={7} role="tecnico" now={FIELD_NOW} />);

    await user.click(await screen.findByRole('button', { name: 'Cerrar visita' }));
    await user.click(screen.getByRole('button', { name: 'Confirmar cierre' }));

    await waitFor(() => expect(closeTechnicianAppointment).toHaveBeenCalledWith(7, 'completed'));
    expect(closeAppointment).not.toHaveBeenCalled();
  });

  /** S5: the two field quick actions, inside their window. */
  it('offers both field quick actions while their windows are open', () => {
    render(<AppointmentDetail data={technicianDetail} role="tecnico" now={FIELD_NOW} />);

    expect(screen.getByRole('heading', { name: 'Avisar al cliente' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Voy en camino' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Llegué / estoy afuera' })).toBeEnabled();
  });

  /** S6: each action opens on its own lead time, not together. */
  it('opens each quick action on its own lead time', () => {
    render(<AppointmentDetail data={technicianDetail} role="tecnico" now={new Date('2026-09-26T12:20:00.000Z')} />);
    expect(screen.getByRole('button', { name: 'Voy en camino' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Llegué / estoy afuera' })).not.toBeInTheDocument();

    cleanup();
    render(<AppointmentDetail data={technicianDetail} role="tecnico" now={new Date('2026-09-26T11:50:00.000Z')} />);
    expect(screen.queryByRole('button', { name: 'Voy en camino' })).not.toBeInTheDocument();
    expect(screen.getByText(/60 minutos antes/)).toBeInTheDocument();
  });

  /** S7: a recent send shows a countdown instead of allowing an instant resend. */
  it('counts down the resend cooldown per action', () => {
    render(<AppointmentDetail
      data={withState('en_route', {
        en_route: { resend_available_at: '2026-09-26T12:57:30.000Z' },
        arrived: { resend_available_at: null },
      })}
      role="tecnico"
      now={FIELD_NOW}
    />);

    expect(screen.getByRole('button', { name: 'Reenviar en 2:30' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Llegué / estoy afuera' })).toBeEnabled();
  });

  /** S5: the axis only moves forward — an action already passed is not offered. */
  it('hides an action the field axis has already passed', () => {
    render(<AppointmentDetail data={withState('arrived')} role="tecnico" now={FIELD_NOW} />);

    expect(screen.queryByRole('button', { name: 'Voy en camino' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Llegué / estoy afuera' })).toBeEnabled();
  });

  /** S8: the send goes through the technician endpoint and refreshes the visit. */
  it('sends a quick action through the technician endpoint and refreshes', async () => {
    const user = userEvent.setup();
    vi.mocked(getTechnicianAppointment).mockResolvedValue(technicianDetail);
    vi.mocked(sendTechnicianQuickAction).mockResolvedValue({ ok: true, technician_state: 'en_route', resend_available_at: '2026-09-26T13:00:00.000Z' });

    render(<ToastProvider><AppointmentDetail appointmentId={7} role="tecnico" now={FIELD_NOW} /></ToastProvider>);
    await user.click(await screen.findByRole('button', { name: 'Voy en camino' }));

    await waitFor(() => expect(sendTechnicianQuickAction).toHaveBeenCalledWith(7, 'en_route'));
    expect(await screen.findByRole('status')).toHaveTextContent('Avisamos que vas en camino');
    expect(document.querySelector('.toast-region')).toHaveTextContent('Avisamos que vas en camino');
  });

  it('keeps the operator affordances for an operator role and no field actions', () => {
    render(<AppointmentDetail data={detail} role="operador" />);

    expect(screen.getByRole('link', { name: /Ver ficha del cliente/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cerrar visita' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reprogramar' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Voy en camino' })).not.toBeInTheDocument();
  });

  /** S9: the office reads what the technician marked, and how long ago. */
  it('shows the technician field state with its age to the operator', () => {
    render(<AppointmentDetail
      data={{ ...detail, appointment: { ...detail.appointment, technician_state: 'en_route', technician_state_at: '2026-09-26T12:50:00Z' } }}
      role="operador"
      now={FIELD_NOW}
    />);

    expect(screen.getByText('Estado en terreno')).toBeInTheDocument();
    expect(screen.getByText('Voy en camino')).toBeInTheDocument();
    expect(screen.getByText('hace 5 min')).toBeInTheDocument();
  });

  /** S9: a visit the technician has not touched carries no semaphore. */
  it('hides the office semaphore for a visit the technician has not touched', () => {
    render(<AppointmentDetail data={detail} role="operador" now={FIELD_NOW} />);

    expect(screen.queryByText('Estado en terreno')).not.toBeInTheDocument();
  });

  /** S9: the technician's own badge gains the same age. */
  it('shows how long ago the technician marked the state', () => {
    render(<AppointmentDetail data={withState('en_route', technicianDetail.quick_actions, '2026-09-26T12:50:00Z')} role="tecnico" now={FIELD_NOW} />);

    expect(screen.getByText('Último aviso enviado')).toBeInTheDocument();
    expect(screen.getByText('hace 5 min')).toBeInTheDocument();
  });
});
