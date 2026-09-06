import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  createAutomationRule,
  disableAutomationRule,
  enableAutomationRule,
  getAutomationRule,
  updateAutomationRule,
} from '../../api';
import type { Rule, User } from '../../types';
import { AutomationRuleDetailPage } from './AutomationRuleDetailPage';

vi.mock('../../api', () => ({
  createAutomationRule: vi.fn(),
  disableAutomationRule: vi.fn(),
  enableAutomationRule: vi.fn(),
  getAutomationRule: vi.fn(),
  updateAutomationRule: vi.fn(),
}));

const admin: User = { username: 'ana', role: 'admin' };
const operator: User = { username: 'vero', role: 'operador' };
const rule = (overrides: Partial<Rule> = {}): Rule => ({
  id: 7,
  name: 'Avisar caso nuevo',
  event_type: 'case.created',
  conditions: { priority: 'alta' },
  channel: 'whatsapp',
  template_event: 'case.created',
  cooldown_seconds: 300,
  enabled: true,
  created_by: 'ana',
  created_at: '2026-09-05T12:00:00Z',
  updated_at: '2026-09-05T12:00:00Z',
  ...overrides,
});

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('AutomationRuleDetailPage', () => {
  it('refreshes the persisted rule through GET after admin creation', async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    vi.mocked(createAutomationRule).mockResolvedValue({ rule: rule({ id: 8, name: 'Regla creada' }) });
    vi.mocked(getAutomationRule).mockResolvedValue({ rule: rule({ id: 8, name: 'Regla persistida' }) });
    render(<AutomationRuleDetailPage ruleId={null} user={admin} onCreated={onCreated} />);

    await user.type(screen.getByLabelText('Nombre'), 'Regla creada');
    await user.type(screen.getByLabelText('Evento'), 'case.created');
    await user.type(screen.getByLabelText('Canal'), 'whatsapp');
    await user.type(screen.getByLabelText('Contenido de notificación'), 'case.created');
    await user.click(screen.getByRole('button', { name: 'Crear regla' }));

    expect(createAutomationRule).toHaveBeenCalledOnce();
    expect(getAutomationRule).toHaveBeenCalledWith(8);
    expect(onCreated).toHaveBeenCalledWith(8);
    expect(await screen.findByDisplayValue('Regla persistida')).toBeInTheDocument();
  });

  it('lets admins edit bounded fields and shows validation before submitting', async () => {
    const user = userEvent.setup();
    render(<AutomationRuleDetailPage ruleId={7} user={admin} data={rule()} state="ready" />);

    await user.click(screen.getByRole('button', { name: 'Editar regla' }));
    await user.clear(screen.getByLabelText('Nombre'));
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));

    expect(screen.getByText('El nombre es obligatorio')).toBeInTheDocument();
    expect(updateAutomationRule).not.toHaveBeenCalled();
  });

  it('submits edits and refreshes the detail from the API', async () => {
    const user = userEvent.setup();
    vi.mocked(updateAutomationRule).mockResolvedValue({ rule: rule({ name: 'Avisar prioridad alta' }) });
    vi.mocked(getAutomationRule).mockResolvedValue({ rule: rule({ name: 'Avisar prioridad alta' }) });
    render(<AutomationRuleDetailPage ruleId={7} user={admin} data={rule()} state="ready" />);

    await user.click(screen.getByRole('button', { name: 'Editar regla' }));
    await user.clear(screen.getByLabelText('Nombre'));
    await user.type(screen.getByLabelText('Nombre'), 'Avisar prioridad alta');
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));

    expect(updateAutomationRule).toHaveBeenCalledWith(7, expect.objectContaining({ name: 'Avisar prioridad alta' }));
    expect(await screen.findByDisplayValue('Avisar prioridad alta')).toBeInTheDocument();
    expect(getAutomationRule).toHaveBeenCalledWith(7);
  });

  it('keeps operator controls read-only', () => {
    render(<AutomationRuleDetailPage ruleId={7} user={operator} data={rule()} state="ready" />);

    expect(screen.queryByRole('button', { name: /editar|habilitar|deshabilitar|guardar/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Nombre')).toHaveAttribute('readonly');
    expect(screen.getByLabelText('Nombre')).toHaveValue('Avisar caso nuevo');
  });

  it('requires confirmation and refreshes after disabling a rule', async () => {
    const user = userEvent.setup();
    vi.mocked(disableAutomationRule).mockResolvedValue({ ok: true, rule: rule({ enabled: false }) });
    vi.mocked(getAutomationRule).mockResolvedValue({ rule: rule({ enabled: false }) });
    render(<AutomationRuleDetailPage ruleId={7} user={admin} data={rule()} state="ready" />);

    await user.click(screen.getByRole('button', { name: 'Deshabilitar regla' }));
    expect(screen.getByRole('dialog', { name: 'Deshabilitar regla' })).toBeInTheDocument();
    expect(disableAutomationRule).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Confirmar deshabilitación' }));

    expect(disableAutomationRule).toHaveBeenCalledWith(7);
    expect(getAutomationRule).toHaveBeenCalledWith(7);
    expect(await screen.findByText('Deshabilitada')).toBeInTheDocument();
  });

  it('renders API mutation errors', async () => {
    const user = userEvent.setup();
    vi.mocked(enableAutomationRule).mockRejectedValue(new Error('No tienes permiso'));
    render(<AutomationRuleDetailPage ruleId={7} user={admin} data={rule({ enabled: false })} state="ready" />);

    await user.click(screen.getByRole('button', { name: 'Habilitar regla' }));
    await user.click(screen.getByRole('button', { name: 'Confirmar habilitación' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('No tienes permiso');
  });
});
