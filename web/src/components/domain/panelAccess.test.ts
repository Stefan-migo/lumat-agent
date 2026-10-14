import { describe, expect, it } from 'vitest';
import { canOpen, defaultViewForRole, footerViewsForRole, viewsForRole } from './panelAccess';
import type { PanelView } from './PanelShell';

/** D1: the technician's unit of work is the visit, not the CRM. */
describe('panelAccess — technician surface', () => {
  it('allows the technician only their field destinations', () => {
    for (const view of ['agenda', 'chat', 'notifications', 'profile'] as PanelView[]) {
      expect(canOpen('tecnico', view), view).toBe(true);
    }
  });

  it('denies the technician every operator and admin destination', () => {
    for (const view of ['dashboard', 'clients', 'conversations', 'kb', 'settings', 'users', 'automation-rules', 'cases', 'advanced-dashboard'] as PanelView[]) {
      expect(canOpen('tecnico', view), view).toBe(false);
    }
  });

  it('lands the technician on the agenda, never the operator dashboard', () => {
    expect(defaultViewForRole('tecnico')).toBe('agenda');
  });

  it('limits the technician mobile tabs to their own surface', () => {
    expect(footerViewsForRole('tecnico')).toEqual(['agenda', 'chat', 'notifications', 'profile']);
  });
});

describe('panelAccess — operator and admin keep their surface', () => {
  it('keeps the operator surface to everything except the admin-only destinations', () => {
    for (const view of ['dashboard', 'clients', 'conversations', 'agenda', 'chat', 'advanced-dashboard'] as PanelView[]) {
      expect(canOpen('operador', view), view).toBe(true);
    }
    for (const view of ['kb', 'settings', 'users', 'automation-rules'] as PanelView[]) {
      expect(canOpen('operador', view), view).toBe(false);
    }
  });

  it('gives admin every destination', () => {
    for (const view of ['dashboard', 'kb', 'settings', 'users', 'automation-rules', 'agenda', 'chat'] as PanelView[]) {
      expect(canOpen('admin', view), view).toBe(true);
    }
  });

  it('keeps the operator landing view and mobile tabs unchanged', () => {
    expect(defaultViewForRole('operador')).toBe('dashboard');
    expect(footerViewsForRole('operador')).toEqual(['dashboard', 'conversations', 'chat', 'agenda', 'clients']);
  });

  it('never grants a technician a view the operator also lacks by accident', () => {
    const technician = viewsForRole('tecnico');
    for (const view of technician) {
      expect(canOpen('tecnico', view), view).toBe(true);
    }
  });
});
