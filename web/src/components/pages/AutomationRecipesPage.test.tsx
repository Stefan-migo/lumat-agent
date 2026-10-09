import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AutomationRecipesPage } from './AutomationRecipesPage';

const recipe = { recipe_id: 'booking-confirmation', name: 'Confirmación de reserva', description: 'Confirma una reserva.', category: 'Reservas', trigger_kind: 'event', event_type: 'appointment.booked', channel_allowed: ['whatsapp', 'email'], recipient_target: 'customer', content: 'Tu reserva está confirmada.', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'string', required: true, default: 'whatsapp' }] };
const installation = { id: 8, recipe_id: recipe.recipe_id, parameters: { channel: 'email' }, enabled: false, created_by: 'ana', created_at: null, updated_at: null };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

describe('AutomationRecipesPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('renders catalog details, installs with selected channel, and refreshes installations', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith('/automation-recipes')) return json({ recipes: [recipe] });
      if (init?.method === 'POST') return json({ installation }, 201);
      return json({ installations: path.endsWith('/automation-installations') && fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/automation-installations')).length > 1 ? [installation] : [] });
    });
    render(<AutomationRecipesPage />);
    expect(await screen.findByText('Tu reserva está confirmada.')).toBeInTheDocument();
    expect(screen.getByText('Canales: whatsapp, email')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Instalar' }));
    expect(screen.getByLabelText('Canal')).toHaveValue('whatsapp');
    fireEvent.change(screen.getByLabelText('Canal'), { target: { value: 'email' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar instalación' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/panel/api/automation-installations', expect.objectContaining({ method: 'POST', body: '{"recipe_id":"booking-confirmation","parameters":{"channel":"email"}}' })));
    expect(await screen.findByRole('button', { name: 'Activar' })).toBeInTheDocument();
    expect(screen.getByText('Inactiva')).toBeInTheDocument();
  });

  it.each([[false, 'Activar'], [true, 'Desactivar']] as const)('toggles an installation currently %s and refreshes', async (enabled, action) => {
    let currentEnabled = enabled;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const path = String(input);
      if (path.endsWith('/automation-recipes')) return json({ recipes: [recipe] });
      if (path.endsWith('/automation-installations/8/enable') || path.endsWith('/automation-installations/8/disable')) { currentEnabled = !enabled; return json({ ok: true, installation: { ...installation, enabled: currentEnabled } }); }
      return json({ installations: [ { ...installation, enabled: currentEnabled } ] });
    });
    render(<AutomationRecipesPage />);
    fireEvent.click(await screen.findByRole('button', { name: action }));
    expect(await screen.findByRole('button', { name: enabled ? 'Desactivar' : 'Activar' })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(`/panel/api/automation-installations/8/${enabled ? 'disable' : 'enable'}`, expect.objectContaining({ method: 'POST' }));
  });

  it('shows loading, retryable errors, denied access, and an empty installation state honestly', async () => {
    let resolve!: (value: Response) => void;
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => String(input).endsWith('/automation-recipes')
      ? new Promise<Response>((done) => { resolve = done; })
      : Promise.resolve(json({ installations: [] })));
    render(<AutomationRecipesPage />);
    expect(screen.getByText('Cargando el catálogo')).toBeInTheDocument();
    resolve(json({ recipes: [recipe] }));
    expect(await screen.findByText('Aún no hay recetas instaladas')).toBeInTheDocument();

    vi.restoreAllMocks();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).endsWith('/automation-recipes') ? json({ detail: 'Forbidden' }, 403) : json({ installations: [] }));
    const denied = render(<AutomationRecipesPage />);
    expect((await screen.findAllByText('No tienes permiso para ver estas automatizaciones')).length).toBeGreaterThan(0);
    denied.unmount();

    vi.restoreAllMocks();
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network'));
    render(<AutomationRecipesPage />);
    expect(await screen.findByText('No pudimos cargar el catálogo')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: 'Reintentar' })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it('disables the install control while its request is pending', async () => {
    let finish!: (value: Response) => void;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith('/automation-recipes')) return json({ recipes: [recipe] });
      if (init?.method === 'POST') return new Promise<Response>((resolve) => { finish = resolve; });
      return json({ installations: [] });
    });
    render(<AutomationRecipesPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Instalar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar instalación' }));
    expect(screen.getByRole('button', { name: 'Instalando…' })).toBeDisabled();
    finish(json({ installation }, 201));
    await screen.findByRole('button', { name: 'Instalar' });
  });
});
