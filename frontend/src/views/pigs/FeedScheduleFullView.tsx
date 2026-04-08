import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getFeedTypeDescription } from '../../constants/feedTypes';
import { getFeedSchedule } from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import FeedScheduleForm from './FeedScheduleForm';
import type { FeedSchedule } from '../../types/models';

const PT_WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

function formatDateWithWeekday(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const weekday = PT_WEEKDAYS[d.getDay()];
  return `${formatDate(dateStr)} (${weekday})`;
}

export default function FeedScheduleFullView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showEdit, setShowEdit] = useState(false);

  const id = batchId ?? '';
  const fetchSchedule = useCallback(() => getFeedSchedule(id), [id]);
  const { data: schedule, loading, error, refetch } = useApi(fetchSchedule);

  const [statusFilter, setStatusFilter] = useState<string>('all');

  const translateStatus = (s: string): string => {
    const map: Record<string, string> = {
      scheduled: t('pigs.feedScheduleStatusScheduled', 'Agendado'),
      delivered: t('pigs.feedScheduleStatusDelivered', 'Entregue'),
      canceled: t('pigs.feedScheduleStatusCanceled', 'Cancelado'),
    };
    return map[s] ?? s;
  };

  const sortedSchedule = useMemo(() => {
    const all = schedule ?? [];
    const sorted = [...all].sort((a, b) => a.planned_date.localeCompare(b.planned_date));
    if (statusFilter === 'all') return sorted;
    return sorted.filter((s) => s.status === statusFilter);
  }, [schedule, statusFilter]);

  const cols: Column<FeedSchedule>[] = [
    { header: t('pigs.plannedDate'), accessor: (r) => formatDateWithWeekday(r.planned_date) },
    { header: t('pigs.feedType'), accessor: (r) => getFeedTypeDescription(r.feed_type) },
    { header: t('pigs.expectedAmountKg'), accessor: (r) => formatNumber(r.expected_amount_kg) },
    { header: t('pigs.status'), accessor: (r) => translateStatus(r.status ?? 'scheduled') },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.feedSchedule') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.feedSchedule')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        <>
          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem', alignItems: 'center' }}>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="filter-select">
              <option value="all">{t('common.all', 'Todos')}</option>
              <option value="scheduled">{t('pigs.feedScheduleStatusScheduled', 'Agendado')}</option>
              <option value="delivered">{t('pigs.feedScheduleStatusDelivered', 'Entregue')}</option>
              <option value="canceled">{t('pigs.feedScheduleStatusCanceled', 'Cancelado')}</option>
            </select>
            <button type="button" className="btn btn-secondary" onClick={() => setShowEdit(true)}>
              {t('common.edit')}
            </button>
          </div>

          <DataTable columns={cols} data={sortedSchedule} keyExtractor={(r) => r.sk} />
        </>
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>

      {showEdit && (
        <FeedScheduleForm
          batchId={id}
          existing={schedule ?? []}
          onClose={() => setShowEdit(false)}
          onSuccess={() => { setShowEdit(false); refetch(); }}
        />
      )}
    </Layout>
  );
}
