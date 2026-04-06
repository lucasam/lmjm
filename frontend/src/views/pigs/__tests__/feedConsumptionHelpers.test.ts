import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { filterArrivalsInPeriod, computePeriodDays } from '../FeedConsumptionDataView';
import type { FeedTruckArrival } from '../../../types/models';

const pad = (n: number): string => n.toString().padStart(2, '0');

/** Generate a valid YYYY-MM-DDTHH:MM datetime string. */
const datetimeArb = (): fc.Arbitrary<string> =>
  fc.tuple(
    fc.integer({ min: 2020, max: 2030 }),
    fc.integer({ min: 1, max: 12 }),
    fc.integer({ min: 1, max: 28 }), // safe day range for all months
    fc.integer({ min: 0, max: 23 }),
    fc.integer({ min: 0, max: 59 }),
  ).map(([y, mo, d, h, mi]) =>
    `${y}-${pad(mo)}-${pad(d)}T${pad(h)}:${pad(mi)}`
  );

/** Generate a sorted pair of distinct datetime strings (prev < curr). */
const sortedDatetimePairArb = (): fc.Arbitrary<[string, string]> =>
  fc.tuple(datetimeArb(), datetimeArb())
    .filter(([a, b]) => a < b)
    .map(([a, b]) => [a, b] as [string, string]);

/** Build a minimal FeedTruckArrival with the given receive_date. */
function makeArrival(receiveDate: string, amount: number = 100): FeedTruckArrival {
  return {
    pk: 'BATCH#1',
    sk: `FeedTruckArrival|${receiveDate.replace(/[-T:]/g, '')}|uuid`,
    receive_date: receiveDate,
    fiscal_document_number: '000',
    actual_amount_kg: amount,
    feed_type: '001',
  };
}

/**
 * Feature: datetime-precision, Property 5: Arrival attribution uses full datetime comparison
 * Validates: Requirements 6.1, 6.2
 */
describe('filterArrivalsInPeriod property tests', () => {
  it('includes exactly arrivals where receive_date > prev and receive_date <= curr (lexicographic)', () => {
    fc.assert(
      fc.property(
        sortedDatetimePairArb(),
        fc.array(datetimeArb(), { minLength: 0, maxLength: 20 }),
        ([prev, curr], receiveDates) => {
          const arrivals = receiveDates.map(rd => makeArrival(rd));
          const result = filterArrivalsInPeriod(arrivals, prev, curr);

          // Expected: exactly those arrivals where receive_date > prev AND receive_date <= curr
          const expected = arrivals.filter(a => a.receive_date > prev && a.receive_date <= curr);

          expect(result.length).toBe(expected.length);
          for (const a of result) {
            expect(a.receive_date > prev).toBe(true);
            expect(a.receive_date <= curr).toBe(true);
          }
          // Every arrival matching the condition is included
          for (const a of expected) {
            expect(result).toContain(a);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});


/**
 * Feature: datetime-precision, Property 6: Period days calculation ignores time component
 * Validates: Requirements 6.3
 */
describe('computePeriodDays property tests', () => {
  /** Generate a time string HH:MM */
  const timeArb = (): fc.Arbitrary<string> =>
    fc.tuple(
      fc.integer({ min: 0, max: 23 }),
      fc.integer({ min: 0, max: 59 }),
    ).map(([h, m]) => `${pad(h)}:${pad(m)}`);

  /** Generate a date string YYYY-MM-DD with safe day range */
  const dateArb = (): fc.Arbitrary<string> =>
    fc.tuple(
      fc.integer({ min: 2020, max: 2030 }),
      fc.integer({ min: 1, max: 12 }),
      fc.integer({ min: 1, max: 28 }),
    ).map(([y, mo, d]) => `${y}-${pad(mo)}-${pad(d)}`);

  /** Generate a sorted pair of distinct date strings */
  const sortedDatePairArb = (): fc.Arbitrary<[string, string]> =>
    fc.tuple(dateArb(), dateArb())
      .filter(([a, b]) => a < b)
      .map(([a, b]) => [a, b] as [string, string]);

  it('changing only the time portion of either measurement does not change the days count', () => {
    fc.assert(
      fc.property(
        sortedDatePairArb(),
        timeArb(),
        timeArb(),
        timeArb(),
        timeArb(),
        (dates, time1a, time1b, time2a, time2b) => {
          const [date1, date2] = dates;

          const dt1a = `${date1}T${time1a}`;
          const dt2a = `${date2}T${time2a}`;
          const dt1b = `${date1}T${time1b}`;
          const dt2b = `${date2}T${time2b}`;

          const daysA = computePeriodDays(dt1a, dt2a);
          const daysB = computePeriodDays(dt1b, dt2b);

          // Same date portions → same days count regardless of time
          expect(daysA).toBe(daysB);

          // Days should equal whole calendar days between date portions
          const d1 = new Date(date1 + 'T00:00:00');
          const d2 = new Date(date2 + 'T00:00:00');
          const expectedDays = Math.max(1, Math.round((d2.getTime() - d1.getTime()) / 86400000));
          expect(daysA).toBe(expectedDays);
        },
      ),
      { numRuns: 100 },
    );
  });
});
