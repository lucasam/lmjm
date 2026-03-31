import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getModule } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import WarehouseForm from './WarehouseForm';
import type { Warehouse } from '../../types/models';

export default function ModuleDetailView() {
  const { t } = useTranslation();
  const { moduleId } = useParams<{ moduleId: string }>();
  const { user, logout } = useAuth();
  const [showWarehouseForm, setShowWarehouseForm] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | null>(null);

  const id = moduleId ?? '';
  const fetchModule = useCallback(() => getModule(id), [id]);
  const { data: mod, loading, error, refetch } = useApi(fetchModule);

  const warehouseCols: Column<Warehouse>[] = [
    { header: t('pigs.warehouseName'), accessor: (r) => r.name },
    { header: t('pigs.area'), accessor: (r) => String(r.area) },
    { header: t('pigs.supportedAnimalCount'), accessor: (r) => String(r.supported_animal_count) },
    { header: t('pigs.siloCapacity'), accessor: (r) => String(r.silo_capacity) },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: mod ? `${t('pigs.moduleNumber')} ${mod.module_number}` : id },
  ];

  const handleWarehouseSuccess = () => {
    setShowWarehouseForm(false);
    setEditingWarehouse(null);
    refetch();
  };

  const handleRowClick = (w: Warehouse) => {
    setEditingWarehouse(w);
    setShowWarehouseForm(true);
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && mod && (
        <>
          <h1 style={titleStyle}>{mod.name}</h1>
          <div style={detailGrid}>
            <DetailRow label={t('pigs.moduleNumber')} value={String(mod.module_number)} />
            <DetailRow label={t('pigs.moduleName')} value={mod.name} />
          </div>

          <div style={actionBar}>
            <h2 style={sectionTitle}>{t('pigs.warehouses')}</h2>
            <button type="button" style={actionBtn} onClick={() => { setEditingWarehouse(null); setShowWarehouseForm(true); }}>
              {t('pigs.newWarehouse')}
            </button>
          </div>

          <DataTable
            columns={warehouseCols}
            data={mod.warehouses}
            keyExtractor={(r) => r.sk}
            onRowClick={handleRowClick}
          />
        </>
      )}

      {showWarehouseForm && (
        <WarehouseForm
          moduleId={id}
          warehouse={editingWarehouse}
          onClose={() => { setShowWarehouseForm(false); setEditingWarehouse(null); }}
          onSuccess={handleWarehouseSuccess}
        />
      )}
    </Layout>
  );
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div style={detailRow}>
      <span style={detailLabel}>{label}</span>
      <span style={detailValue}>{value ?? '—'}</span>
    </div>
  );
}

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const detailGrid: React.CSSProperties = { marginBottom: '1.5rem' };
const detailRow: React.CSSProperties = { display: 'flex', padding: '0.4rem 0', borderBottom: '1px solid #eee', gap: '0.5rem' };
const detailLabel: React.CSSProperties = { fontWeight: 600, minWidth: '140px', color: '#555' };
const detailValue: React.CSSProperties = { color: '#222' };
const sectionTitle: React.CSSProperties = { fontSize: '1.1rem', fontWeight: 600, margin: '1.5rem 0 0.75rem' };
const actionBar: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' };
const actionBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
