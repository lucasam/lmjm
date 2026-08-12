import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getFeedTypeDescription } from '../../constants/feedTypes';
import {
  listFeedTruckArrivals,
  getFeedSchedule,
  listRawMaterialTypes,
  deleteFeedTruckArrival,
} from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import FeedTruckArrivalForm from './FeedTruckArrivalForm';
import type { FeedTruckArrival } from '../../types/models';

interface FeedTypeSummary {
  feedType: string;
  feedDescription: string;
  total: number;
  minDate: string;
  maxDate: string;
  count: number;
}

// Numeric sort by fiscal document number, tolerant of non-numeric values.
function byFiscalAsc(a: FeedTruckArrival, b: FeedTruckArrival): number {
  const na = Number(a.fiscal_document_number);
  const nb = Number(b.fiscal_document_number);
  if (Number.isFinite(na) && Number.isFinite(nb) && na !== nb) return na - nb;
  return a.fiscal_document_number.localeCompare(b.fiscal_document_number);
}

export default function FeedTruckArrivalView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const id = batchId ?? '';

  const [editArrival, setEditArrival] = useState<FeedTruckArrival | null>(null);

  const fetchArrivals = useCallback(() => listFeedTruckArrivals(id), [id]);
  const fetchSchedule = useCallback(() => getFeedSchedule(id), [id]);
  const fetchRawMaterialTypes = useCallback(() => listRawMaterialTypes(), []);

  const { data: arrivals, loading, error, refetch } = useApi(fetchArrivals);
  const { data: schedule } = useApi(fetchSchedule);
  const { data: rawMaterialTypes } = useApi(fetchRawMaterialTypes);

  // Full table sorted by fiscal document ascending, with a running cumulative.
  const sortedAsc = useMemo(() => {
    const data = [...(arrivals ?? [])].sort(byFiscalAsc);
    let cumulative = 0;
    return data.map((r) => {
      cumulative += r.actual_amount_kg;
      return { ...r, cumulativeAmountKg: cumulative };
    });
  }, [arrivals]);

  // Summary per feed type: total received, min/max receive date.
  const summary = useMemo<FeedTypeSummary[]>(() => {
    const map = new Map<string, FeedTypeSummary>();
    for (const r of arrivals ?? []) {
      const existing = map.get(r.feed_type);
      if (!existing) {
        map.set(r.feed_type, {
          feedType: r.feed_type,
          feedDescription: r.feed_description || getFeedTypeDescription(r.feed_type),
          total: r.actual_amount_kg,
          minDate: r.receive_date,
          maxDate: r.receive_date,
          count: 1,
        });
      } else {
        existing.total += r.actual_amount_kg;
        existing.count += 1;
        if (r.receive_date < existing.minDate) existing.minDate = r.receive_date;
        if (r.receive_date > existing.maxDate) existing.maxDate = r.receive_date;
      }
    }
    return Array.from(map.values()).sort((a, b) => a.feedType.localeCompare(b.feedType));
  }, [arrivals]);

  const handleDelete = async (r: FeedTruckArrival) => {
    if (!window.confirm(t('pigs.confirmDeleteFeedTruck', 'Excluir este recebimento de ração?'))) return;
    await deleteFeedTruckArrival(id, r.sk);
    refetch();
  };

  const cols: Column<FeedTruckArrival & { cumulativeAmountKg: number }>[] = [
    { header: t('pigs.receiveDate'), accessor: (r) => formatDate(r.receive_date) },
    { header: t('pigs.fiscalDocumentNumber'), accessor: (r) => r.fiscal_document_number },
    {
      header: t('pigs.feedType'),
      accessor: (r) => `${r.feed_type} — ${r.feed_description || getFeedTypeDescription(r.feed_type)}`,
    },
    { header: t('pigs.actualAmountKg'), accessor: (r) => formatNumber(r.actual_amount_kg) },
    { header: 'Acumulado (kg)', accessor: (r) => formatNumber(r.cumulativeAmountKg) },
    {
      header: t('pigs.scheduledDate', 'Agendamento'),
      accessor: (r) => {
        if (!r.feed_schedule_id) return '—';
        const matched = (schedule ?? []).find((s) => s.sk === r.feed_schedule_id);
        return matched ? formatDate(matched.planned_date) : '—';
      },
    },
    {
      header: '',
      accessor: (r) => (
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={() => setEditArrival(r)}
        >
          {t('common.edit')}
        </button>
      ),
    },
    {
      header: '',
      accessor: (r) => (
        <button
          type="button"
          className="btn btn-outline btn-sm"
          style={{ color: 'var(--error)', borderColor: 'var(--error)' }}
          onClick={() => handleDelete(r)}
        >
          {t('common.delete', 'Excluir')}
        </button>
      ),
    },
  ];

  const summaryCols: Column<FeedTypeSummary>[] = [
    { header: t('pigs.feedType'), accessor: (r) => `${r.feedType} — ${r.feedDescription}` },
    { header: t('pigs.actualAmountKg'), accessor: (r) => formatNumber(r.total) },
    { header: t('pigs.minReceiveDate', 'Primeiro Recebimento'), accessor: (r) => formatDate(r.minDate) },
    { header: t('pigs.maxReceiveDate', 'Último Recebimento'), accessor: (r) => formatDate(r.maxDate) },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs', 'Suínos'), to: '/pigs' },
    { label: t('pigs.batch', 'Lote'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.feedTruckArrivals') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.feedTruckArrivals')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        <>
          <DataTable columns={cols} data={sortedAsc} keyExtractor={(r) => r.sk} />

          <h2 className="section-title">{t('pigs.feedTruckSummary', 'Resumo por Tipo de Ração')}</h2>
          <DataTable columns={summaryCols} data={summary} keyExtractor={(r) => r.feedType} />

          <div style={{ marginTop: 'var(--space-md)' }}>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}
            >
              ← {t('pigs.batch', 'Lote')}
            </button>
          </div>
        </>
      )}

      {editArrival && (
        <FeedTruckArrivalForm
          batchId={id}
          feedSchedule={schedule ?? []}
          rawMaterialTypes={rawMaterialTypes ?? []}
          initial={editArrival}
          onClose={() => setEditArrival(null)}
          onSuccess={() => {
            setEditArrival(null);
            refetch();
          }}
        />
      )}
    </Layout>
  );
}
