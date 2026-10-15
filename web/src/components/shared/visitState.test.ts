import { describe, expect, it } from 'vitest';
import { fieldStateAge, QUICK_ACTION_LABELS } from './visitState';

const NOW = new Date('2026-09-26T12:55:00Z');

describe('fieldStateAge', () => {
  it('null when unset or in the future', () => {
    expect(fieldStateAge(null, NOW)).toBeNull();
    expect(fieldStateAge(undefined, NOW)).toBeNull();
    expect(fieldStateAge('2026-09-26T12:55:01Z', NOW)).toBeNull();
  });

  it('sub-minute, minutes, hours, days', () => {
    expect(fieldStateAge('2026-09-26T12:55:00Z', NOW)).toBe('hace menos de 1 min');
    expect(fieldStateAge('2026-09-26T12:54:30Z', NOW)).toBe('hace menos de 1 min');
    expect(fieldStateAge('2026-09-26T12:54:00Z', NOW)).toBe('hace 1 min');
    expect(fieldStateAge('2026-09-26T11:55:00Z', NOW)).toBe('hace 1 h');
    expect(fieldStateAge('2026-09-25T12:55:00Z', NOW)).toBe('hace 1 d');
    expect(fieldStateAge('2026-09-24T12:55:00Z', NOW)).toBe('hace 2 d');
  });

  it('labels', () => {
    expect(QUICK_ACTION_LABELS).toEqual({ en_route: 'Voy en camino', arrived: 'Llegué / estoy afuera' });
  });
});
