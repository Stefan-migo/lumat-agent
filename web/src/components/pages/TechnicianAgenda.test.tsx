import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { TechnicianAgenda } from './TechnicianAgenda';
import { TechnicianShell } from '../domain/TechnicianShell';
import type { TechnicianAppointment, User } from '../../types';

const appointment: TechnicianAppointment = {
  id: 7, service: 'Calefont', local_start: '2026-01-02T10:00:00', starts_at: '2026-01-02T13:00:00+00:00', ends_at: '2026-01-02T14:00:00+00:00', timezone: 'America/Santiago',
  customer: { name: 'María Silva', address: 'Los Alerces 42', comuna: 'Ñuñoa', phone: '+56912345678' }, case_summary: 'Revisar fuga del calefont',
};

const tecnico: User = { id: 4, username: 'tec-agenda', role: 'tecnico' };

/** Mirrors app.tsx: a tecnico session composes the shell around the agenda. */
function renderSurface() {
  return render(
    <TechnicianShell user={tecnico} onLogout={() => {}}>
      <TechnicianAgenda />
    </TechnicianShell>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('TechnicianAgenda', () => {
  it('renders the owned agenda allow-list and local time', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }),
    );

    render(<TechnicianAgenda />);

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.getByText('María Silva')).toBeInTheDocument();
    expect(screen.getByText('Los Alerces 42')).toBeInTheDocument();
    expect(screen.getByText('Ñuñoa')).toBeInTheDocument();
    expect(screen.getByText('+56912345678')).toBeInTheDocument();
    expect(screen.getByText('Revisar fuga del calefont')).toBeInTheDocument();
    expect(screen.queryByText('private@example.test')).not.toBeInTheDocument();
    expect(screen.queryByText(/consent|history|sync|notes|status/i)).not.toBeInTheDocument();
  });

});

describe('technician surface composition', () => {
  it('exposes exactly one page heading', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }),
    );

    renderSurface();

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Agenda técnica');
  });

  it('keeps the shell brand and session controls alongside the page title', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }),
    );

    renderSurface();

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.getByAltText('Lumat')).toBeInTheDocument();
    expect(screen.getByText('tec-agenda')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument();
  });
});

describe('technician surface — reaching the customer', () => {
  const renderWith = (rows: TechnicianAppointment[]) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: rows }), { status: 200 }),
    );
    return render(<TechnicianAgenda />);
  };

  it('never renders an empty tel: link when the customer has no phone', async () => {
    renderWith([{ ...appointment, id: 8, customer: { ...appointment.customer, phone: null } }]);

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.getByText('Teléfono no registrado')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('makes the phone reachable through the shared Button primitive when it exists', async () => {
    renderWith([appointment]);

    const call = await screen.findByRole('link', { name: '+56912345678' });
    expect(call).toHaveAttribute('href', 'tel:+56912345678');
    expect(call).toHaveClass('btn');
  });
});

describe('technician surface — reading the agenda as a schedule', () => {
  const at = (offsetDays: number, hour: number) => {
    const date = new Date();
    date.setUTCDate(date.getUTCDate() + offsetDays);
    date.setUTCHours(hour, 0, 0, 0);
    return date;
  };
  /** Fixtures sit in UTC so "today" cannot depend on the host timezone. */
  const visit = (id: number, offsetDays: number, hour: number, service: string): TechnicianAppointment => ({
    id, service, local_start: at(offsetDays, hour).toISOString().slice(0, 19),
    starts_at: at(offsetDays, hour).toISOString(), ends_at: at(offsetDays, hour + 1).toISOString(),
    timezone: 'UTC', customer: { name: `Cliente ${id}`, address: `Calle ${id}`, comuna: 'Ñuñoa', phone: '+56900000000' },
    case_summary: null,
  });
  const mock = (rows: TechnicianAppointment[]) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: rows }), { status: 200 }),
    );
  };

  it('leads each card with the appointment slot, not the service name', async () => {
    mock([visit(1, 0, 14, 'Calefont')]);

    render(<TechnicianAgenda />);

    const service = await screen.findByText('Calefont');
    const card = service.closest('article');
    expect(card?.firstElementChild).toHaveClass('technician-agenda__slot');
  });

  it('marks today and keeps past visits out of the upcoming section', async () => {
    mock([visit(1, -2, 14, 'Instalación vieja'), visit(2, 0, 14, 'Calefont hoy'), visit(3, 3, 14, 'Cambio de termo')]);

    render(<TechnicianAgenda />);

    await screen.findByText('Calefont hoy');
    const upcoming = screen.getByRole('region', { name: 'Próximas visitas' });
    const past = screen.getByRole('region', { name: 'Visitas anteriores' });
    expect(within(upcoming).getByRole('heading', { name: 'Hoy' })).toBeInTheDocument();
    expect(within(upcoming).getByText('Cambio de termo')).toBeInTheDocument();
    expect(within(upcoming).queryByText('Instalación vieja')).not.toBeInTheDocument();
    expect(within(past).getByText('Instalación vieja')).toBeInTheDocument();
    expect(upcoming.compareDocumentPosition(past) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('renders no past section when every visit is still ahead', async () => {
    mock([visit(1, 0, 14, 'Calefont hoy'), visit(2, 3, 14, 'Cambio de termo')]);

    render(<TechnicianAgenda />);

    await screen.findByText('Calefont hoy');
    expect(screen.getByRole('region', { name: 'Próximas visitas' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Visitas anteriores' })).not.toBeInTheDocument();
  });
});

describe('technician surface — controls come from the panel primitives', () => {
  it('renders the recovery and session controls through the shared Button', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }),
    );

    renderSurface();

    expect(await screen.findByRole('button', { name: 'Reintentar' })).toHaveClass('btn');
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toHaveClass('btn');
  });
});
