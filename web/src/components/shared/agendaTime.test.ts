import { describe, expect, it } from 'vitest';
import { agendaDayKey, formatAgendaSlot } from './agendaTime';

describe('agenda time contract', () => {
  it('formats slots in the appointment timezone using 24-hour time', () => {
    expect(formatAgendaSlot('2026-09-05T18:30:00+00:00', 'America/Santiago')).toBe('14:30');
  });

  it('returns a comparable local calendar day key', () => {
    expect(agendaDayKey('2026-09-05T03:30:00+00:00', 'America/Santiago')).toBe('2026-09-04');
  });
});
