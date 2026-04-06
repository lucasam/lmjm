import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { formatDate } from '../index';

/**
 * Feature: datetime-precision, Property 4: formatDate renders datetime and date strings correctly
 * Validates: Requirements 5.1, 5.2
 */
describe('formatDate property tests', () => {
  // Generators for valid date/time components
  const yearArb = fc.integer({ min: 2000, max: 2099 });
  const monthArb = fc.integer({ min: 1, max: 12 });
  const dayArb = (month: number, year: number) => {
    const daysInMonth = new Date(year, month, 0).getDate();
    return fc.integer({ min: 1, max: daysInMonth });
  };
  const hourArb = fc.integer({ min: 0, max: 23 });
  const minuteArb = fc.integer({ min: 0, max: 59 });

  const pad = (n: number): string => n.toString().padStart(2, '0');

  it('renders YYYY-MM-DDTHH:MM as DD/MM/YYYY HH:MM with matching components', () => {
    fc.assert(
      fc.property(
        yearArb,
        monthArb,
        hourArb,
        minuteArb,
        fc.context(),
        (year, month, hour, minute, ctx) => {
          return fc.assert(
            fc.property(dayArb(month, year), (day) => {
              const input = `${year}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}`;
              const result = formatDate(input);
              ctx.log(`input=${input}, result=${result}`);

              // Should match DD/MM/YYYY HH:MM format
              const match = result.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/);
              expect(match).not.toBeNull();

              // Components should match input
              expect(match![1]).toBe(pad(day));
              expect(match![2]).toBe(pad(month));
              expect(match![3]).toBe(year.toString());
              expect(match![4]).toBe(pad(hour));
              expect(match![5]).toBe(pad(minute));
            }),
            { numRuns: 1 }
          );
        }
      ),
      { numRuns: 100 }
    );
  });

  it('renders YYYY-MM-DD as DD/MM/YYYY with matching components', () => {
    fc.assert(
      fc.property(
        yearArb,
        monthArb,
        fc.context(),
        (year, month, ctx) => {
          return fc.assert(
            fc.property(dayArb(month, year), (day) => {
              const input = `${year}-${pad(month)}-${pad(day)}`;
              const result = formatDate(input);
              ctx.log(`input=${input}, result=${result}`);

              // Should match DD/MM/YYYY format (no time)
              const match = result.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
              expect(match).not.toBeNull();

              // Components should match input
              expect(match![1]).toBe(pad(day));
              expect(match![2]).toBe(pad(month));
              expect(match![3]).toBe(year.toString());
            }),
            { numRuns: 1 }
          );
        }
      ),
      { numRuns: 100 }
    );
  });
});
