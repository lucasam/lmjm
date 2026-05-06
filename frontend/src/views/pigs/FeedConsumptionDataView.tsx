import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import {
  getBatch,
  listFeedBalances,
  listFeedTruckArrivals,
  listMortalities,
  getFeedConsumptionPlan,
} from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type {
  Batch,
  FeedBalance,
  FeedTruckArrival,
  Mortality,
  FeedConsumptionPlanEntry,
} from '../../types/models';

interface ConsumptionRow {
  periodStart: string;
  periodEnd: string;
  days: number;
  totalConsumed: number;
  cumulativeConsumed: number;
  liveAnimals: number;
  consumptionPerPig: number;
  expectedConsumptionPerPig: number | null;
  dailyPerAnimal: number;
  plannedDailyPerAnimal: number | null;
  expectedPigletWeight: number | null;
  totalFeedReceived: number;
  balanceKg: number;
  totalFeedConsumedCalc: number;
}

function getCumulativeDeathsUpTo(mortalities: Mortality[], dateStr: string): number {
  let count = 0;
  for (const m of mortalities) {
    if (m.mortality_date <= dateStr) count++;
  }
  return count;
}

/**
 * Filter arrivals whose receive_date falls in the half-open interval (prevDatetime, currDatetime]
 * using full datetime string comparison (lexicographic on YYYY-MM-DDTHH:MM).
 */
export function filterArrivalsInPeriod(
  arrivals: FeedTruckArrival[],
  prevDatetime: string,
  currDatetime: string,
): FeedTruckArrival[] {
  return arrivals.filter(a => a.receive_date > prevDatetime && a.receive_date <= currDatetime);
}

/**
 * Compute the number of whole calendar days between two datetime strings.
 * Extracts the date portion only (YYYY-MM-DD via substring(0,10)) so that
 * the time component does not affect the result.
 */
export function computePeriodDays(prevDatetime: string, currDatetime: string): number {
  const d1 = new Date(prevDatetime.substring(0, 10) + 'T00:00:00');
  const d2 = new Date(currDatetime.substring(0, 10) + 'T00:00:00');
  return Math.max(1, Math.round((d2.getTime() - d1.getTime()) / 86400000));
}

function computeConsumptionData(
  batch: Batch,
  balances: FeedBalance[],
  arrivals: FeedTruckArrival[],
  mortalities: Mortality[],
  plan: FeedConsumptionPlanEntry[],
): ConsumptionRow[] {
  const totalAnimals = batch.total_animal_count ?? 0;
  if (totalAnimals === 0 || balances.length < 2) return [];

  const sortedBalances = [...balances].sort((a, b) => a.measurement_date.localeCompare(b.measurement_date));
  const receiveDate = batch.average_start_date ?? '';

  const planByDay: Record<number, number> = {};
  const weightByDay: Record<number, number> = {};
  for (const p of plan) {
    planByDay[p.day_number] = p.expected_kg_per_animal;
    if (p.expected_piglet_weight > 0) {
      weightByDay[p.day_number] = p.expected_piglet_weight;
    }
  }

  const rows: ConsumptionRow[] = [];
  let cumulativeConsumed = 0;
  let cumulativeFeedReceived = 0;

  // Count feed received up to the first balance (before the loop starts)
  const firstBalanceDatetime = sortedBalances[0].measurement_date;
  for (const a of arrivals) {
    if (a.receive_date <= firstBalanceDatetime) {
      cumulativeFeedReceived += a.actual_amount_kg;
    }
  }

  for (let i = 1; i < sortedBalances.length; i++) {
    const prev = sortedBalances[i - 1];
    const curr = sortedBalances[i];

    const prevDatetime = prev.measurement_date;
    const currDatetime = curr.measurement_date;

    // Arrival attribution uses full datetime string comparison
    const periodArrivals = filterArrivalsInPeriod(arrivals, prevDatetime, currDatetime);
    let deliveredInPeriod = 0;
    for (const a of periodArrivals) {
      deliveredInPeriod += a.actual_amount_kg;
    }
    cumulativeFeedReceived += deliveredInPeriod;

    const totalConsumed = prev.balance_kg + deliveredInPeriod - curr.balance_kg;
    cumulativeConsumed += totalConsumed;

    // Period days uses date portion only (ignores time component)
    const days = computePeriodDays(prevDatetime, currDatetime);

    const deaths = getCumulativeDeathsUpTo(mortalities, currDatetime);
    const liveAnimals = Math.max(1, totalAnimals - deaths);

    // Change 1: consumptionPerPig is cumulative total up to date / liveAnimals
    const consumptionPerPig = cumulativeConsumed / liveAnimals;
    const dailyPerAnimal = totalConsumed / (liveAnimals * days);

    const currDateOnly = currDatetime.substring(0, 10);
    const d2 = new Date(currDateOnly + 'T00:00:00');
    const recDate = new Date(receiveDate.substring(0, 10) + 'T00:00:00');
    const dayEnd = Math.floor((d2.getTime() - recDate.getTime()) / 86400000);

    const prevDateOnly = prevDatetime.substring(0, 10);
    const d1 = new Date(prevDateOnly + 'T00:00:00');
    const dayStart = Math.floor((d1.getTime() - recDate.getTime()) / 86400000) + 1;

    // Planned daily average for this period
    let plannedSum = 0;
    let plannedCount = 0;
    for (let d = Math.max(1, dayStart); d <= Math.min(300, dayEnd); d++) {
      if (planByDay[d] != null) {
        plannedSum += planByDay[d];
        plannedCount++;
      }
    }
    const plannedDailyPerAnimal = plannedCount > 0 ? plannedSum / plannedCount : null;

    // Change 3: expected cumulative consumption per pig from plan (sum from day 1 to dayEnd)
    let expectedCumulativeSum = 0;
    let hasExpectedData = false;
    for (let d = 1; d <= Math.min(300, dayEnd); d++) {
      if (planByDay[d] != null) {
        expectedCumulativeSum += planByDay[d];
        hasExpectedData = true;
      }
    }
    const expectedConsumptionPerPig = hasExpectedData ? expectedCumulativeSum : null;

    // Use the weight at the end of the period
    const expectedPigletWeight = weightByDay[dayEnd] ?? null;

    rows.push({
      periodStart: prevDatetime,
      periodEnd: currDatetime,
      days,
      totalConsumed,
      cumulativeConsumed,
      liveAnimals,
      consumptionPerPig,
      expectedConsumptionPerPig,
      dailyPerAnimal,
      plannedDailyPerAnimal,
      expectedPigletWeight,
      totalFeedReceived: cumulativeFeedReceived,
      balanceKg: curr.balance_kg,
      totalFeedConsumedCalc: cumulativeFeedReceived - curr.balance_kg,
    });
  }

  return rows;
}

