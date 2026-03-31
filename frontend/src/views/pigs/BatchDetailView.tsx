import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
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
  const [triggeringStart, setTriggeringStart] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchSchedule = useCallback(() => getFeedSchedule(id), [id]);
  const fetchFeedTrucks = useCallback(() => listFeedTruckArrivals(id), [id]);
  const fetchPigTrucks = useCallback(() => listPigTruckArrivals(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);
  const fetchMedications = useCallback(() => listMedications(id), [id]);
  const fetchPlan = useCallback(() => getFeedConsumptionPlan(id), [id]);
  const fetchBalances = useCallback(() => listFeedBalances(id), [id]);

  const { data: batch, loading: l1, error: e1, refetch: rBatch } = useApi(fetchBatch);
  const { data: schedule, loading: l2, error: e2, refetch: rSchedule } = useApi(fetchSchedule);
  const { data: feedTrucks, loading: l3, error: e3, refetch: rFeedTrucks } = useApi(fetchFeedTrucks);
  const { data: pigTrucks, loading: l4, error: e4, refetch: rPigTrucks } = useApi(fetchPigTrucks);
  const { data: mortalities, loading: l5, error: e5, refetch: rMortalities } = useApi(fetchMortalities);
  const { data: medications, loading: l6, error: e6, refetch: rMedications } = useApi(fetchMedications);
  const { data: plan, loading: l7, error: e7, refetch: rPlan } = useApi(fetchPlan);
  const { data: balances, loading: l8, error: e8, refetch: rBalances } = useApi(fetchBalances);

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

  const scheduleCols: Column<FeedSchedule>[] = [
    { header: t('pigs.feedType'), accessor: (r) => r.feed_type },
    { header: t('pigs.plannedDate'), accessor: (r) => formatDate(r.planned_date) },
    { header: t('pigs.expectedAmountKg'), accessor: (r) => formatNumber(r.expected_amount_kg) },
    { header: t('pigs.status'), accessor: (r) => r.fulfilled_by ? '✓' : '—' },
  ];

  const feedTruckCols: Column<FeedTruckArrival>[] = [
    { header: t('pigs.receiveDate'), accessor: (r) => formatDate(r.receive_date) },
    { header: t('pigs.feedType'), accessor: (r) => r.feed_type },
    { header: t('pigs.actualAmountKg'), accessor: (r) => formatNumber(r.actual_amount_kg) },
    { header: t('pigs.fiscalDocumentNumber'), accessor: (r) => r.fiscal_document_number },
  ];

  const pigTruckCols: Column<PigTruckArrival>[] = [
    { header: t('pigs.arrivalDate'), accessor: (r) => formatDate(r.arrival_date) },
    { header: t('pigs.animalCount'), accessor: (r) => String(r.animal_count) },
    { header: t('cattle.sex'), accessor: (r) => r.sex === 'Male' ? t('pigs.male') : t('pigs.female') },
    { header: t('pigs.originName'), accessor: (r) => r.origin_name },
    { header: t('pigs.originType'), accessor: (r) => r.origin_type === 'UPL' ? t('pigs.upl') : t('pigs.creche') },
    { header: t('pigs.pigAgeDays'), accessor: (r) => String(r.pig_age_days) },
  ];

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
      <h1 style={titleStyle}>{t('pigs.batchDetail')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && batch && (
        <>
          {/* Batch attributes */}
          <div style={detailGrid}>
            <DetailRow label={t('pigs.status')} value={statusLabel(batch.status)} />
            <DetailRow label={t('pigs.supplyId')} value={String(batch.supply_id)} />
            <DetailRow label={t('pigs.receiveDate')} value={formatDate(batch.receive_date)} />
            <DetailRow label={t('pigs.expectedSlaughterDate')} value={batch.expected_slaughter_date ? formatDate(batch.expected_slaughter_date) : undefined} />
            <DetailRow label={t('pigs.minFeedStockThreshold')} value={formatNumber(batch.min_feed_stock_threshold)} />
          </div>

          {/* Start summary */}
          {batch.total_animal_count != null && (
            <>
              <h2 style={sectionTitle}>{t('pigs.startSummary')}</h2>
              <div style={detailGrid}>
                <DetailRow label={t('pigs.totalAnimalCount')} value={String(batch.total_animal_count)} />
                <DetailRow label={t('pigs.averageStartDate')} value={batch.average_start_date ? formatDate(batch.average_start_date) : undefined} />
                <DetailRow label={t('pigs.distinctOriginCount')} value={batch.distinct_origin_count != null ? String(batch.distinct_origin_count) : undefined} />
                <DetailRow label={t('pigs.originTypes')} value={batch.origin_types?.join(', ')} />
              </div>
            </>
          )}

          {/* Edit batch button */}
          <div style={actionBar}>
            <button type="button" style={actionBtn} onClick={() => setModal('editBatch')}>
              {t('common.edit')} {t('pigs.batchDetail')}
            </button>
          </div>

          {/* Trigger start summary button */}
          {batch.status === 'created' && (
            <div style={actionBar}>
              <button type="button" style={startBtn} onClick={handleTriggerStart} disabled={triggeringStart}>
                {triggeringStart ? t('common.loading') : t('pigs.triggerStartSummary')}
              </button>
              {startError && <span style={inlineError}>{startError}</span>}
            </div>
          )}

          {/* Action buttons */}
          <div style={actionBar}>
            <button type="button" style={actionBtn} onClick={() => setModal('feedTruck')}>{t('pigs.newFeedTruckArrival')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('feedSchedule')}>{t('pigs.feedSchedule')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('pigTruck')}>{t('pigs.newPigTruckArrival')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('mortality')}>{t('pigs.newMortality')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('medication')}>{t('pigs.newMedication')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('medicationShot')}>{t('pigs.newMedicationShot')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('feedPlan')}>{t('pigs.feedConsumptionPlan')}</button>
            <button type="button" style={actionBtn} onClick={() => setModal('feedBalance')}>{t('pigs.newFeedBalance')}</button>
          </div>

          {/* Analytical view links */}
          <div style={actionBar}>
            <button type="button" style={linkBtn} onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/medication-shots`)}>{t('pigs.medicationShots')}</button>
            <button type="button" style={linkBtn} onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/mortality-weekly`)}>{t('pigs.mortalityWeekly')}</button>
            <button type="button" style={linkBtn} onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/feed-consumption`)}>{t('pigs.feedConsumption')}</button>
            <button type="button" style={linkBtn} onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}/feed-forecast`)}>{t('pigs.feedForecast')}</button>
          </div>

          {/* Feed schedule */}
          <h2 style={sectionTitle}>{t('pigs.feedSchedule')}</h2>
          <DataTable columns={scheduleCols} data={schedule ?? []} keyExtractor={(r) => r.sk} />

          {/* Feed truck arrivals */}
          <h2 style={sectionTitle}>{t('pigs.feedTruckArrivals')}</h2>
          <DataTable columns={feedTruckCols} data={feedTrucks ?? []} keyExtractor={(r) => r.sk} />

          {/* Pig truck arrivals */}
          <h2 style={sectionTitle}>{t('pigs.pigTruckArrivals')}</h2>
          <DataTable columns={pigTruckCols} data={pigTrucks ?? []} keyExtractor={(r) => r.sk} />

          {/* Mortalities */}
          <h2 style={sectionTitle}>{t('pigs.mortalities')}</h2>
          <DataTable columns={mortalityCols} data={mortalities ?? []} keyExtractor={(r) => r.sk} />

          {/* Medications */}
          <h2 style={sectionTitle}>{t('pigs.medications')}</h2>
          <DataTable columns={medicationCols} data={medications ?? []} keyExtractor={(r) => r.sk} />

          {/* Feed balances */}
          <h2 style={sectionTitle}>{t('pigs.feedBalance')}</h2>
          <DataTable columns={feedBalanceCols} data={balances ?? []} keyExtractor={(r) => r.sk} />
        </>
      )}

      {/* Modals */}
      {modal === 'feedTruck' && (
        <FeedTruckArrivalForm batchId={id} feedSchedule={schedule ?? []} onClose={() => setModal(null)} onSuccess={closeAndRefresh(() => { rFeedTrucks(); rSchedule(); })} />
      )}
      {modal === 'feedSchedule' && (
        <FeedScheduleForm batchId={id} existing={schedule ?? []} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rSchedule)} />
      )}
      {modal === 'pigTruck' && (
        <PigTruckArrivalForm batchId={id} onClose={() => setModal(null)} onSuccess={closeAndRefresh(rPigTrucks)} />
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
    <div style={detailRow}>
      <span style={detailLabel}>{label}</span>
      <span style={detailValue}>{value ?? '—'}</span>
    </div>
  );
}

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const detailGrid: React.CSSProperties = { marginBottom: '1.5rem' };
const detailRow: React.CSSProperties = { display: 'flex', padding: '0.4rem 0', borderBottom: '1px solid #eee', gap: '0.5rem' };
const detailLabel: React.CSSProperties = { fontWeight: 600, minWidth: '180px', color: '#555' };
const detailValue: React.CSSProperties = { color: '#222' };
const sectionTitle: React.CSSProperties = { fontSize: '1.1rem', fontWeight: 600, margin: '1.5rem 0 0.75rem' };
const actionBar: React.CSSProperties = { display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' };
const actionBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
const startBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#2e7d32', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
const linkBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#e3f2fd', color: '#1976d2', border: '1px solid #1976d2', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
const inlineError: React.CSSProperties = { color: '#721c24', fontSize: '0.85rem', alignSelf: 'center' };


function BatchEditForm({ batchId, initial, onClose, onSuccess }: {
  batchId: string;
  initial: { status: string; supply_id: number; module_id: string; receive_date: string; expected_slaughter_date?: string; min_feed_stock_threshold: number };
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useTranslation();
  const [status, setStatus] = useState(initial.status);
  const [supplyId, setSupplyId] = useState(String(initial.supply_id));
  const [moduleId, setModuleId] = useState(initial.module_id);
  const [receiveDate, setReceiveDate] = useState(initial.receive_date);
  const [expectedSlaughterDate, setExpectedSlaughterDate] = useState(initial.expected_slaughter_date ?? '');
  const [minFeedStockThreshold, setMinFeedStockThreshold] = useState(String(initial.min_feed_stock_threshold));
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
        module_id: moduleId,
        receive_date: receiveDate.replace(/-/g, ''),
        ...(expectedSlaughterDate ? { expected_slaughter_date: expectedSlaughterDate.replace(/-/g, '') } : {}),
        min_feed_stock_threshold: Number(minFeedStockThreshold),
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
    <div style={editOverlay} onClick={onClose} role="presentation">
      <div style={editModal} onClick={(e) => e.stopPropagation()}>
        <h2 style={editTitle}>{t('pigs.editBatch', 'Editar Lote')}</h2>
        {success && <div style={editSuccess}>✓ {t('common.save')}</div>}
        {formError && <div style={editError}>{formError}</div>}
        <form onSubmit={handleSubmit}>
          <label style={editLabel}>
            {t('pigs.status')}
            <select value={status} onChange={(e) => setStatus(e.target.value)} style={editInput}>
              <option value="created">{t('pigs.statusCreated')}</option>
              <option value="in_progress">{t('pigs.statusInProgress')}</option>
              <option value="delivered">{t('pigs.statusDelivered')}</option>
            </select>
          </label>
          <label style={editLabel}>
            {t('pigs.supplyId')}
            <input type="number" min="0" step="1" value={supplyId} onChange={(e) => setSupplyId(e.target.value)} style={editInput} />
          </label>
          <label style={editLabel}>
            {t('pigs.modules')}
            <input type="text" value={moduleId} onChange={(e) => setModuleId(e.target.value)} style={editInput} />
          </label>
          <label style={editLabel}>
            {t('pigs.receiveDate')}
            <input type="date" value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} style={editInput} />
          </label>
          <label style={editLabel}>
            {t('pigs.expectedSlaughterDate')}
            <input type="date" value={expectedSlaughterDate} onChange={(e) => setExpectedSlaughterDate(e.target.value)} style={editInput} />
          </label>
          <label style={editLabel}>
            {t('pigs.minFeedStockThreshold')}
            <input type="number" min="0" step="1" value={minFeedStockThreshold} onChange={(e) => setMinFeedStockThreshold(e.target.value)} style={editInput} />
          </label>
          <div style={editBtnRow}>
            <button type="button" style={editCancelBtn} onClick={onClose}>{t('common.cancel')}</button>
            <button type="submit" style={editSubmitBtn} disabled={submitting}>
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const editOverlay: React.CSSProperties = {
  position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 500, padding: '1rem',
};
const editModal: React.CSSProperties = {
  backgroundColor: '#fff', borderRadius: '8px', padding: '1.5rem',
  width: '100%', maxWidth: '480px', maxHeight: '90vh', overflowY: 'auto',
};
const editTitle: React.CSSProperties = { fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem' };
const editLabel: React.CSSProperties = { display: 'block', marginBottom: '1rem', fontSize: '0.9rem', fontWeight: 500, color: '#333' };
const editInput: React.CSSProperties = {
  display: 'block', width: '100%', padding: '10px', marginTop: '0.25rem',
  border: '1px solid #ccc', borderRadius: '4px', fontSize: '1rem', boxSizing: 'border-box', minHeight: '44px',
};
const editBtnRow: React.CSSProperties = { display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' };
const editCancelBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#eee', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem',
};
const editSubmitBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
const editSuccess: React.CSSProperties = { padding: '0.75rem', marginBottom: '0.75rem', backgroundColor: '#e8f5e9', borderRadius: '4px', color: '#2e7d32' };
const editError: React.CSSProperties = { padding: '0.75rem', marginBottom: '0.75rem', backgroundColor: '#fdecea', borderRadius: '4px', color: '#721c24' };
