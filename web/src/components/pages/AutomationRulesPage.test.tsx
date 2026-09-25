import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AutomationRulesPage } from './AutomationRulesPage';
import { listAutomationRules } from '../../api';
import type { Rule } from '../../types';
import type { User } from '../../types';

vi.mock('../../api', () => ({ listAutomationRules: vi.fn() }));

const rule = (overrides: Partial<Rule> = {}): Rule => ({
  id: 7, name: 'Avisar caso nuevo', event_type: 'case.created', conditions: { priority: 'alta' }, channel: 'whatsapp',
  template_event: 'case.created', cooldown_seconds: 300, enabled: true, created_by: 'ana', created_at: '2026-09-05T12:00:00Z', updated_at: '2026-09-05T12:00:00Z', ...overrides,
});
const admin: User = { username: 'ana', role: 'admin' };
const operator: User = { username: 'vero', role: 'operador' };

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('AutomationRulesPage', () => {
  it('renders an accessible table with rule fields and notification event/content labels', () => {
    render(<AutomationRulesPage data={[rule()]} state="ready" />);
    expect(screen.getByRole('heading', { name: 'Reglas de automatización', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Avisar caso nuevo' })).toHaveAttribute('href', '/panel/app/automation-rules/7');
    expect(screen.getAllByText('case.created')).toHaveLength(2);
    expect(screen.getByText('Contenido de notificación')).toBeInTheDocument();
    expect(screen.queryByText(/selector|versión de template/i)).not.toBeInTheDocument();
    expect(screen.getByText('Habilitada')).toBeInTheDocument();
    expect(screen.getByText('{"priority":"alta"}')).toBeInTheDocument();
    expect(screen.getByText('ana')).toBeInTheDocument();
  });

  it('renders loading, empty, forbidden, and recoverable error states', async () => {
    const retry = vi.fn();
    const { rerender } = render(<AutomationRulesPage data={null} state="loading" onRetry={retry} />);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando reglas');
    expect(document.querySelector('.page-header p')).toHaveTextContent('Reglas de automatización');
    rerender(<AutomationRulesPage data={[]} state="empty" onRetry={retry} />);
    expect(screen.getByText('No hay reglas de automatización')).toBeInTheDocument();
    rerender(<AutomationRulesPage data={null} state="denied" onRetry={retry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso');
    rerender(<AutomationRulesPage data={null} state="error" onRetry={retry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar las reglas');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it('loads rules through the API and retries after a failure', async () => {
    vi.mocked(listAutomationRules).mockResolvedValue({ rules: [rule({ id: 8, name: 'Segunda regla' })] });
    render(<AutomationRulesPage />);
    expect(await screen.findByRole('link', { name: 'Segunda regla' })).toBeInTheDocument();
    expect(listAutomationRules).toHaveBeenCalledOnce();
  });

  it('offers rule creation to admins but not operators', async () => {
    const user = userEvent.setup();
    const onOpenCreate = vi.fn();
    const { rerender } = render(<AutomationRulesPage user={admin} data={[]} state="empty" onOpenCreate={onOpenCreate} />);
    expect(screen.getByRole('button', { name: 'Crear regla' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Crear regla' }));
    expect(onOpenCreate).toHaveBeenCalledOnce();

    rerender(<AutomationRulesPage user={operator} data={[]} state="empty" onOpenCreate={onOpenCreate} />);
    expect(screen.queryByRole('button', { name: 'Crear regla' })).not.toBeInTheDocument();
  });
});