// --- Simple SVG line chart ---

interface ChartPoint {
  label: string;
  actual: number | null;
  planned: number | null;
}

function ConsumptionChart({ points }: { points: ChartPoint[] }) {
  if (points.length === 0) return null;

  const W = 700;
  const H = 300;
  const PAD_L = 60;
  const PAD_R = 20;
  const PAD_T = 20;
  const PAD_B = 60;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const allVals = points.flatMap(p => [p.actual, p.planned]).filter((v): v is number => v != null);
  if (allVals.length === 0) return null;
  const minY = 0;
  const maxY = Math.max(...allVals) * 1.1 || 1;

  const xStep = points.length > 1 ? plotW / (points.length - 1) : 0;
  const toX = (i: number) => PAD_L + i * xStep;
  const toY = (v: number) => PAD_T + plotH - ((v - minY) / (maxY - minY)) * plotH;

  const buildPath = (key: 'actual' | 'planned') => {
    const segments: string[] = [];
    points.forEach((p, i) => {
      const v = p[key];
      if (v == null) return;
      const cmd = segments.length === 0 ? 'M' : 'L';
      segments.push(`${cmd}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`);
    });
    return segments.join(' ');
  };

  // Y-axis ticks
  const tickCount = 5;
  const yTicks = Array.from({ length: tickCount + 1 }, (_, i) => minY + (maxY - minY) * (i / tickCount));

  return (
    <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
      <svg width={W} height={H} style={{ fontFamily: 'inherit', fontSize: '11px' }}>
        {/* Grid lines */}
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={PAD_L} y1={toY(v)} x2={W - PAD_R} y2={toY(v)} stroke="#e0e0e0" />
            <text x={PAD_L - 6} y={toY(v) + 4} textAnchor="end" fill="#666">{v.toFixed(2)}</text>
          </g>
        ))}

        {/* Actual line (blue) */}
        <path d={buildPath('actual')} fill="none" stroke="#1976d2" strokeWidth={2} />
        {/* Planned line (orange) */}
        <path d={buildPath('planned')} fill="none" stroke="#f57c00" strokeWidth={2} strokeDasharray="6,3" />

        {/* Dots */}
        {points.map((p, i) => (
          <g key={i}>
            {p.actual != null && <circle cx={toX(i)} cy={toY(p.actual)} r={3} fill="#1976d2" />}
            {p.planned != null && <circle cx={toX(i)} cy={toY(p.planned)} r={3} fill="#f57c00" />}
          </g>
        ))}

        {/* X-axis labels */}
        {points.map((p, i) => (
          <text key={i} x={toX(i)} y={H - PAD_B + 16} textAnchor="middle" fill="#666" fontSize="10">
            {p.label}
          </text>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', marginTop: '0.25rem' }}>
        <span><span style={{ color: '#1976d2' }}>■</span> Diário/Animal Real (kg)</span>
        <span><span style={{ color: '#f57c00' }}>■</span> Planejado Diário/Animal (kg)</span>
      </div>
    </div>
  );
}

export default function FeedConsumptionDataView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchBalances = useCallback(() => listFeedBalances(id), [id]);
  const fetchArrivals = useCallback(() => listFeedTruckArrivals(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);
  const fetchPlan = useCallback(() => getFeedConsumptionPlan(id), [id]);

  const { data: batch, loading: l1, error: e1, refetch: r1 } = useApi(fetchBatch);
  const { data: balances, loading: l2, error: e2, refetch: r2 } = useApi(fetchBalances);
  const { data: arrivals, loading: l3, error: e3, refetch: r3 } = useApi(fetchArrivals);
  const { data: mortalities, loading: l4, error: e4, refetch: r4 } = useApi(fetchMortalities);
  const { data: plan, loading: l5, error: e5, refetch: r5 } = useApi(fetchPlan);

  const loading = l1 || l2 || l3 || l4 || l5;
  const error = e1 || e2 || e3 || e4 || e5;
  const refetchAll = () => { r1(); r2(); r3(); r4(); r5(); };

  const rows = useMemo(
    () => (batch && balances && arrivals && mortalities && plan
      ? computeConsumptionData(batch, balances, arrivals, mortalities, plan)
      : []),
    [batch, balances, arrivals, mortalities, plan],
  );

  // Change 5: chart data — actual daily vs planned daily per animal
  const chartPoints: ChartPoint[] = useMemo(() => {
    return rows.map(row => ({
      label: formatDate(row.periodEnd).substring(0, 5),
      actual: row.dailyPerAnimal,
      planned: row.plannedDailyPerAnimal,
    }));
  }, [rows]);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.feedConsumption') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.feedConsumption')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && (
        rows.length === 0 ? (
          <div className="table-empty">
            {t('pigs.noConsumptionData', 'São necessárias pelo menos duas medições de balanço de ração para calcular o consumo.')}
          </div>
        ) : (
          <>
            {/* Change 5: Chart */}
            <ConsumptionChart points={chartPoints} />

            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('pigs.period', 'Período')}</th>
                    {/* Change 4: expectedPigletWeight as second column */}
                    <th>{t('pigs.expectedPigletWeight', 'Peso Esperado (kg)')}</th>
                    <th>{t('pigs.daysLabel', 'Dias')}</th>
                    {/* Change 2: liveAnimals before totalConsumed */}
                    <th>{t('pigs.liveAnimals', 'Animais Vivos')}</th>
                    <th>{t('pigs.totalConsumed', 'Total Consumido (kg)')}</th>
                    {/* Change 1: consumptionPerPig is now cumulative */}
                    <th>{t('pigs.consumptionPerPig', 'Consumo Acum./Animal (kg)')}</th>
                    {/* Change 3: expected cumulative consumption per pig */}
                    <th>{t('pigs.expectedConsumptionPerPig', 'Esperado Acum./Animal (kg)')}</th>
                    <th>{t('pigs.dailyPerAnimal', 'Diário/Animal (kg)')}</th>
                    <th>{t('pigs.plannedDailyPerAnimal', 'Planejado Diário/Animal (kg)')}</th>
                    <th>{t('pigs.totalFeedReceived', 'Total Recebido (kg)')}</th>
                    <th>{t('pigs.balanceKg', 'Balanço (kg)')}</th>
                    <th>{t('pigs.totalFeedConsumedCalc', 'Consumo Total (kg)')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => {
                    const deviation = row.plannedDailyPerAnimal != null
                      ? row.dailyPerAnimal - row.plannedDailyPerAnimal
                      : null;
                    const deviationColor = deviation != null
                      ? (Math.abs(deviation) > row.plannedDailyPerAnimal! * 0.1 ? '#e65100' : undefined)
                      : undefined;

                    return (
                      <tr key={i}>
                        <td>{formatDate(row.periodStart)} – {formatDate(row.periodEnd)}</td>
                        <td>
                          {row.expectedPigletWeight != null ? formatNumber(row.expectedPigletWeight, 1) : '—'}
                        </td>
                        <td>{row.days}</td>
                        <td>{row.liveAnimals}</td>
                        <td>{formatNumber(row.totalConsumed, 1)}</td>
                        <td>{formatNumber(row.consumptionPerPig, 2)}</td>
                        <td>
                          {row.expectedConsumptionPerPig != null ? formatNumber(row.expectedConsumptionPerPig, 2) : '—'}
                        </td>
                        <td style={{ color: deviationColor }}>
                          {formatNumber(row.dailyPerAnimal, 3)}
                        </td>
                        <td>
                          {row.plannedDailyPerAnimal != null ? formatNumber(row.plannedDailyPerAnimal, 3) : '—'}
                        </td>
                        <td>{formatNumber(row.totalFeedReceived, 1)}</td>
                        <td>{formatNumber(row.balanceKg, 1)}</td>
                        <td>{formatNumber(row.totalFeedConsumedCalc, 1)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
