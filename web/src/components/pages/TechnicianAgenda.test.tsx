import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
