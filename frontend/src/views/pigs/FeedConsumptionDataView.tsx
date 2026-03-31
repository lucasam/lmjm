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
}

function getCumulativeDeathsUpTo(mortalities: Mortality[], dateStr: string): number {
  let count = 0;
  for (const m of mortalities) {
    if (m.mortality_date <= dateStr) count++;
  }
  return count;
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
  const receiveDate = batch.receive_date;

  // Build plan lookup by day_number
  const planByDay: Record<number, number> = {};
  for (const p of plan) {
    planByDay[p.day_number] = p.expected_grams_per_animal;
  }

  const rows: ConsumptionRow[] = [];

  for (let i = 1; i < sortedBalances.length; i++) {
    const prev = sortedBalances[i - 1];
    const curr = sortedBalances[i];

    const prevDate = prev.measurement_date;
    const currDate = curr.measurement_date;

    // Feed delivered in this period
    let deliveredInPeriod = 0;
    for (const a of arrivals) {
      if (a.receive_date > prevDate && a.receive_date <= currDate) {
        deliveredInPeriod += a.actual_amount_kg;
      }
    }

    // Total consumed = prev_balance + deliveries - curr_balance
    const totalConsumed = prev.balance_kg + deliveredInPeriod - curr.balance_kg;

    // Days in period
    const d1 = new Date(prevDate + 'T00:00:00');
    const d2 = new Date(currDate + 'T00:00:00');
    const days = Math.max(1, Math.round((d2.getTime() - d1.getTime()) / 86400000));

    // Live animals at end of period
    const deaths = getCumulativeDeathsUpTo(mortalities, currDate);
    const liveAnimals = Math.max(1, totalAnimals - deaths);

    const consumptionPerPig = totalConsumed / liveAnimals;
    const dailyPerAnimal = totalConsumed / (liveAnimals * days);

    // Average planned daily per animal for this period
    const recDate = new Date(receiveDate + 'T00:00:00');
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

    rows.push({
      periodStart: prevDate,
      periodEnd: currDate,
      days,
      totalConsumed,
      liveAnimals,
      consumptionPerPig,
      dailyPerAnimal,
      plannedDailyPerAnimal,
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
      <h1 style={titleStyle}>{t('pigs.feedConsumption')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && (
        rows.length === 0 ? (
          <div style={emptyStyle}>
            {t('pigs.noConsumptionData', 'São necessárias pelo menos duas medições de balanço de ração para calcular o consumo.')}
          </div>
        ) : (
          <div style={tableWrapper}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>{t('pigs.period', 'Período')}</th>
                  <th style={thStyle}>{t('pigs.daysLabel', 'Dias')}</th>
                  <th style={thStyle}>{t('pigs.totalConsumed', 'Total Consumido (kg)')}</th>
                  <th style={thStyle}>{t('pigs.liveAnimals', 'Animais Vivos')}</th>
                  <th style={thStyle}>{t('pigs.consumptionPerPig', 'Consumo/Animal (kg)')}</th>
                  <th style={thStyle}>{t('pigs.dailyPerAnimal', 'Diário/Animal (g)')}</th>
                  <th style={thStyle}>{t('pigs.plannedDailyPerAnimal', 'Planejado Diário/Animal (g)')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const deviation = row.plannedDailyPerAnimal != null
                    ? row.dailyPerAnimal * 1000 - row.plannedDailyPerAnimal
                    : null;
                  const deviationColor = deviation != null
                    ? (Math.abs(deviation) > row.plannedDailyPerAnimal! * 0.1 ? '#e65100' : undefined)
                    : undefined;

                  return (
                    <tr key={i}>
                      <td style={tdStyle}>{formatDate(row.periodStart)} – {formatDate(row.periodEnd)}</td>
                      <td style={tdStyle}>{row.days}</td>
                      <td style={tdStyle}>{formatNumber(row.totalConsumed, 1)}</td>
                      <td style={tdStyle}>{row.liveAnimals}</td>
                      <td style={tdStyle}>{formatNumber(row.consumptionPerPig, 2)}</td>
                      <td style={{ ...tdStyle, color: deviationColor }}>
                        {formatNumber(row.dailyPerAnimal * 1000, 1)}
                      </td>
                      <td style={tdStyle}>
                        {row.plannedDailyPerAnimal != null ? formatNumber(row.plannedDailyPerAnimal, 1) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}

      <div style={backBar}>
        <button type="button" style={backBtn} onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const tableWrapper: React.CSSProperties = { overflowX: 'auto', WebkitOverflowScrolling: 'touch', width: '100%' };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' };
const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '0.75rem 0.5rem', borderBottom: '2px solid #ddd',
  whiteSpace: 'nowrap', fontWeight: 600, backgroundColor: '#f5f5f5',
};
const tdStyle: React.CSSProperties = { padding: '0.75rem 0.5rem', borderBottom: '1px solid #eee', whiteSpace: 'nowrap' };
const emptyStyle: React.CSSProperties = { padding: '2rem', textAlign: 'center', color: '#888' };
const backBar: React.CSSProperties = { marginTop: '1.5rem' };
const backBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#e3f2fd', color: '#1976d2', border: '1px solid #1976d2', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
