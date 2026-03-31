import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import {
  getBatch,
  listFeedBalances,
  getFeedSchedule,
  listFeedTruckArrivals,
  getFeedConsumptionPlan,
  listMortalities,
  getModule,
} from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type {
  Batch,
  FeedBalance,
  FeedSchedule,
  FeedTruckArrival,
  FeedConsumptionPlanEntry,
  Mortality,
  Module,
} from '../../types/models';

interface ForecastRow {
  date: string;
  projectedBalance: number;
  overCapacity: boolean;
  belowThreshold: boolean;
}

function getCumulativeDeathsUpTo(mortalities: Mortality[], dateStr: string): number {
  let count = 0;
  for (const m of mortalities) {
    if (m.mortality_date <= dateStr) count++;
  }
  return count;
}

function computeForecast(
  batch: Batch,
  balances: FeedBalance[],
  schedule: FeedSchedule[],
  arrivals: FeedTruckArrival[],
  plan: FeedConsumptionPlanEntry[],
  mortalities: Mortality[],
  moduleData: Module,
): ForecastRow[] {
  const totalAnimals = batch.total_animal_count ?? 0;
  if (totalAnimals === 0 || balances.length === 0) return [];

  const totalSiloCapacity = moduleData.silo_capacity;
  const minThreshold = batch.min_feed_stock_threshold;

  // Latest balance
  const sortedBalances = [...balances].sort((a, b) => a.measurement_date.localeCompare(b.measurement_date));
  const latestBalance = sortedBalances[sortedBalances.length - 1];

  // Fulfilled schedule IDs (from arrivals that reference a schedule)
  const fulfilledScheduleIds = new Set<string>();
  for (const a of arrivals) {
    if (a.feed_schedule_id) fulfilledScheduleIds.add(a.feed_schedule_id);
  }
  // Also check fulfilled_by on schedule entries
  for (const s of schedule) {
    if (s.fulfilled_by) fulfilledScheduleIds.add(s.sk);
  }

  // Unfulfilled schedule entries as delivery map by date
  const deliveryByDate: Record<string, number> = {};
  for (const s of schedule) {
    if (!fulfilledScheduleIds.has(s.sk)) {
      deliveryByDate[s.planned_date] = (deliveryByDate[s.planned_date] || 0) + s.expected_amount_kg;
    }
  }

  // Plan lookup by day_number
  const planByDay: Record<number, number> = {};
  for (const p of plan) {
    planByDay[p.day_number] = p.expected_grams_per_animal;
  }

  const receiveDate = new Date(batch.receive_date + 'T00:00:00');
  const startDate = new Date(latestBalance.measurement_date + 'T00:00:00');
  let balance = latestBalance.balance_kg;

  // Forecast up to 60 days or end of 130-day plan
  const maxDays = 60;
  const rows: ForecastRow[] = [];

  for (let d = 0; d <= maxDays; d++) {
    const currentDate = new Date(startDate.getTime() + d * 86400000);
    const dateStr = currentDate.toISOString().substring(0, 10);

    if (d > 0) {
      // Add scheduled deliveries for this day
      balance += deliveryByDate[dateStr] || 0;

      // Subtract daily consumption
      const daysSinceReceive = Math.round((currentDate.getTime() - receiveDate.getTime()) / 86400000);
      const dayNumber = daysSinceReceive + 1;
      const gramsPerAnimal = planByDay[dayNumber] ?? 0;
      const deaths = getCumulativeDeathsUpTo(mortalities, dateStr);
      const liveAnimals = Math.max(1, totalAnimals - deaths);
      const dailyConsumptionKg = (gramsPerAnimal / 1000) * liveAnimals;
      balance -= dailyConsumptionKg;
    }

    rows.push({
      date: dateStr,
      projectedBalance: balance,
      overCapacity: totalSiloCapacity > 0 && balance > totalSiloCapacity,
      belowThreshold: balance < minThreshold,
    });
  }

  return rows;
}

export default function FeedBalanceForecastView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchBalances = useCallback(() => listFeedBalances(id), [id]);
  const fetchSchedule = useCallback(() => getFeedSchedule(id), [id]);
  const fetchArrivals = useCallback(() => listFeedTruckArrivals(id), [id]);
  const fetchPlan = useCallback(() => getFeedConsumptionPlan(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);

  const { data: batch, loading: l1, error: e1, refetch: r1 } = useApi(fetchBatch);

  const fetchModule = useCallback(
    () => (batch ? getModule(batch.module_id) : Promise.resolve({ pk: '', module_number: 0, name: '', area: 0, supported_animal_count: 0, silo_capacity: 0 } as Module)),
    [batch],
  );

  const { data: balances, loading: l2, error: e2, refetch: r2 } = useApi(fetchBalances);
  const { data: schedule, loading: l3, error: e3, refetch: r3 } = useApi(fetchSchedule);
  const { data: arrivals, loading: l4, error: e4, refetch: r4 } = useApi(fetchArrivals);
  const { data: plan, loading: l5, error: e5, refetch: r5 } = useApi(fetchPlan);
  const { data: mortalities, loading: l6, error: e6, refetch: r6 } = useApi(fetchMortalities);
  const { data: moduleData, loading: l7, error: e7, refetch: r7 } = useApi(fetchModule);

  const loading = l1 || l2 || l3 || l4 || l5 || l6 || l7;
  const error = e1 || e2 || e3 || e4 || e5 || e6 || e7;
  const refetchAll = () => { r1(); r2(); r3(); r4(); r5(); r6(); r7(); };

  const forecastRows = useMemo(
    () => (batch && balances && schedule && arrivals && plan && mortalities && moduleData
      ? computeForecast(batch, balances, schedule, arrivals, plan, mortalities, moduleData)
      : []),
    [batch, balances, schedule, arrivals, plan, mortalities, moduleData],
  );

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.feedForecast') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 style={titleStyle}>{t('pigs.feedForecast')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && (
        forecastRows.length === 0 ? (
          <div style={emptyStyle}>
            {t('pigs.noForecastData', 'São necessários dados de balanço de ração e resumo inicial para gerar a previsão.')}
          </div>
        ) : (
          <>
            <div style={legendBar}>
              <span style={legendItem}><span style={{ ...legendDot, backgroundColor: '#d32f2f' }} /> {t('pigs.overCapacity', 'Acima da capacidade do silo')}</span>
              <span style={legendItem}><span style={{ ...legendDot, backgroundColor: '#e65100' }} /> {t('pigs.belowThreshold', 'Abaixo do estoque mínimo')}</span>
            </div>
            <div style={tableWrapper}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>{t('pigs.date')}</th>
                    <th style={thStyle}>{t('pigs.projectedBalance', 'Saldo Projetado (kg)')}</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastRows.map((row) => {
                    let rowBg: string | undefined;
                    if (row.overCapacity) rowBg = '#ffebee';
                    else if (row.belowThreshold) rowBg = '#fff3e0';

                    return (
                      <tr key={row.date} style={rowBg ? { backgroundColor: rowBg } : undefined}>
                        <td style={tdStyle}>{formatDate(row.date)}</td>
                        <td style={{
                          ...tdStyle,
                          fontWeight: 600,
                          color: row.overCapacity ? '#d32f2f' : row.belowThreshold ? '#e65100' : undefined,
                        }}>
                          {formatNumber(row.projectedBalance, 1)}
                          {row.overCapacity && ' ⚠'}
                          {row.belowThreshold && ' ⚠'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
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
const legendBar: React.CSSProperties = { display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap', fontSize: '0.85rem' };
const legendItem: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '0.4rem' };
const legendDot: React.CSSProperties = { display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%' };
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
