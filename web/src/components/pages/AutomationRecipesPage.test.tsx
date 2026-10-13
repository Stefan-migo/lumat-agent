import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ApiError } from '../../api';
import { AutomationRecipesPage } from './AutomationRecipesPage';

const recipes = [
  { recipe_id: 'appointment_confirmation', name: 'Confirmación de reserva', description: 'Envía un mensaje automático al confirmar una reserva.', category: 'reservas', trigger_kind: 'event', event_type: 'appointment.booked', channel_allowed: ['whatsapp'], recipient_target: 'customer', content: 'Tu visita quedó registrada.', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'channel', required: true, default: 'whatsapp' }] },
  { recipe_id: 'appointment_review_request', name: 'Pedir evaluación', description: 'Solicita una evaluación después de la visita.', category: 'postventa', trigger_kind: 'offset', event_type: 'appointment.review_due', channel_allowed: ['whatsapp'], recipient_target: 'customer', content: '¿Cómo estuvo tu visita?', cooldown_seconds: 0, parameters: [{ key: 'channel', label: 'Canal', type: 'channel', required: true, default: 'whatsapp' }, { key: 'days_after', label: 'Días después de la visita', type: 'number', required: true, default: 3 }] },
];
const installation = { id: 8, recipe_id: recipes[0].recipe_id, parameters: { channel: 'whatsapp' }, enabled: false, created_by: 'ana', created_at: null, updated_at: null };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const page = (loadInstallations = async () => ({ installations: [] as typeof installation[] })) => render(<AutomationRecipesPage loadRecipes={async () => ({ recipes })} loadInstallations={loadInstallations} />);

describe('AutomationRecipesPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('renders truthful catalog counts, descriptions, channels, and filters by search and category', async () => {
    page();
    expect(await screen.findByText(recipes[0].description)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Catálogo (2)' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Instaladas (0)' })).toBeInTheDocument();
    expect(screen.getAllByText('WhatsApp')).toHaveLength(2);
    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar automatización' }), { target: { value: 'evaluación' } });
    await waitFor(() => expect(screen.queryByText('Confirmación de reserva')).not.toBeInTheDocument());
    expect(screen.queryByText('Confirmación de reserva')).not.toBeInTheDocument();
    expect(screen.getByText('Pedir evaluación')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Categoría'), { target: { value: 'reservas' } });
    expect(screen.queryByText('Pedir evaluación')).not.toBeInTheDocument();
    expect(screen.getByText('No encontramos automatizaciones')).toBeInTheDocument();
  });

  it('creates a catalog installation from the configuration dialog', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (String(input).endsWith('/automation-installations') && init?.method === 'POST') return json({ installation }, 201);
      return json(String(input).endsWith('/automation-recipes') ? { recipes } : { installations: [] });
    });
    page();
    fireEvent.click((await screen.findAllByRole('button', { name: '+ Configurar' }))[0]);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Configurar' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/panel/api/automation-installations', expect.objectContaining({ method: 'POST', body: JSON.stringify({ recipe_id: recipes[0].recipe_id, parameters: { channel: 'whatsapp' } }) })));
  });

  it('edits parameters and toggles an installed recipe', async () => {
    let enabled = false;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith('/automation-recipes')) return json({ recipes });
      if (path.endsWith('/automation-installations/8/enable')) { enabled = true; return json({ ok: true, installation: { ...installation, enabled } }); }
      if (init?.method === 'PATCH') return json({ installation: { ...installation, parameters: { channel: 'whatsapp', days_after: 5 } } });
      return json({ installations: [{ ...installation, enabled }] });
    });
    page(async () => ({ installations: [installation] }));
    fireEvent.click(screen.getByRole('button', { name: /Ver instaladas/ }));
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Instaladas (1)' })).toHaveAttribute('aria-selected', 'true'));
    fireEvent.click(screen.getByRole('button', { name: 'Editar' }));
    fireEvent.change(screen.getByLabelText('Canal'), { target: { value: 'whatsapp' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/panel/api/automation-installations/8', expect.objectContaining({ method: 'PATCH' })));
    fireEvent.click(await screen.findByRole('button', { name: 'Activar' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/panel/api/automation-installations/8/enable', expect.objectContaining({ method: 'POST' })));
  });

  it('shows loading, denied, retryable error, and honest empty installed states', async () => {
    let resolveRecipes!: (value: { recipes: typeof recipes }) => void;
    const loading = render(<AutomationRecipesPage loadRecipes={() => new Promise((resolve) => { resolveRecipes = resolve; })} loadInstallations={async () => ({ installations: [] })} />);
    expect(screen.getByRole('status', { name: 'Cargando el catálogo' })).toBeInTheDocument();
    resolveRecipes({ recipes });
    fireEvent.click(screen.getByRole('button', { name: /Ver instaladas/ }));
    expect(await screen.findByText('Aún no hay automatizaciones instaladas')).toBeInTheDocument();
    loading.unmount();

    const denied = render(<AutomationRecipesPage loadRecipes={async () => { throw new ApiError(403, 'Forbidden'); }} loadInstallations={async () => ({ installations: [] })} />);
    expect(await screen.findByText('No tienes permiso para ver estas automatizaciones')).toBeInTheDocument();
    denied.unmount();

    let attempts = 0;
    render(<AutomationRecipesPage loadRecipes={async () => { attempts += 1; throw new Error('network'); }} loadInstallations={async () => ({ installations: [] })} />);
    expect(await screen.findByText('No pudimos cargar el catálogo')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    await waitFor(() => expect(attempts).toBe(2));
  });
});
