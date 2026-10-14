import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TechnicianAgenda } from './TechnicianAgenda';
import type { TechnicianAppointment } from '../../types';

const appointment: TechnicianAppointment = {
  id: 7, service: 'Calefont', local_start: '2026-01-02T10:00:00', starts_at: '2026-01-02T13:00:00+00:00', ends_at: '2026-01-02T14:00:00+00:00', timezone: 'America/Santiago', status: 'booked', emergency: false, priority: null,
  customer: { name: 'María Silva', address: 'Los Alerces 42', comuna: 'Ñuñoa' }, case_summary: 'Revisar fuga del calefont',
};

afterEach(() => vi.restoreAllMocks());

describe('TechnicianAgenda', () => {
  it('renders the owned agenda allow-list and local time', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }),
    );

    render(<TechnicianAgenda />);

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.getByText('María Silva')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Los Alerces 42' })).toBeInTheDocument();
    expect(screen.getByText('Ñuñoa')).toBeInTheDocument();
    expect(screen.queryByText('+56912345678')).not.toBeInTheDocument();
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

    render(<TechnicianAgenda />);

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Agenda técnica');
  });
});

describe('technician surface — reaching the customer', () => {
  const renderWith = (rows: TechnicianAppointment[]) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: rows }), { status: 200 }),
    );
    return render(<TechnicianAgenda />);
  };

  /** The customer phone is never handed to the technician (S3): no field, no
   *  tel: link. Contact happens through the field quick actions instead. */
  it('never renders the customer phone nor a tel: link', async () => {
    renderWith([appointment]);

    expect(await screen.findByText('Calefont')).toBeInTheDocument();
    expect(screen.queryByText('+56912345678')).not.toBeInTheDocument();
    expect(screen.queryByText('Teléfono no registrado')).not.toBeInTheDocument();
    expect(screen.getAllByRole('link').some((link) => link.getAttribute('href')?.startsWith('tel:'))).toBe(false);
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
    timezone: 'UTC', status: 'booked', emergency: false, priority: null, customer: { name: `Cliente ${id}`, address: `Calle ${id}`, comuna: 'Ñuñoa' },
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

describe('technician surface — appointment state', () => {
  const mock = (rows: TechnicianAppointment[]) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: rows }), { status: 200 }),
    );
  };

  it('states every appointment status in words, so colour is never the only channel', async () => {
    mock([
      { ...appointment, id: 1, service: 'Reparación', status: 'booked' },
      { ...appointment, id: 2, service: 'Revisión', status: 'cancelled' },
      { ...appointment, id: 3, service: 'Instalación', status: 'completed' },
      { ...appointment, id: 4, service: 'Mantención', status: 'no_show' },
    ]);

    render(<TechnicianAgenda />);

    await screen.findByText('Reparación');
    expect(screen.getByText('Reservada')).toBeInTheDocument();
    expect(screen.getByText('Cancelada')).toBeInTheDocument();
    expect(screen.getByText('Completada')).toBeInTheDocument();
    expect(screen.getByText('No asistió')).toBeInTheDocument();
  });

  it('marks a cancelled visit so it cannot be read as a booked one', async () => {
    mock([
      { ...appointment, id: 1, service: 'Reparación', status: 'booked' },
      { ...appointment, id: 2, service: 'Revisión', status: 'cancelled' },
    ]);

    render(<TechnicianAgenda />);

    const cancelled = (await screen.findByText('Revisión')).closest('article');
    const booked = screen.getByText('Reparación').closest('article');
    expect(within(cancelled as HTMLElement).getByText('Cancelada')).toBeInTheDocument();
    expect(within(booked as HTMLElement).getByText('Reservada')).toBeInTheDocument();
  });

  it('counts the visits that happen and names the cancelled ones apart', async () => {
    mock([
      { ...appointment, id: 1, service: 'Reparación', status: 'booked' },
      { ...appointment, id: 2, service: 'Revisión', status: 'cancelled' },
      { ...appointment, id: 3, service: 'Instalación', status: 'cancelled' },
    ]);

    render(<TechnicianAgenda />);

    await screen.findByText('Reparación');
    expect(screen.getByText(/1 visita · 2 canceladas ·/)).toBeInTheDocument();
  });

  it('drops the cancelled suffix when no visit was cancelled', async () => {
    mock([{ ...appointment, id: 1, service: 'Reparación', status: 'booked' }]);

    render(<TechnicianAgenda />);

    await screen.findByText('Reparación');
    expect(screen.getByText(/1 visita · Actualizado/)).toBeInTheDocument();
    expect(screen.queryByText(/cancelada/)).not.toBeInTheDocument();
  });
});

describe('technician surface — visit safety and location', () => {
  it('names emergency and high priority visits instead of relying on colour', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [
        { ...appointment, id: 1, emergency: true, priority: null },
        { ...appointment, id: 2, emergency: false, priority: 'alta' },
      ] }), { status: 200 }),
    );

    render(<TechnicianAgenda />);

    await screen.findByText('Emergencia');
    expect(screen.getByText('Emergencia')).toBeInTheDocument();
    expect(screen.getByText('Prioridad alta')).toBeInTheDocument();
  });

  it('links the address and comuna to a Google Maps address search', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }),
    );

    render(<TechnicianAgenda />);

    const address = await screen.findByRole('link', { name: 'Los Alerces 42' });
    expect(address).toHaveAttribute(
      'href',
      `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent('Los Alerces 42, Ñuñoa')}`,
    );
    expect(address).toHaveClass('btn', 'btn--secondary', 'technician-agenda__field-control');
  });

  it('does not link a comuna when the street address is missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [{ ...appointment, customer: { ...appointment.customer, address: null, comuna: 'Ñuñoa' } }] }), { status: 200 }),
    );
    render(<TechnicianAgenda />);

    const missingAddress = await screen.findByText('Dirección no registrada');
    const card = missingAddress.closest('article');
    expect(missingAddress).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole('link')).not.toBeInTheDocument();
  });
});

describe('technician surface — controls come from the panel primitives', () => {
  it('renders the recovery and session controls through the shared Button', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }),
    );

    render(<TechnicianAgenda />);

    expect(await screen.findByRole('button', { name: 'Reintentar' })).toHaveClass('btn');
    expect(screen.getByRole('alert').parentElement).toHaveClass('agenda-recovery');
  });
});

describe('technician surface — freshness', () => {
  const mock = () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }),
    );
    return fetchMock;
  };

  it('re-fetches on demand instead of polling', async () => {
    const fetchMock = mock();
    const user = userEvent.setup();

    render(<TechnicianAgenda />);

    await screen.findByText('Calefont');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it('tells the technician when the agenda was last loaded', async () => {
    mock();

    render(<TechnicianAgenda />);

    await screen.findByText('Calefont');
    expect(screen.getByText(/Actualizado/)).toBeInTheDocument();
    expect(screen.getByText(/1 visita ·/)).toBeInTheDocument();
  });

  it('keeps the loaded agenda on screen while it refreshes', async () => {
    let settle: ((value: Response) => void) | undefined;
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ appointments: [appointment] }), { status: 200 }))
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { settle = resolve; }));
    const user = userEvent.setup();

    render(<TechnicianAgenda />);

    await screen.findByText('Calefont');
    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    // While the refresh is in flight the roster stays readable instead of blanking.
    expect(screen.getByText('Calefont')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Cargando agenda');

    settle?.(new Response(JSON.stringify({ appointments: [] }), { status: 200 }));
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
  });
});
