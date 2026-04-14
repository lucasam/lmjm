import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listModules, listBatches } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import BatchForm from './BatchForm';
import type { Module, Batch } from '../../types/models';

export default function PigDashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showBatchForm, setShowBatchForm] = useState(false);

  const fetchModules = useCallback(() => listModules(), []);
  const fetchBatches = useCallback(() => listBatches(), []);

  const { data: modules, loading: loadingModules, error: errorModules, refetch: refetchModules } = useApi(fetchModules);
  const { data: batches, loading: loadingBatches, error: errorBatches, refetch: refetchBatches } = useApi(fetchBatches);

  const loading = loadingModules || loadingBatches;
  const error = errorModules || errorBatches;

  const moduleCols: Column<Module>[] = [
    { header: t('pigs.moduleNumber'), accessor: (r) => String(r.module_number) },
    { header: t('pigs.moduleName'), accessor: (r) => r.name },
  ];

  const statusLabel = (status: Batch['status']) => {
    const map: Record<string, string> = {
      created: t('pigs.statusCreated'),
      in_progress: t('pigs.statusInProgress'),
      delivered: t('pigs.statusDelivered'),
    };
    return map[status] ?? status;
  };

  // Build module_id → name lookup from already-fetched modules
  const moduleNameMap = new Map<string, string>();
  (modules ?? []).forEach((m) => moduleNameMap.set(m.pk, m.name));

  const batchCols: Column<Batch>[] = [
    { header: t('pigs.moduleName'), accessor: (r) => moduleNameMap.get(r.module_id) ?? r.module_id },
    { header: t('pigs.status'), accessor: (r) => statusLabel(r.status) },
    { header: t('pigs.supplyId'), accessor: (r) => String(r.supply_id) },
    { header: t('pigs.totalAnimalCount'), accessor: (r) => r.total_animal_count != null ? String(r.total_animal_count) : '—' },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs') },
  ];

  const handleBatchSuccess = () => {
    setShowBatchForm(false);
    refetchBatches();
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">{t('pigs.dashboard')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={() => { refetchModules(); refetchBatches(); }} />}

      {!loading && !error && (
        <>
          {/* Module summary */}
          <h2 className="section-title">{t('pigs.modules')}</h2>
          <DataTable
            columns={moduleCols}
            data={modules ?? []}
            keyExtractor={(r) => r.pk}
            onRowClick={(r) => navigate(`/pigs/modules/${encodeURIComponent(r.pk)}`)}
          />

          {/* Active batches */}
          <div className="action-bar" style={{ justifyContent: 'space-between' }}>
            <h2 className="section-title" style={{ margin: 0, border: 'none', paddingBottom: 0 }}>{t('pigs.batches')}</h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn-outline" onClick={() => navigate('/pigs/integrator-weekly-data')}>
                {t('pigs.integratorWeeklyData', 'Dados Semanais Integradora')}
              </button>
              <button type="button" className="btn btn-outline" onClick={() => navigate('/pigs/fiscal-documents')}>
                {t('pigs.fiscalDocuments', 'Notas Fiscais')}
              </button>
              <button type="button" className="btn btn-outline" onClick={() => navigate('/pigs/raw-material-types')}>
                {t('pigs.rawMaterialTypes', 'Tipos de Matéria Prima')}
              </button>
              <button type="button" className="btn btn-primary" onClick={() => setShowBatchForm(true)}>
                {t('pigs.newBatch')}
              </button>
            </div>
          </div>
          <DataTable
            columns={batchCols}
            data={batches ?? []}
            keyExtractor={(r) => r.pk}
            onRowClick={(r) => navigate(`/pigs/batches/${encodeURIComponent(r.pk)}`)}
          />
        </>
      )}

      {showBatchForm && (
        <BatchForm
          onClose={() => setShowBatchForm(false)}
          onSuccess={handleBatchSuccess}
        />
      )}
    </Layout>
  );
}
