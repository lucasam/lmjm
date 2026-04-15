import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getFeedConsumptionPlan } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import type { FeedConsumptionPlanEntry } from '../../types/models';

export default function ReadOnlyFeedConsumptionPlanView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { batchId } = useParams<{ batchId: string }>();
  const { user, logout } = useAuth();

  const fetchData = useCallback(() => getFeedConsumptionPlan(batchId!), [batchId]);
  const { data, loading, error, refetch } = useApi(fetchData);

  const columns: Column<FeedConsumptionPlanEntry>[] = [
    { header: t('feedConsumptionPlan.dayNumber', 'Dia'), accessor: (r) => r.day_number },
    { header: t('feedConsumptionPlan.date', 'Data'), accessor: (r) => r.date },
    { header: t('feedConsumptionPlan.expectedKgPerAnimal', 'Kg/Animal Esperado'), accessor: (r) => r.expected_kg_per_animal },
    { header: t('feedConsumptionPlan.expectedPigletWeight', 'Peso Esperado (g)'), accessor: (r) => r.expected_piglet_weight },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('feedConsumptionPlan.batchDetail', 'Batch Detail'), to: `/pigs/batches/${batchId}` },
    { label: t('feedConsumptionPlan.title', 'Feed Consumption Plan') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <div className="action-bar" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('feedConsumptionPlan.title', 'Feed Consumption Plan')}</h1>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        <DataTable
          columns={columns}
          data={data ?? []}
          keyExtractor={(r) => String(r.day_number)}
        />
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${batchId}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
