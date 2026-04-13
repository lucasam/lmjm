// TypeScript port of bordero_calculator.py and cap_map_calculator.py
// Uses standard number type for live preview (backend uses Decimal for persistence precision)

const GROSS_INTEGRATOR_PCT = 5.1;

/** Round to 4 decimal places (mirrors Python Decimal.quantize("0.0001")) */
function q(value: number): number {
  return Math.round(value * 10000) / 10000;
}

// ---------------------------------------------------------------------------
// calculateBordero
// ---------------------------------------------------------------------------

export interface BorderoInput {
  housedCount: number;
  mortalityCount: number;
  pigletWeight: number;
  pigWeight: number;
  totalFeed: number;
  daysHoused: number;
  cap: number;
  mapValue: number;
  pricePerKg: number;
  pigletAdjustment: number;
  carcassAdjustment: number;
}

export interface BorderoResult {
  housedCount: number;
  mortalityCount: number;
  pigCount: number;
  pigletWeight: number;
  pigWeight: number;
  totalFeed: number;
  daysHoused: number;
  cap: number;
  mapValue: number;
  pricePerKg: number;
  grossIntegratorPct: number;
  carcassYieldFactor: number;
  pigletCarcassWeight: number;
  pigCarcassWeight: number;
  totalPigletCarcass: number;
  totalPigCarcass: number;
  totalCarcassProduced: number;
  realConversion: number;
  pigletAdjustment: number;
  carcassAdjustment: number;
  adjustedConversion: number;
  dailyWeightGain: number;
  dailyCarcassGain: number;
  realMortalityPct: number;
  adjustedMortalityPct: number;
  mortalityAdjustmentPct: number;
  conversionAdjustmentPct: number;
  integratorPct: number;
  grossIncome: number;
  netIncome: number;
  grossIncomePerPig: number;
  netIncomePerPig: number;
}

/**
 * Pure function: computes all derived Borderô fields.
 * Returns null instead of throwing for invalid input (used in live preview).
 */
export function calculateBordero(inp: BorderoInput): BorderoResult | null {
  if (inp.housedCount === 0) return null;
  if (inp.daysHoused <= 0) return null;

  const pigCount = inp.housedCount - inp.mortalityCount;
  if (pigCount <= 0) return null;

  // Carcass calculations
  const carcassYieldFactor = q((inp.pigWeight - 6.629) / 1.289);
  const pigletCarcassWeight = q(inp.pigletWeight * carcassYieldFactor);
  const pigCarcassWeight = q(inp.pigWeight * carcassYieldFactor);
  const totalPigletCarcass = q(pigletCarcassWeight * inp.housedCount);
  const totalPigCarcass = q(pigCarcassWeight * pigCount);
  const totalCarcassProduced = q(totalPigCarcass - totalPigletCarcass);

  if (totalCarcassProduced <= 0) return null;

  // Feed conversion
  const realConversion = q(inp.totalFeed / totalCarcassProduced);
  const adjustedConversion = q(realConversion + inp.pigletAdjustment + inp.carcassAdjustment);

  // Mortality
  const realMortalityPct = q((inp.mortalityCount / inp.housedCount) * 100);
  const adjustedMortalityPct = realMortalityPct;

  // Integrator percentage adjustments
  const mortalityAdjustmentPct = q(inp.mapValue - adjustedMortalityPct);
  const conversionAdjustmentPct = q(inp.cap - adjustedConversion);
  const integratorPct = q(GROSS_INTEGRATOR_PCT + mortalityAdjustmentPct + conversionAdjustmentPct);

  // Financial result
  const grossIncome = q(totalCarcassProduced * inp.pricePerKg * integratorPct / 100);
  const netIncome = grossIncome;

  // Performance
  const dailyWeightGain = q((inp.pigWeight - inp.pigletWeight) / inp.daysHoused);
  const dailyCarcassGain = q((pigCarcassWeight - pigletCarcassWeight) / inp.daysHoused);

  // Per-pig metrics
  const grossIncomePerPig = q(grossIncome / pigCount);
  const netIncomePerPig = q(netIncome / pigCount);

  return {
    housedCount: inp.housedCount,
    mortalityCount: inp.mortalityCount,
    pigCount,
    pigletWeight: inp.pigletWeight,
    pigWeight: inp.pigWeight,
    totalFeed: inp.totalFeed,
    daysHoused: inp.daysHoused,
    cap: inp.cap,
    mapValue: inp.mapValue,
    pricePerKg: inp.pricePerKg,
    grossIntegratorPct: GROSS_INTEGRATOR_PCT,
    carcassYieldFactor,
    pigletCarcassWeight,
    pigCarcassWeight,
    totalPigletCarcass,
    totalPigCarcass,
    totalCarcassProduced,
    realConversion,
    pigletAdjustment: inp.pigletAdjustment,
    carcassAdjustment: inp.carcassAdjustment,
    adjustedConversion,
    dailyWeightGain,
    dailyCarcassGain,
    realMortalityPct,
    adjustedMortalityPct,
    mortalityAdjustmentPct,
    conversionAdjustmentPct,
    integratorPct,
    grossIncome,
    netIncome,
    grossIncomePerPig,
    netIncomePerPig,
  };
}

