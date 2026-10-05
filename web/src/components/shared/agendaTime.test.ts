import { describe, expect, it } from 'vitest';
import {
  agendaDayKey,
  agendaDayNumber,
  agendaDayLabel,
  agendaMonthDays,
  agendaMonthLabel,
  agendaPeriodLabel,
  agendaShiftPeriod,
  agendaTodayKey,
  agendaWeekDays,
  agendaWeekdayLabels,
  composeAgendaTime,
  formatAgendaSlot,
} from './agendaTime';

describe('agenda time contract', () => {
  it('formats slots in the appointment timezone using 24-hour time', () => {
    expect(formatAgendaSlot('2026-09-05T18:30:00+00:00', 'America/Santiago')).toBe('14:30');
  });

  it('returns a comparable local calendar day key', () => {
    expect(agendaDayKey('2026-09-05T03:30:00+00:00', 'America/Santiago')).toBe('2026-09-04');
  });

  it('derives today from the requested timezone', () => {
    expect(agendaTodayKey('Pacific/Kiritimati')).toBe(
      new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Pacific/Kiritimati',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date()),
    );
  });

  it('formats month and period labels in Chilean Spanish', () => {
    expect(agendaMonthLabel('2026-09-24', 'America/Santiago')).toBe('Septiembre de 2026');
    expect(agendaPeriodLabel('2026-09-24', 'America/Santiago')).toBe('Jueves 24 de septiembre');
    expect(agendaPeriodLabel('2026-10-04', 'America/Santiago')).toBe('Domingo 4 de octubre');
    expect(agendaDayNumber('2026-09-04')).toBe('4');
  });

  it('formats a compact capitalized date for each agenda visit', () => {
    expect(agendaDayLabel('2026-10-06', 'America/Santiago')).toBe('Mar 6 oct');
  });

  it.each([
    ['2026-01-01', 31],
    ['2026-02-01', 28],
    ['2028-02-01', 29],
    ['2026-04-01', 30],
    ['2026-12-01', 31],
  ])('lists exactly the days in %s without adjacent-month spillover', (anchor, count) => {
    const days = agendaMonthDays(anchor, 'America/Santiago');

    expect(days).toHaveLength(count);
    expect(days[0]).toBe(anchor);
    expect(days.every((day) => day.startsWith(anchor.slice(0, 7)))).toBe(true);
    expect(days.at(-1)?.slice(8)).toBe(String(count).padStart(2, '0'));
  });

  it('lists Monday-first weeks for every possible month start weekday', () => {
    const anchors = Array.from({ length: 12 }, (_, month) => `2026-${String(month + 1).padStart(2, '0')}-01`);

    for (const anchor of anchors) {
      const days = agendaWeekDays(anchor, 'America/Santiago');
      expect(days).toHaveLength(7);
      expect(new Date(`${days[0]}T12:00:00Z`).getUTCDay()).toBe(1);
      expect(days).toEqual([...days].sort());
    }
  });

  it('returns Monday-first weekday labels', () => {
    expect(agendaWeekdayLabels('America/Santiago')).toEqual(['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']);
  });

  it('shifts month and week periods across both year boundaries', () => {
    expect(agendaShiftPeriod('2026-01-15', 'month', -1, 'America/Santiago')).toBe('2025-12-01');
    expect(agendaShiftPeriod('2025-12-15', 'month', 1, 'America/Santiago')).toBe('2026-01-01');
    expect(agendaShiftPeriod('2026-01-01', 'week', -1, 'America/Santiago')).toBe('2025-12-22');
    expect(agendaShiftPeriod('2025-12-31', 'week', 1, 'America/Santiago')).toBe('2026-01-05');
    expect(agendaShiftPeriod('2026-01-01', 'month', 0, 'America/Santiago')).toBe(agendaTodayKey('America/Santiago'));
    expect(agendaShiftPeriod('2026-01-01', 'week', 0, 'America/Santiago')).toBe(agendaTodayKey('America/Santiago'));
  });

  it('composes a valid local date and time into appointment payload parts', () => {
    expect(composeAgendaTime('2026-09-05', '14:30', 'America/Santiago')).toEqual({
      local_date: '2026-09-05',
      local_time: '14:30:00',
      timezone: 'America/Santiago',
    });
  });

  it('reports nonexistent and ambiguous local times distinctly', () => {
    expect(() => composeAgendaTime('2026-03-08', '02:30', 'America/New_York')).toThrow('does not exist');
    expect(() => composeAgendaTime('2026-11-01', '01:30', 'America/New_York')).toThrow('ambiguous');
  });
});
