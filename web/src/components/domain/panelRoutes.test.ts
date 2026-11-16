import { describe, expect, it } from 'vitest';
import { notificationDestination } from './panelRoutes';

describe('notificationDestination', () => {
  it('maps only the entities the panel can actually open', () => {
    expect(notificationDestination('appointment', '7')).toEqual({ view: 'agenda', appointmentId: 7 });
    expect(notificationDestination('conversation', '19')).toEqual({ view: 'conversations', conversationId: 19 });
    for (const entity of ['panel', 'case', 'notification_failure', 'cost_alert', null, undefined]) {
      expect(notificationDestination(entity, '7')).toBeNull();
    }
  });

  it('refuses an id that is not a positive integer instead of building a broken route', () => {
    expect(notificationDestination('appointment', 'panel:7')).toBeNull();
    expect(notificationDestination('appointment', '0')).toBeNull();
    expect(notificationDestination('appointment', '-4')).toBeNull();
    expect(notificationDestination('appointment', '1e9')).toBeNull();
    expect(notificationDestination('appointment', '99999999999999999999')).toBeNull();
    expect(notificationDestination('appointment', null)).toBeNull();
  });
});
