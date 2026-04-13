import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { selectCapMapVariant, IntegratorWeeklyDataRecord } from "../borderoCalculator";

/**
 * Feature: batch-financial-result, Property 4: CAP/MAP variant selection
 * Validates: Requirements 13.2, 13.3
 *
 * For any distinct_origin_count (1–10) and origin_type (Creche/UPL),
 * verify the correct CAP/MAP variant is selected based on the selection table:
 *   >2 origins + Creche → cap1, map2
 *   ≤2 origins + Creche → cap2, map1
 *   ≤2 origins + UPL    → cap3, map1
 *   >2 origins + UPL    → cap4, map2
 */
describe("Property 4: CAP/MAP variant selection", () => {
  const weeklyDataArb = fc.record({
    dateGenerated: fc.constant("2024-01-15"),
    validityStart: fc.constant("2024-01-08"),
    validityEnd: fc.constant("2024-01-22"),
    cap1: fc.float({ min: 1, max: 5, noNaN: true }),
    cap2: fc.float({ min: 1, max: 5, noNaN: true }),
    cap3: fc.float({ min: 1, max: 5, noNaN: true }),
    cap4: fc.float({ min: 1, max: 5, noNaN: true }),
    map1: fc.float({ min: 1, max: 10, noNaN: true }),
    map2: fc.float({ min: 1, max: 10, noNaN: true }),
  }) as fc.Arbitrary<IntegratorWeeklyDataRecord>;

  const distinctOriginCountArb = fc.integer({ min: 1, max: 10 });
  const originTypeArb = fc.constantFrom("Creche" as const, "UPL" as const);

  it("should select the correct CAP variant based on origin count and type", () => {
    fc.assert(
      fc.property(
        distinctOriginCountArb,
        originTypeArb,
        weeklyDataArb,
        (distinctOriginCount, originType, weeklyData) => {
          const result = selectCapMapVariant(distinctOriginCount, originType, weeklyData);

          if (distinctOriginCount > 2 && originType === "Creche") {
            expect(result.cap).toBe(weeklyData.cap1);
          } else if (distinctOriginCount <= 2 && originType === "Creche") {
            expect(result.cap).toBe(weeklyData.cap2);
          } else if (distinctOriginCount <= 2 && originType === "UPL") {
            expect(result.cap).toBe(weeklyData.cap3);
          } else {
            // >2 origins + UPL
            expect(result.cap).toBe(weeklyData.cap4);
          }
        },
      ),
      { numRuns: 200 },
    );
  });

  it("should select the correct MAP variant based on origin count", () => {
    fc.assert(
      fc.property(
        distinctOriginCountArb,
        originTypeArb,
        weeklyDataArb,
        (distinctOriginCount, originType, weeklyData) => {
          const result = selectCapMapVariant(distinctOriginCount, originType, weeklyData);

          if (distinctOriginCount <= 2) {
            expect(result.map).toBe(weeklyData.map1);
          } else {
            expect(result.map).toBe(weeklyData.map2);
          }
        },
      ),
      { numRuns: 200 },
    );
  });
});

import { findNearestWeeklyData } from "../borderoCalculator";

/**
 * Feature: batch-financial-result, Property 5: IntegratorWeeklyData lookup with nearest fallback
 * Validates: Requirements 13.1
 *
 * For any non-empty list of IntegratorWeeklyData records with validity periods
 * and any target date, the lookup function SHALL return:
 *   - The record whose validity period contains the target date, if one exists
 *   - Otherwise, the record with the nearest dateGenerated to the target date
 */
describe("Property 5: IntegratorWeeklyData lookup with nearest fallback", () => {
  /** Format a Date as YYYY-MM-DD */
  function toDateStr(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  /** Arbitrary that produces a YYYY-MM-DD string within a reasonable range */
  const dateArb = fc
    .integer({ min: 0, max: 3650 }) // up to ~10 years of days
    .map((offset) => {
      const d = new Date(2020, 0, 1);
      d.setDate(d.getDate() + offset);
      return toDateStr(d);
    });

  /** Arbitrary for a single IntegratorWeeklyDataRecord with a validity window */
  const weeklyRecordArb = fc
    .tuple(
      dateArb, // dateGenerated
      fc.integer({ min: 0, max: 3650 }), // validity start offset
      fc.integer({ min: 1, max: 30 }), // validity window length in days
      fc.float({ min: 1, max: 5, noNaN: true }),
      fc.float({ min: 1, max: 5, noNaN: true }),
      fc.float({ min: 1, max: 5, noNaN: true }),
      fc.float({ min: 1, max: 5, noNaN: true }),
      fc.float({ min: 1, max: 10, noNaN: true }),
      fc.float({ min: 1, max: 10, noNaN: true }),
    )
    .map(([dateGenerated, startOffset, windowLen, cap1, cap2, cap3, cap4, map1, map2]) => {
      const start = new Date(2020, 0, 1);
      start.setDate(start.getDate() + startOffset);
      const end = new Date(start);
      end.setDate(end.getDate() + windowLen);
      return {
        dateGenerated,
        validityStart: toDateStr(start),
        validityEnd: toDateStr(end),
        cap1,
        cap2,
        cap3,
        cap4,
        map1,
        map2,
      } as IntegratorWeeklyDataRecord;
    });

  const nonEmptyRecordsArb = fc.array(weeklyRecordArb, { minLength: 1, maxLength: 10 });

  it("should return a record whose validity period contains the target date when one exists", () => {
    fc.assert(
      fc.property(nonEmptyRecordsArb, dateArb, (records, targetDate) => {
        const result = findNearestWeeklyData(records, targetDate);
        expect(result).toBeDefined();

        // Check if any record's validity period contains the target date
        const containingRecord = records.find(
          (r) => r.validityStart <= targetDate && targetDate <= r.validityEnd,
        );

        if (containingRecord) {
          // The result must be a record whose validity period contains the target date
          expect(result!.validityStart <= targetDate && targetDate <= result!.validityEnd).toBe(
            true,
          );
        }
      }),
      { numRuns: 200 },
    );
  });

  it("should return the record with the nearest dateGenerated when no validity period matches", () => {
    fc.assert(
      fc.property(nonEmptyRecordsArb, dateArb, (records, targetDate) => {
        const result = findNearestWeeklyData(records, targetDate);
        expect(result).toBeDefined();

        // Check if any record's validity period contains the target date
        const containingRecord = records.find(
          (r) => r.validityStart <= targetDate && targetDate <= r.validityEnd,
        );

        if (!containingRecord) {
          // No validity match — result should be the nearest by dateGenerated
          const targetTime = new Date(targetDate).getTime();
          const resultDiff = Math.abs(targetTime - new Date(result!.dateGenerated).getTime());

          for (const r of records) {
            const diff = Math.abs(targetTime - new Date(r.dateGenerated).getTime());
            expect(resultDiff).toBeLessThanOrEqual(diff);
          }
        }
      }),
      { numRuns: 200 },
    );
  });
});
