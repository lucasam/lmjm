import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { datetimeLocalToApi } from '../datetimeConvert';

/**
 * Feature: datetime-precision, Property 3: Frontend datetime-local to API format conversion
 * Validates: Requirements 3.2, 4.2
 */
describe('datetimeLocalToApi property tests', () => {
  const pad = (n: number): string => n.toString().padStart(2, '0');

  const yearArb = fc.integer({ min: 2000, max: 2099 });
  const monthArb = fc.integer({ min: 1, max: 12 });
  const dayArb = (month: number, year: number) => {
    const daysInMonth = new Date(year, month, 0).getDate();
    return fc.integer({ min: 1, max: daysInMonth });
  };
  const hourArb = fc.integer({ min: 0, max: 23 });
  const minuteArb = fc.integer({ min: 0, max: 59 });

  it('produces a 12-character numeric string and round-trips to original components', () => {
    fc.assert(
      fc.property(
        yearArb,
        monthArb,
        hourArb,
        minuteArb,
        (year, month, hour, minute) => {
          fc.assert(
            fc.property(dayArb(month, year), (day) => {
              const input = `${year}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}`;
              const result = datetimeLocalToApi(input);

              // Must be exactly 12 characters
              expect(result).toHaveLength(12);

              // Must be all digits
              expect(result).toMatch(/^\d{12}$/);

              // Parse back the components
              const rYear = parseInt(result.substring(0, 4), 10);
              const rMonth = parseInt(result.substring(4, 6), 10);
              const rDay = parseInt(result.substring(6, 8), 10);
              const rHour = parseInt(result.substring(8, 10), 10);
              const rMinute = parseInt(result.substring(10, 12), 10);

              // Components must match the original input
              expect(rYear).toBe(year);
              expect(rMonth).toBe(month);
              expect(rDay).toBe(day);
              expect(rHour).toBe(hour);
              expect(rMinute).toBe(minute);
            }),
            { numRuns: 1 },
          );
        },
      ),
      { numRuns: 100 },
    );
  });
});
