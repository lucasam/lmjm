import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listCattleAnimals } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import type { CattleAnimal } from '../../types/models';

export default function AnimalListView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const fetchAnimals = useCallback(() => listCattleAnimals(), []);
  const { data: animals, loading, error, refetch } = useApi(fetchAnimals);

  const columns: Column<CattleAnimal>[] = [
    { header: t('cattle.earTag'), accessor: (r) => r.ear_tag },
    { header: t('cattle.breed'), accessor: (r) => r.breed ?? '—' },
    { header: t('cattle.sex'), accessor: (r) => r.sex ?? '—' },
    { header: t('cattle.batch'), accessor: (r) => r.batch ?? '—' },
    { header: t('cattle.status'), accessor: (r) => r.status ?? '—' },
    {
      header: t('cattle.pregnant'),
      accessor: (r) =>
        r.pregnant == null ? '—' : r.pregnant ? t('common.yes') : t('common.no'),
    },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle') },
  ];

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">{t('cattle.animalList')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}
      {!loading && !error && animals && (
        <DataTable
          columns={columns}
          data={animals}
          keyExtractor={(r) => r.ear_tag}
          onRowClick={(r) => navigate(`/cattle/${encodeURIComponent(r.ear_tag)}`)}
        />
      )}
    </Layout>
  );
}
