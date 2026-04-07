import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getFeedTypeDescription } from '../../constants/feedTypes';
import {
  getBatch,
  getFeedSchedule,
  listFeedTruckArrivals,
  listPigTruckArrivals,
  listMortalities,
  listMedications,
  createBatchStartSummary,
  getFeedConsumptionPlan,
  listFeedBalances,
  updateBatch,
  listFeedScheduleFiscalDocuments,
  listRawMaterialTypes,
} from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import FeedTruckArrivalForm from './FeedTruckArrivalForm';
import FeedScheduleForm from './FeedScheduleForm';
import PigTruckArrivalForm from './PigTruckArrivalForm';
import MortalityForm from './MortalityForm';
import MedicationForm from './MedicationForm';
import MedicationShotForm from './MedicationShotForm';
import FeedConsumptionPlanForm from './FeedConsumptionPlanForm';
import FeedBalanceForm from './FeedBalanceForm';
import type {
  FeedSchedule,
  FeedTruckArrival,
  PigTruckArrival,
  Mortality,
  Medication,
  FeedBalance,
} from '../../types/models';

type ModalType =
  | 'feedTruck'
  | 'feedSchedule'
  | 'pigTruck'
  | 'editPigTruck'
  | 'mortality'
  | 'medication'
  | 'medicationShot'
  | 'feedPlan'
  | 'feedBalance'
  | 'editBatch'
  | null;

