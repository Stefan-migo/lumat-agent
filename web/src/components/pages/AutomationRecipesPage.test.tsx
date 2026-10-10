import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AutomationRecipesPage } from './AutomationRecipesPage';

const recipe = { recipe_id: 'booking-confirmation', name: 'Confirmación de reserva', description: 'Confirma una reserva.', category: 'Reservas', trigger_kind: 'event', event_type: 'appointment.booked', channel_allowed: ['whatsapp', 'email'], recipient_target: 'customer', content: 'Tu reserva está confirmada.', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'string', required: true, default: 'whatsapp' }] };
const offsetRecipe = { recipe_id: 'appointment_review_request', name: 'Pedir evaluación', description: 'Solicita una evaluación después de la visita.', category: 'postventa', trigger_kind: 'offset', event_type: 'appointment.review_due', channel_allowed: ['whatsapp'], recipient_target: 'customer', content: '¿Cómo estuvo tu visita? Nos encantaría conocer tu opinión.', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'channel', required: true, default: null }, { key: 'days_after', label: 'Días después de la visita', type: 'number', required: true, default: 3 }] };
const weeklyRecipe = { recipe_id: 'admin_weekly_summary', name: 'Resumen semanal', description: 'Envía un resumen semanal.', category: 'administración', trigger_kind: 'schedule', channel_allowed: ['whatsapp'], recipient_target: 'admin', content: 'Resumen semanal.', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'channel', required: true, default: 'whatsapp' }, { key: 'weekday', label: 'Día de la semana', type: 'weekday', required: true, default: 1 }, { key: 'time', label: 'Hora', type: 'time', required: true, default: '07:00' }] };
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

  it('installs an offset recipe with its numeric parameter', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith('/automation-recipes')) return json({ recipes: [offsetRecipe] });
      if (init?.method === 'POST') return json({ installation: { ...installation, recipe_id: offsetRecipe.recipe_id, parameters: { channel: 'whatsapp', days_after: 5 } } }, 201);
      return json({ installations: [] });
    });
    render(<AutomationRecipesPage />);
    expect(await screen.findByText(offsetRecipe.content)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Instalar' }));
    expect(screen.getByLabelText('Días después de la visita')).toHaveValue(3);
    fireEvent.change(screen.getByLabelText('Días después de la visita'), { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar instalación' }));
    await waitFor(() => {
      const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/automation-installations') && init?.method === 'POST');
      expect(postCall).toBeDefined();
      const body = JSON.parse(String(postCall?.[1]?.body));
      expect(body.parameters.days_after).toBe(5);
      expect(typeof body.parameters.days_after).toBe('number');
    });
  });

  it('installs a weekly summary with numeric weekday and time parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith('/automation-recipes')) return json({ recipes: [weeklyRecipe] });
      if (init?.method === 'POST') return json({ installation: { ...installation, recipe_id: weeklyRecipe.recipe_id, parameters: { channel: 'whatsapp', weekday: 3, time: '09:30' } } }, 201);
      return json({ installations: [] });
    });
    render(<AutomationRecipesPage />);
    expect(await screen.findByText(weeklyRecipe.content)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Instalar' }));
    expect(screen.getByLabelText('Día de la semana')).toHaveValue('1');
    expect(screen.getByLabelText('Hora')).toHaveValue('07:00');
    fireEvent.change(screen.getByLabelText('Día de la semana'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText('Hora'), { target: { value: '09:30' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar instalación' }));
    await waitFor(() => {
      const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/automation-installations') && init?.method === 'POST');
      expect(postCall).toBeDefined();
      const body = JSON.parse(String(postCall?.[1]?.body));
      expect(body.parameters.weekday).toBe(3);
      expect(typeof body.parameters.weekday).toBe('number');
      expect(body.parameters.time).toBe('09:30');
    });
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