// ---------------------------------------------------------------------------
// computeCapMap
// ---------------------------------------------------------------------------

export interface CapMapResult {
  cap1: number;
  cap2: number;
  cap3: number;
  cap4: number;
  map1: number;
  map2: number;
}

/**
 * Computes CAP(1-4) and MAP(1-2) from integrator weekly data.
 */
export function computeCapMap(
  car: number,
  mar: number,
  avgSlaughterWeight: number,
  avgPigletWeight: number,
  averageAge: number,
): CapMapResult {
  const cap1 = q(car - (avgSlaughterWeight - 85) * 0.0095 - (avgPigletWeight - 22) * 0.0125);
  const cap2 = q(cap1 - 0.03);
  const cap3 = q(cap2 - 0.015);
  const cap4 = q(cap1 - 0.015);
  const map1 = q((130 - averageAge) * 0.0183 + mar);
  const map2 = q(map1 - 0.4);
  return { cap1, cap2, cap3, cap4, map1, map2 };
}

// ---------------------------------------------------------------------------
// selectCapMapVariant
// ---------------------------------------------------------------------------

export interface IntegratorWeeklyDataRecord {
  dateGenerated: string;
  validityStart: string;
  validityEnd: string;
  cap1: number;
  cap2: number;
  cap3: number;
  cap4: number;
  map1: number;
  map2: number;
}

/**
 * Selects the correct CAP and MAP variant based on batch characteristics.
 *
 * CAP selection:
 *   >2 origins + Creche → CAP(1)
 *   ≤2 origins + Creche → CAP(2)
 *   ≤2 origins + UPL    → CAP(3)
 *   >2 origins + UPL    → CAP(4)
 *
 * MAP selection:
 *   ≤2 origins → MAP(1)
 *   >2 origins → MAP(2)
 */
export function selectCapMapVariant(
  distinctOriginCount: number,
  predominantOriginType: "Creche" | "UPL",
  weeklyData: IntegratorWeeklyDataRecord,
): { cap: number; map: number } {
  let cap: number;
  if (predominantOriginType === "Creche") {
    cap = distinctOriginCount > 2 ? weeklyData.cap1 : weeklyData.cap2;
  } else {
    cap = distinctOriginCount > 2 ? weeklyData.cap4 : weeklyData.cap3;
  }

  const map = distinctOriginCount > 2 ? weeklyData.map2 : weeklyData.map1;

  return { cap, map };
}

// ---------------------------------------------------------------------------
// findNearestWeeklyData
// ---------------------------------------------------------------------------

/**
 * Finds the IntegratorWeeklyData record whose validity period contains the
 * target date. If none matches, returns the record with the nearest
 * dateGenerated to the target date.
 *
 * Returns undefined if the records array is empty.
 */
export function findNearestWeeklyData(
  records: IntegratorWeeklyDataRecord[],
  targetDate: string,
): IntegratorWeeklyDataRecord | undefined {
  if (records.length === 0) return undefined;

  // First: look for a record whose validity period contains the target date
  for (const record of records) {
    if (record.validityStart <= targetDate && targetDate <= record.validityEnd) {
      return record;
    }
  }

  // Fallback: find the record with the nearest dateGenerated
  let nearest = records[0];
  let minDiff = Math.abs(new Date(targetDate).getTime() - new Date(nearest.dateGenerated).getTime());

  for (let i = 1; i < records.length; i++) {
    const diff = Math.abs(new Date(targetDate).getTime() - new Date(records[i].dateGenerated).getTime());
    if (diff < minDiff) {
      minDiff = diff;
      nearest = records[i];
    }
  }

  return nearest;
}
