import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getFeedTypeDescription } from '../../constants/feedTypes';
import {
  getBatch,
  listFeedBalances,
  getFeedSchedule,
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
  FeedConsumptionPlanEntry,
  Mortality,
  Module,
} from '../../types/models';

interface ForecastRow {
  date: string;
  estimatedConsumption: number;
  estimatedFeedTruckArrival: number;
  estimatedFeedTruckDescription: string;
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
  plan: FeedConsumptionPlanEntry[],
  mortalities: Mortality[],
  moduleData: Module,
  includeBalanceDayDelivery: boolean,
): ForecastRow[] {
  const totalAnimals = batch.total_animal_count ?? 0;
  if (totalAnimals === 0 || balances.length === 0) return [];

  const totalSiloCapacity = moduleData.silo_capacity;
  const minThreshold = batch.min_feed_stock_threshold;

  const sortedBalances = [...balances].sort((a, b) => a.measurement_date.localeCompare(b.measurement_date));
  const latestBalance = sortedBalances[sortedBalances.length - 1];

  // Change 1: Include scheduled and delivered schedules (exclude only canceled)
  const deliveryByDate: Record<string, number> = {};
  const deliveryDescByDate: Record<string, string[]> = {};
  for (const s of schedule) {
    if (s.status === 'scheduled' || s.status === 'delivered') {
      deliveryByDate[s.planned_date] = (deliveryByDate[s.planned_date] || 0) + s.expected_amount_kg;
      if (!deliveryDescByDate[s.planned_date]) deliveryDescByDate[s.planned_date] = [];
      deliveryDescByDate[s.planned_date].push(s.feed_description || getFeedTypeDescription(s.feed_type));
    }
  }

  const planByDay: Record<number, number> = {};
  for (const p of plan) {
    planByDay[p.day_number] = p.expected_kg_per_animal;
  }

  const receiveDate = new Date((batch.average_start_date ?? '').substring(0, 10) + 'T00:00:00');
  const startDate = new Date(latestBalance.measurement_date.substring(0, 10) + 'T00:00:00');
  let balance = latestBalance.balance_kg;

  const maxDays = 60;
  const rows: ForecastRow[] = [];

  for (let d = 0; d <= maxDays; d++) {
    const currentDate = new Date(startDate.getTime() + d * 86400000);
    const dateStr = currentDate.toISOString().substring(0, 10);

    let estimatedConsumption = 0;
    const estimatedFeedTruckArrival = deliveryByDate[dateStr] || 0;
    const estimatedFeedTruckDescription = (deliveryDescByDate[dateStr] || []).join(', ');

    if (d === 0) {
      // Change 2: optionally include delivery on the balance measurement day
      if (includeBalanceDayDelivery && estimatedFeedTruckArrival > 0) {
        balance += estimatedFeedTruckArrival;
      }
    } else {
      balance += estimatedFeedTruckArrival;

      const daysSinceReceive = Math.round((currentDate.getTime() - receiveDate.getTime()) / 86400000);
      const dayNumber = daysSinceReceive + 1;
      const kgPerAnimal = planByDay[dayNumber] ?? 0;
      const deaths = getCumulativeDeathsUpTo(mortalities, dateStr);
      const liveAnimals = Math.max(1, totalAnimals - deaths);
      estimatedConsumption = kgPerAnimal * liveAnimals;
      balance -= estimatedConsumption;
    }

    rows.push({
      date: dateStr,
      estimatedConsumption,
      estimatedFeedTruckArrival,
      estimatedFeedTruckDescription,
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
  const fetchPlan = useCallback(() => getFeedConsumptionPlan(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);

  const { data: batch, loading: l1, error: e1, refetch: r1 } = useApi(fetchBatch);

  const fetchModule = useCallback(
    () => (batch ? getModule(batch.module_id) : Promise.resolve({ pk: '', module_number: 0, name: '', area: 0, supported_animal_count: 0, silo_capacity: 0 } as Module)),
    [batch],
  );

  const { data: balances, loading: l2, error: e2, refetch: r2 } = useApi(fetchBalances);
  const { data: schedule, loading: l3, error: e3, refetch: r3 } = useApi(fetchSchedule);
  const { data: plan, loading: l4, error: e4, refetch: r4 } = useApi(fetchPlan);
  const { data: mortalities, loading: l5, error: e5, refetch: r5 } = useApi(fetchMortalities);
  const { data: moduleData, loading: l6, error: e6, refetch: r6 } = useApi(fetchModule);

  const loading = l1 || l2 || l3 || l4 || l5 || l6;
  const error = e1 || e2 || e3 || e4 || e5 || e6;
  const refetchAll = () => { r1(); r2(); r3(); r4(); r5(); r6(); };

  const [includeBalanceDayDelivery, setIncludeBalanceDayDelivery] = useState(false);

  const forecastRows = useMemo(
    () => (batch && balances && schedule && plan && mortalities && moduleData
      ? computeForecast(batch, balances, schedule, plan, mortalities, moduleData, includeBalanceDayDelivery)
      : []),
    [batch, balances, schedule, plan, mortalities, moduleData, includeBalanceDayDelivery],
  );

  const PT_WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
  const formatDateWithWeekday = (dateStr: string): string => {
    const d = new Date(dateStr + 'T00:00:00');
    return `${formatDate(dateStr)} (${PT_WEEKDAYS[d.getDay()]})`;
  };
  const todayStr = new Date().toISOString().substring(0, 10);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.feedForecast') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.feedForecast')}</h1>

      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: '0.5rem 0 1rem' }}>
        <input
          type="checkbox"
          checked={includeBalanceDayDelivery}
          onChange={(e) => setIncludeBalanceDayDelivery(e.target.checked)}
        />
        {t('pigs.includeBalanceDayDelivery', 'Incluir entrega do dia do balanço')}
      </label>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && (
        forecastRows.length === 0 ? (
          <div className="table-empty">
            {t('pigs.noForecastData', 'São necessários dados de balanço de ração e resumo inicial para gerar a previsão.')}
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: 'var(--error)' }} />
                {t('pigs.overCapacity', 'Acima da capacidade do silo')}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: 'var(--accent)' }} />
                {t('pigs.belowThreshold', 'Abaixo do estoque mínimo')}
              </span>
            </div>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('pigs.date')}</th>
                    <th>{t('pigs.estimatedConsumption', 'Consumo Estimado (kg)')}</th>
                    <th>{t('pigs.estimatedFeedTruckArrival', 'Entrega Prevista (kg)')}</th>
                    <th>{t('pigs.projectedBalance', 'Saldo Projetado (kg)')}</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastRows.map((row) => {
                    const isToday = row.date === todayStr;
                    let rowBg: string | undefined;
                    if (isToday) rowBg = '#e3f2fd';
                    else if (row.overCapacity) rowBg = '#ffebee';
                    else if (row.belowThreshold) rowBg = '#fff3e0';

                    return (
                      <tr key={row.date} style={rowBg ? { backgroundColor: rowBg } : undefined}>
                        <td style={isToday ? { fontWeight: 700 } : undefined}>{formatDateWithWeekday(row.date)}</td>
                        <td>{row.estimatedConsumption > 0 ? formatNumber(row.estimatedConsumption, 1) : '—'}</td>
                        <td>{row.estimatedFeedTruckArrival > 0 ? `${formatNumber(row.estimatedFeedTruckArrival, 1)} — ${row.estimatedFeedTruckDescription}` : '—'}</td>
                        <td style={{
                          fontWeight: 600,
                          color: row.overCapacity ? 'var(--error)' : row.belowThreshold ? 'var(--accent)' : undefined,
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

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
