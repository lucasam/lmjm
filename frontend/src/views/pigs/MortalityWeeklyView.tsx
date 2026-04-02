import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getBatch, listMortalities } from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type { Batch, Mortality } from '../../types/models';

interface WeekRow {
  week: number;
  startDate: Date;
  endDate: Date;
  deathCount: number;
  weeklyPct: number;
  cumulativePct: number;
}

function computeWeeklyData(batch: Batch, mortalities: Mortality[]): WeekRow[] {
  const totalAnimals = batch.total_animal_count ?? 0;
  if (totalAnimals === 0) return [];

  const receiveDate = new Date(batch.receive_date + 'T00:00:00');

  const weekDeaths: Record<number, number> = {};
  let maxWeek = 0;
  for (const m of mortalities) {
    const mDate = new Date(m.mortality_date + 'T00:00:00');
    const diffMs = mDate.getTime() - receiveDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays < 0) continue;
    const week = Math.floor(diffDays / 7) + 1;
    weekDeaths[week] = (weekDeaths[week] || 0) + 1;
    if (week > maxWeek) maxWeek = week;
  }

  const rows: WeekRow[] = [];
  let cumulativeDeaths = 0;
  const weeksToShow = Math.max(maxWeek, 1);

  for (let w = 1; w <= weeksToShow; w++) {
    const deaths = weekDeaths[w] || 0;
    cumulativeDeaths += deaths;
    const startDate = new Date(receiveDate.getTime() + (w - 1) * 7 * 86400000);
    const endDate = new Date(receiveDate.getTime() + w * 7 * 86400000 - 86400000);
    rows.push({
      week: w,
      startDate,
      endDate,
      deathCount: deaths,
      weeklyPct: (deaths / totalAnimals) * 100,
      cumulativePct: (cumulativeDeaths / totalAnimals) * 100,
    });
  }

  return rows;
}

export default function MortalityWeeklyView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);

  const { data: batch, loading: l1, error: e1, refetch: r1 } = useApi(fetchBatch);
  const { data: mortalities, loading: l2, error: e2, refetch: r2 } = useApi(fetchMortalities);

  const loading = l1 || l2;
  const error = e1 || e2;
  const refetchAll = () => { r1(); r2(); };

  const weeklyData = useMemo(
    () => (batch && mortalities ? computeWeeklyData(batch, mortalities) : []),
    [batch, mortalities],
  );

  const noStartSummary = batch != null && batch.total_animal_count == null;

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.mortalityWeekly') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.mortalityWeekly')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && noStartSummary && (
        <div className="alert alert-error" style={{ backgroundColor: '#fff3cd', borderColor: '#ffc107', color: '#856404' }}>
          {t('pigs.startSummaryRequired', 'O resumo inicial deve ser gerado antes de calcular a mortalidade semanal.')}
        </div>
      )}

      {!loading && !error && !noStartSummary && (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('pigs.weekNumber', 'Semana')}</th>
                <th>{t('pigs.dateRange', 'Período')}</th>
                <th>{t('pigs.deathCount', 'Mortes')}</th>
                <th>{t('pigs.weeklyPct', '% Semanal')}</th>
                <th>{t('pigs.cumulativePct', '% Acumulada')}</th>
              </tr>
            </thead>
            <tbody>
              {weeklyData.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">{t('common.noData')}</td>
                </tr>
              ) : (
                weeklyData.map((row) => (
                  <tr key={row.week}>
                    <td>{row.week}</td>
                    <td>{formatDate(row.startDate)} – {formatDate(row.endDate)}</td>
                    <td>{row.deathCount}</td>
                    <td>{formatNumber(row.weeklyPct, 2)}%</td>
                    <td>{formatNumber(row.cumulativePct, 2)}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