export default function BatchDetailView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [modal, setModal] = useState<ModalType>(null);
  const [editPigTruckArrival, setEditPigTruckArrival] = useState<PigTruckArrival | null>(null);
  const [triggeringStart, setTriggeringStart] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [scheduleFilter, setScheduleFilter] = useState<string>('all');

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchSchedule = useCallback(() => getFeedSchedule(id), [id]);
  const fetchFeedTrucks = useCallback(() => listFeedTruckArrivals(id), [id]);
  const fetchPigTrucks = useCallback(() => listPigTruckArrivals(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);
  const fetchMedications = useCallback(() => listMedications(id), [id]);
  const fetchPlan = useCallback(() => getFeedConsumptionPlan(id), [id]);
  const fetchBalances = useCallback(() => listFeedBalances(id), [id]);
  const fetchFiscalDocs = useCallback(() => listFeedScheduleFiscalDocuments(id), [id]);
  const fetchRawMaterialTypes = useCallback(() => listRawMaterialTypes(), []);

  const { data: batch, loading: l1, error: e1, refetch: rBatch } = useApi(fetchBatch);
  const { data: schedule, loading: l2, error: e2, refetch: rSchedule } = useApi(fetchSchedule);
  const { data: feedTrucks, loading: l3, error: e3, refetch: rFeedTrucks } = useApi(fetchFeedTrucks);
  const { data: pigTrucks, loading: l4, error: e4, refetch: rPigTrucks } = useApi(fetchPigTrucks);
  const { data: mortalities, loading: l5, error: e5, refetch: rMortalities } = useApi(fetchMortalities);
  const { data: medications, loading: l6, error: e6, refetch: rMedications } = useApi(fetchMedications);
  const { data: plan, loading: l7, error: e7, refetch: rPlan } = useApi(fetchPlan);
  const { data: balances, loading: l8, error: e8, refetch: rBalances } = useApi(fetchBalances);
  const { data: fiscalDocs, refetch: rFiscalDocs } = useApi(fetchFiscalDocs);
  const { data: rawMaterialTypes } = useApi(fetchRawMaterialTypes);

  const loading = l1 || l2 || l3 || l4 || l5 || l6 || l7 || l8;
  const error = e1 || e2 || e3 || e4 || e5 || e6 || e7 || e8;

  const refetchAll = () => {
    rBatch(); rSchedule(); rFeedTrucks(); rPigTrucks();
    rMortalities(); rMedications(); rPlan(); rBalances();
  };

  const handleTriggerStart = async () => {
    setTriggeringStart(true);
    setStartError(null);
    try {
      await createBatchStartSummary(id);
      rBatch();
      rPigTrucks();
    } catch (err) {
      setStartError(err instanceof Error ? err.message : String(err));
    } finally {
      setTriggeringStart(false);
    }
  };

  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      created: t('pigs.statusCreated'),
      in_progress: t('pigs.statusInProgress'),
      delivered: t('pigs.statusDelivered'),
    };
    return map[status] ?? status;
  };

  const translateScheduleStatus = (s: string): string => {
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
    if (scheduleFilter === 'all') return sorted;
    return sorted.filter((s) => s.status === scheduleFilter);
  }, [schedule, scheduleFilter]);

  const scheduleCols: Column<FeedSchedule>[] = [
    { header: t('pigs.feedType'), accessor: (r) => getFeedTypeDescription(r.feed_type) },
    { header: t('pigs.plannedDate'), accessor: (r) => formatDate(r.planned_date) },
    { header: t('pigs.expectedAmountKg'), accessor: (r) => formatNumber(r.expected_amount_kg) },
    { header: t('pigs.status'), accessor: (r) => translateScheduleStatus(r.status ?? 'scheduled') },
  ];

  const feedTruckCols: Column<FeedTruckArrival>[] = [
    { header: t('pigs.receiveDate'), accessor: (r) => formatDate(r.receive_date) },
    { header: t('pigs.feedType'), accessor: (r) => getFeedTypeDescription(r.feed_type) },
    { header: t('pigs.actualAmountKg'), accessor: (r) => formatNumber(r.actual_amount_kg) },
    { header: t('pigs.fiscalDocumentNumber'), accessor: (r) => r.fiscal_document_number },
  ];

  const pigTruckCols: Column<PigTruckArrival>[] = [
    { header: t('pigs.arrivalDate'), accessor: (r) => formatDate(r.arrival_date) },
    { header: t('pigs.animalCount'), accessor: (r) => String(r.animal_count) },
    { header: t('pigs.animalWeight'), accessor: (r) => r.animal_weight ? formatNumber(r.animal_weight, 2) : '—' },
    { header: t('cattle.sex'), accessor: (r) => r.sex === 'Male' ? t('pigs.male') : t('pigs.female') },
    { header: t('pigs.originName'), accessor: (r) => r.origin_name },
    { header: t('pigs.originType'), accessor: (r) => r.origin_type === 'UPL' ? t('pigs.upl') : t('pigs.creche') },
    { header: t('pigs.pigAgeDays'), accessor: (r) => String(r.pig_age_days) },
    { header: '', accessor: (r) => (
      <button type="button" className="btn btn-outline btn-sm" onClick={() => { setEditPigTruckArrival(r); setModal('editPigTruck'); }}>
        {t('common.edit')}
      </button>
    )},
  ];

  const pigTruckSummary = useMemo(() => {
    const data = pigTrucks ?? [];
    if (data.length === 0) return null;
    const totalAnimals = data.reduce((sum, a) => sum + a.animal_count, 0);
    const totalWeight = data.reduce((sum, a) => sum + (a.animal_weight ?? 0) * a.animal_count, 0);
    const weightedAvg = totalAnimals > 0 ? totalWeight / totalAnimals : 0;
    return { totalAnimals, weightedAvg };
  }, [pigTrucks]);

  const mortalityCols: Column<Mortality>[] = [
    { header: t('pigs.mortalityDate'), accessor: (r) => formatDate(r.mortality_date) },
    { header: t('cattle.sex'), accessor: (r) => r.sex === 'Male' ? t('pigs.male') : t('pigs.female') },
    { header: t('pigs.origin'), accessor: (r) => r.origin },
    { header: t('pigs.deathReason'), accessor: (r) => r.death_reason },
    { header: t('pigs.reportedBy'), accessor: (r) => r.reported_by },
  ];

  const medicationCols: Column<Medication>[] = [
    { header: t('pigs.medicationName'), accessor: (r) => r.medication_name },
    { header: t('pigs.expirationDate'), accessor: (r) => formatDate(r.expiration_date) },
    { header: t('pigs.partNumber'), accessor: (r) => r.part_number },
  ];

  const feedBalanceCols: Column<FeedBalance>[] = [
    { header: t('pigs.measurementDate'), accessor: (r) => formatDate(r.measurement_date) },
    { header: t('pigs.balanceKg'), accessor: (r) => formatNumber(r.balance_kg) },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail') },
  ];

  const closeAndRefresh = (refetchFn: () => void) => () => {
    setModal(null);
    refetchFn();
  };

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      {/* Header with title + low-usage config icons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <h1 className="page-title" style={{ margin: 0, flex: 1 }}>{t('pigs.batchDetail')}</h1>
        <button type="button" className="btn btn-outline" style={{ padding: '0.4rem 0.6rem', fontSize: '0.85rem' }} onClick={() => setModal('editBatch')} title={t('common.edit')}>✏️</button>
        {batch && batch.status === 'created' && (
          <button type="button" className="btn btn-outline" style={{ padding: '0.4rem 0.6rem', fontSize: '0.85rem' }} onClick={handleTriggerStart} disabled={triggeringStart} title={t('pigs.triggerStartSummary')}>🚀</button>
        )}
        {startError && <span className="inline-error">{startError}</span>}
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && batch && (
        <>
          {/* Batch attributes */}
          <div className="detail-grid">
            <DetailRow label={t('pigs.status')} value={statusLabel(batch.status)} />
            <DetailRow label={t('pigs.supplyId')} value={String(batch.supply_id)} />
            <DetailRow label={t('pigs.receiveDate')} value={formatDate(batch.receive_date)} />
            <DetailRow label={t('pigs.expectedSlaughterDate')} value={batch.expected_slaughter_date ? formatDate(batch.expected_slaughter_date) : undefined} />
            <DetailRow label={t('pigs.minFeedStockThreshold')} value={formatNumber(batch.min_feed_stock_threshold)} />
          </div>

          {/* Start summary */}
          {batch.total_animal_count != null && (
            <>
              <h2 className="section-title">{t('pigs.startSummary')}</h2>
              <div className="detail-grid">
                <DetailRow label={t('pigs.totalAnimalCount')} value={String(batch.total_animal_count)} />
                <DetailRow label={t('pigs.averageStartDate')} value={batch.average_start_date ? formatDate(batch.average_start_date) : undefined} />
                <DetailRow label={t('pigs.distinctOriginCount')} value={batch.distinct_origin_count != null ? String(batch.distinct_origin_count) : undefined} />
                <DetailRow label={t('pigs.originTypes')} value={batch.origin_types?.join(', ')} />
                <DetailRow label={t('pigs.initialAnimalWeight')} value={batch.initial_animal_weight != null ? formatNumber(batch.initial_animal_weight, 2) : undefined} />
              </div>
            </>
          )}

          {/* High-usage daily actions */}
          <h2 className="section-title">{t('pigs.quickActions', 'Ações Rápidas')}</h2>
          <div className="action-bar">
            <button type="button" className="btn btn-primary" onClick={() => setModal('mortality')}>{t('pigs.newMortality')}</button>
            <button type="button" className="btn btn-primary" onClick={() => setModal('feedTruck')}>{t('pigs.newFeedTruckArrival')}</button>
            <button type="button" className="btn btn-primary" onClick={() => setModal('medicationShot')}>{t('pigs.newMedicationShot')}</button>
            <button type="button" className="btn btn-primary" onClick={() => setModal('feedBalance')}>{t('pigs.newFeedBalance')}</button>
          </div>

          {/* Analytical view links */}
          <div className="action-bar">
            <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/medication-shots`)}>{t('pigs.medicationShots')}</button>
            <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/mortality-weekly`)}>{t('pigs.mortalityWeekly')}</button>
            <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/feed-consumption`)}>{t('pigs.feedConsumption')}</button>
            <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/feed-forecast`)}>{t('pigs.feedForecast')}</button>
          </div>

          {/* Feed schedule */}
          <h2 className="section-title">{t('pigs.feedSchedule')}</h2>
          <div style={{ marginBottom: '0.75rem' }}>
            <select value={scheduleFilter} onChange={(e) => setScheduleFilter(e.target.value)} className="filter-select">
              <option value="all">{t('common.all', 'Todos')}</option>
              <option value="scheduled">{t('pigs.feedScheduleStatusScheduled', 'Agendado')}</option>
              <option value="delivered">{t('pigs.feedScheduleStatusDelivered', 'Entregue')}</option>
              <option value="canceled">{t('pigs.feedScheduleStatusCanceled', 'Cancelado')}</option>
            </select>
          </div>
          <DataTable columns={scheduleCols} data={sortedSchedule} keyExtractor={(r) => r.sk} />

          {/* Feed truck arrivals */}
          <h2 className="section-title">{t('pigs.feedTruckArrivals')}</h2>
          <DataTable columns={feedTruckCols} data={feedTrucks ?? []} keyExtractor={(r) => r.sk} />

          {/* Pig truck arrivals */}
          <h2 className="section-title">{t('pigs.pigTruckArrivals')}</h2>
          <DataTable columns={pigTruckCols} data={pigTrucks ?? []} keyExtractor={(r) => r.sk} />
          {pigTruckSummary && (
            <div className="detail-grid" style={{ marginTop: '0.5rem' }}>
              <DetailRow label={t('pigs.totalAnimalCount')} value={String(pigTruckSummary.totalAnimals)} />
              <DetailRow label={t('pigs.animalWeight')} value={formatNumber(pigTruckSummary.weightedAvg, 2)} />
            </div>
          )}

          {/* Mortalities */}
          <h2 className="section-title">{t('pigs.mortalities')}</h2>
          <DataTable columns={mortalityCols} data={mortalities ?? []} keyExtractor={(r) => r.sk} />

          {/* Medications */}
          <h2 className="section-title">{t('pigs.medications')}</h2>
          <DataTable columns={medicationCols} data={medications ?? []} keyExtractor={(r) => r.sk} />

          {/* Feed balances */}
          <h2 className="section-title">{t('pigs.feedBalance')}</h2>
          <DataTable columns={feedBalanceCols} data={balances ?? []} keyExtractor={(r) => r.sk} />

          {/* Batch configuration actions (low frequency) */}
          <h2 className="section-title">{t('pigs.batchConfig', 'Configuração do Lote')}</h2>
          <div className="action-bar">
            <button type="button" className="btn btn-secondary" onClick={() => setModal('pigTruck')}>{t('pigs.newPigTruckArrival')}</button>
            <button type="button" className="btn btn-secondary" onClick={() => setModal('medication')}>{t('pigs.newMedication')}</button>
            <button type="button" className="btn btn-secondary" onClick={() => setModal('feedPlan')}>{t('pigs.feedConsumptionPlan')}</button>
            <button type="button" className="btn btn-secondary" onClick={() => setModal('feedSchedule')}>{t('pigs.feedSchedule')}</button>
          </div>
        </>
      )}

      {/* Modals */}
      {modal === 'feedTruck' && (
        <FeedTruckArrivalForm batchId={id} feedSchedule={schedule ?? []} pendingFiscalDocs={fiscalDocs ?? []} rawMaterialTypes={rawMaterialTypes ?? []} onClose={() => setModal(null)} onSuccess={closeAndRefresh(() => { rFeedTrucks(); rSchedule(); rFiscalDocs(); })} />
      )}
      {modal === 'feedSchedule' && (
        <FeedScheduleForm batchId={id} existing={schedule ?? []} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rSchedule)} />
      )}
      {modal === 'pigTruck' && (
        <PigTruckArrivalForm batchId={id} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rPigTrucks)} />
      )}
      {modal === 'editPigTruck' && editPigTruckArrival && (
        <PigTruckArrivalForm batchId={id} initial={editPigTruckArrival} onClose={() => { setModal(null); setEditPigTruckArrival(null); }} onSuccess={() => { setModal(null); setEditPigTruckArrival(null); rPigTrucks(); }} />
      )}
      {modal === 'mortality' && (
        <MortalityForm batchId={id} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rMortalities)} />
      )}
      {modal === 'medication' && (
        <MedicationForm batchId={id} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rMedications)} />
      )}
      {modal === 'medicationShot' && (
        <MedicationShotForm batchId={id} medications={medications ?? []} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rMedications)} />
      )}
      {modal === 'feedPlan' && (
        <FeedConsumptionPlanForm batchId={id} receiveDate={batch?.receive_date ?? ''} existing={plan ?? []} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rPlan)} />
      )}
      {modal === 'feedBalance' && (
        <FeedBalanceForm batchId={id} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rBalances)} />
      )}
      {modal === 'editBatch' && batch && (
        <BatchEditForm
          batchId={id}
          initial={batch}
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); rBatch(); }}
        />
      )}
    </Layout>
  );
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="detail-row">
      <span className="detail-label" style={{ minWidth: '180px' }}>{label}</span>
      <span className="detail-value">{value ?? '—'}</span>
    </div>
  );
}


