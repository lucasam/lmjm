import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getModule } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';

export default function ModuleDetailView() {
  const { t } = useTranslation();
  const { moduleId } = useParams<{ moduleId: string }>();
  const { user, logout } = useAuth();

  const id = moduleId ?? '';
  const fetchModule = useCallback(() => getModule(id), [id]);
  const { data: mod, loading, error, refetch } = useApi(fetchModule);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: mod ? `${t('pigs.moduleNumber')} ${mod.module_number}` : id },
  ];

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
            <DetailRow label={t('pigs.area')} value={String(mod.area)} />
            <DetailRow label={t('pigs.supportedAnimalCount')} value={String(mod.supported_animal_count)} />
            <DetailRow label={t('pigs.siloCapacity')} value={String(mod.silo_capacity)} />
          </div>
        </>
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
