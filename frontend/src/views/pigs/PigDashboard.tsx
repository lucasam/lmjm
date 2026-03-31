import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listModules, listBatches } from '../../api/client';
import { formatDate } from '../../i18n';
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

  const batchCols: Column<Batch>[] = [
    { header: t('pigs.status'), accessor: (r) => statusLabel(r.status) },
    { header: t('pigs.supplyId'), accessor: (r) => String(r.supply_id) },
    { header: t('pigs.totalAnimalCount'), accessor: (r) => r.total_animal_count != null ? String(r.total_animal_count) : '—' },
    { header: t('pigs.receiveDate'), accessor: (r) => formatDate(r.receive_date) },
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
      <h1 style={titleStyle}>{t('pigs.dashboard')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={() => { refetchModules(); refetchBatches(); }} />}

      {!loading && !error && (
        <>
          {/* Module summary */}
          <h2 style={sectionTitle}>{t('pigs.modules')}</h2>
          <DataTable
            columns={moduleCols}
            data={modules ?? []}
            keyExtractor={(r) => r.pk}
            onRowClick={(r) => navigate(`/pigs/modules/${encodeURIComponent(r.pk)}`)}
          />

          {/* Active batches */}
          <div style={actionBar}>
            <h2 style={sectionTitle}>{t('pigs.batches')}</h2>
            <button type="button" style={actionBtn} onClick={() => setShowBatchForm(true)}>
              {t('pigs.newBatch')}
            </button>
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

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const sectionTitle: React.CSSProperties = { fontSize: '1.1rem', fontWeight: 600, margin: '1.5rem 0 0.75rem' };
const actionBar: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' };
const actionBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