function BatchEditForm({ batchId, initial, onClose, onSuccess }: {
  batchId: string;
  initial: { status: string; supply_id: number; receive_date: string; expected_slaughter_date?: string; min_feed_stock_threshold: number; total_animal_count?: number; average_start_date?: string; distinct_origin_count?: number; origin_types?: string[] };
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useTranslation();
  const [status, setStatus] = useState(initial.status);
  const [supplyId, setSupplyId] = useState(String(initial.supply_id));
  const [receiveDate, setReceiveDate] = useState(initial.receive_date);
  const [expectedSlaughterDate, setExpectedSlaughterDate] = useState(initial.expected_slaughter_date ?? '');
  const [minFeedStockThreshold, setMinFeedStockThreshold] = useState(String(initial.min_feed_stock_threshold));
  const [totalAnimalCount, setTotalAnimalCount] = useState(initial.total_animal_count != null ? String(initial.total_animal_count) : '');
  const [averageStartDate, setAverageStartDate] = useState(initial.average_start_date ?? '');
  const [distinctOriginCount, setDistinctOriginCount] = useState(initial.distinct_origin_count != null ? String(initial.distinct_origin_count) : '');
  const [originTypes, setOriginTypes] = useState(initial.origin_types?.join(', ') ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await updateBatch(batchId, {
        status,
        supply_id: Number(supplyId),
        receive_date: receiveDate.replace(/-/g, ''),
        ...(expectedSlaughterDate ? { expected_slaughter_date: expectedSlaughterDate.replace(/-/g, '') } : {}),
        min_feed_stock_threshold: Number(minFeedStockThreshold),
        ...(totalAnimalCount ? { total_animal_count: Number(totalAnimalCount) } : {}),
        ...(averageStartDate ? { average_start_date: averageStartDate.replace(/-/g, '') } : {}),
        ...(distinctOriginCount ? { distinct_origin_count: Number(distinctOriginCount) } : {}),
        ...(originTypes.trim() ? { origin_types: originTypes.split(',').map((s) => s.trim()).filter(Boolean) } : {}),
      });
      setSuccess(true);
      setTimeout(onSuccess, 600);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('pigs.editBatch', 'Editar Lote')}</h2>
        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {formError && <div className="alert alert-error">{formError}</div>}
        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.status')}
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="form-input">
              <option value="created">{t('pigs.statusCreated')}</option>
              <option value="in_progress">{t('pigs.statusInProgress')}</option>
              <option value="delivered">{t('pigs.statusDelivered')}</option>
            </select>
          </label>
          <label className="form-label">
            {t('pigs.supplyId')}
            <input type="number" min="0" step="1" value={supplyId} onChange={(e) => setSupplyId(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.receiveDate')}
            <input type="date" value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.expectedSlaughterDate')}
            <input type="date" value={expectedSlaughterDate} onChange={(e) => setExpectedSlaughterDate(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.minFeedStockThreshold')}
            <input type="number" min="0" step="1" value={minFeedStockThreshold} onChange={(e) => setMinFeedStockThreshold(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.totalAnimalCount')}
            <input type="number" min="0" step="1" value={totalAnimalCount} onChange={(e) => setTotalAnimalCount(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.averageStartDate')}
            <input type="date" value={averageStartDate} onChange={(e) => setAverageStartDate(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.distinctOriginCount')}
            <input type="number" min="0" step="1" value={distinctOriginCount} onChange={(e) => setDistinctOriginCount(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.originTypes')}
            <input type="text" value={originTypes} onChange={(e) => setOriginTypes(e.target.value)} className="form-input" placeholder="UPL, Creche" />
          </label>
          <div className="modal-btn-row">
            <button type="button" className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
