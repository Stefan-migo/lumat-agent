import { describe, expect, it } from 'vitest';
import { canOpen, defaultViewForRole, footerViewsForRole } from './panelAccess';
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

/** Only the technician is restricted here. The administrative destinations are
 *  declared once, with the navigation (`isAdminOnlyView`), not duplicated. */
describe('panelAccess — admin and operator', () => {
  it('leaves admin and operador unrestricted at this level', () => {
    for (const view of ['dashboard', 'kb', 'settings', 'users', 'agenda', 'chat'] as PanelView[]) {
      expect(canOpen('admin', view), view).toBe(true);
      expect(canOpen('operador', view), view).toBe(true);
    }
  });

  it('keeps the operator landing view and mobile tabs unchanged', () => {
    expect(defaultViewForRole('operador')).toBe('dashboard');
    expect(footerViewsForRole('operador')).toEqual(['dashboard', 'conversations', 'chat', 'agenda', 'clients']);
  });

  /** A destination another branch adds to `PanelView` defaults to the safe side
   *  without editing this file: admin and operador allow it, the technician does not. */
  it('defaults an unseen destination to allowed for admin/operador and denied for the technician', () => {
    const unseen = 'a-view-from-another-branch' as unknown as PanelView;
    expect(canOpen('admin', unseen)).toBe(true);
    expect(canOpen('operador', unseen)).toBe(true);
    expect(canOpen('tecnico', unseen)).toBe(false);
  });
});
