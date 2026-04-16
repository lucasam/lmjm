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
  liveAnimals: number;
  consumptionPerPig: number;
  dailyPerAnimal: number;
  plannedDailyPerAnimal: number | null;
  expectedPigletWeight: number | null;
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

    const totalConsumed = prev.balance_kg + deliveredInPeriod - curr.balance_kg;

    // Period days uses date portion only (ignores time component)
    const days = computePeriodDays(prevDatetime, currDatetime);

    const deaths = getCumulativeDeathsUpTo(mortalities, currDatetime);
    const liveAnimals = Math.max(1, totalAnimals - deaths);

    const consumptionPerPig = totalConsumed / liveAnimals;
    const dailyPerAnimal = totalConsumed / (liveAnimals * days);

    const prevDateOnly = prevDatetime.substring(0, 10);
    const currDateOnly = currDatetime.substring(0, 10);
    const d1 = new Date(prevDateOnly + 'T00:00:00');
    const d2 = new Date(currDateOnly + 'T00:00:00');
    const recDate = new Date(receiveDate.substring(0, 10) + 'T00:00:00');
    const dayStart = Math.floor((d1.getTime() - recDate.getTime()) / 86400000) + 1;
    const dayEnd = Math.floor((d2.getTime() - recDate.getTime()) / 86400000);
    let plannedSum = 0;
    let plannedCount = 0;
    for (let d = Math.max(1, dayStart); d <= Math.min(130, dayEnd); d++) {
      if (planByDay[d] != null) {
        plannedSum += planByDay[d];
        plannedCount++;
      }
    }
    const plannedDailyPerAnimal = plannedCount > 0 ? plannedSum / plannedCount : null;

    // Use the weight at the end of the period
    const expectedPigletWeight = weightByDay[dayEnd] ?? null;

    rows.push({
      periodStart: prevDatetime,
      periodEnd: currDatetime,
      days,
      totalConsumed,
      liveAnimals,
      consumptionPerPig,
      dailyPerAnimal,
      plannedDailyPerAnimal,
      expectedPigletWeight,
    });
  }

  return rows;
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
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('pigs.period', 'Período')}</th>
                  <th>{t('pigs.daysLabel', 'Dias')}</th>
                  <th>{t('pigs.totalConsumed', 'Total Consumido (kg)')}</th>
                  <th>{t('pigs.liveAnimals', 'Animais Vivos')}</th>
                  <th>{t('pigs.consumptionPerPig', 'Consumo/Animal (kg)')}</th>
                  <th>{t('pigs.dailyPerAnimal', 'Diário/Animal (kg)')}</th>
                  <th>{t('pigs.plannedDailyPerAnimal', 'Planejado Diário/Animal (kg)')}</th>
                  <th>{t('pigs.expectedPigletWeight', 'Peso Esperado (kg)')}</th>
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
                      <td>{row.days}</td>
                      <td>{formatNumber(row.totalConsumed, 1)}</td>
                      <td>{row.liveAnimals}</td>
                      <td>{formatNumber(row.consumptionPerPig, 2)}</td>
                      <td style={{ color: deviationColor }}>
                        {formatNumber(row.dailyPerAnimal, 3)}
                      </td>
                      <td>
                        {row.plannedDailyPerAnimal != null ? formatNumber(row.plannedDailyPerAnimal, 3) : '—'}
                      </td>
                      <td>
                        {row.expectedPigletWeight != null ? formatNumber(row.expectedPigletWeight, 1) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
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
