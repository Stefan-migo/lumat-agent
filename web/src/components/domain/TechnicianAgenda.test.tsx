import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TechnicianAgenda } from '../pages/TechnicianAgenda';
import { TechnicianShell } from './TechnicianShell';
import type { TechnicianAppointment, User } from '../../types';

const user: User = { username: 'tech', role: 'tecnico' };
const appointment: TechnicianAppointment = {
  id: 7,
  service: 'Calefont',
  local_start: '2026-01-02T10:00:00',
  starts_at: '2026-01-02T13:00:00+00:00',
  ends_at: '2026-01-02T14:00:00+00:00',
  timezone: 'America/Santiago',
  customer: { name: 'María Silva', address: 'Los Alerces 42', comuna: 'Ñuñoa', phone: '+56912345678' },
  case_summary: 'Revisar fuga del calefont',
};

afterEach(() => vi.restoreAllMocks());

describe('TechnicianShell', () => {
  it('renders a minimal shell with logout and no operational navigation', async () => {
    const onLogout = vi.fn();
    render(<TechnicianShell user={user} onLogout={onLogout}><p>Contenido</p></TechnicianShell>);

    expect(screen.getByText('Agenda técnica')).toBeInTheDocument();
    expect(screen.queryByText('Clientes')).not.toBeInTheDocument();
    expect(screen.queryByText('Casos')).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(onLogout).toHaveBeenCalledOnce();
  });
});

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

  it('renders an empty state without fabricating appointments', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ appointments: [] }), { status: 200 }),
    );

    render(<TechnicianAgenda />);

    expect(await screen.findByText('No hay visitas asignadas')).toBeInTheDocument();
    expect(screen.queryByText('Calefont')).not.toBeInTheDocument();
  });
});
