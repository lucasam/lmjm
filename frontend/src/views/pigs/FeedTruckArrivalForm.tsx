import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { postFeedTruckArrival } from '../../api/client';
import type { FeedSchedule, FeedScheduleFiscalDocument, RawMaterialType } from '../../types/models';
import { datetimeLocalToApi, currentDatetimeLocal } from '../../utils/datetimeConvert';

interface FeedTruckArrivalFormProps {
  batchId: string;
  feedSchedule: FeedSchedule[];
  pendingFiscalDocs?: FeedScheduleFiscalDocument[];
  rawMaterialTypes?: RawMaterialType[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function FeedTruckArrivalForm({
  batchId,
  feedSchedule,
  pendingFiscalDocs,
  rawMaterialTypes,
  onClose,
  onSuccess,
}: FeedTruckArrivalFormProps) {
  const { t } = useTranslation();
  const [receiveDate, setReceiveDate] = useState(currentDatetimeLocal());
  const [fiscalDocumentNumber, setFiscalDocumentNumber] = useState('');
  const [actualAmountKg, setActualAmountKg] = useState('');
  const [feedType, setFeedType] = useState('');
  const [feedDescription, setFeedDescription] = useState('');
  const [feedScheduleId, setFeedScheduleId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const feedRawMaterials = useMemo(
    () => (rawMaterialTypes ?? []).filter((r) => r.category === 'feed'),
    [rawMaterialTypes],
  );

  const pendingSchedule = feedSchedule
    .filter((s) => !s.fulfilled_by)
    .sort((a, b) => a.planned_date.localeCompare(b.planned_date));
  const pendingDocs = (pendingFiscalDocs ?? []).filter((d) => d.status === 'pending');

  const selectRawMaterial = (code: string) => {
    setFeedType(code);
    const rmt = feedRawMaterials.find((r) => r.code === code);
    setFeedDescription(rmt ? rmt.description : '');
  };

  const handleFiscalDocSelect = (docSk: string) => {
    if (!docSk) return;
    const doc = pendingDocs.find((d) => d.sk === docSk);
    if (!doc) return;
    setReceiveDate(`${doc.issue_date}T00:00`);
    setFiscalDocumentNumber(doc.fiscal_document_number);
    setActualAmountKg(String(doc.actual_amount_kg));
    selectRawMaterial(doc.product_code);
    setFeedScheduleId(doc.feed_schedule_id ?? '');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postFeedTruckArrival(batchId, {
        receive_date: datetimeLocalToApi(receiveDate),
        fiscal_document_number: fiscalDocumentNumber,
        actual_amount_kg: Number(actualAmountKg),
        feed_type: feedType,
        feed_description: feedDescription,
        ...(feedScheduleId ? { feed_schedule_id: feedScheduleId } : {}),
      });
      setSuccess(true);
      setTimeout(onSuccess, 800);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const scheduleLabel = (s: FeedSchedule) => {
    const desc = s.feed_description || feedRawMaterials.find((r) => r.code === s.feed_type)?.description || s.feed_type;
    return `${desc} — ${s.planned_date} (${s.expected_amount_kg} kg)`;
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('pigs.newFeedTruckArrival')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        {pendingDocs.length > 0 && (
          <label className="form-label">
            Preencher com NF-e
            <select onChange={(e) => handleFiscalDocSelect(e.target.value)} className="form-input" defaultValue="">
              <option value="">—</option>
              {pendingDocs.map((d) => {
                const rmt = feedRawMaterials.find((r) => r.code === d.product_code);
                const desc = rmt ? rmt.description : d.product_code;
                return (
                  <option key={d.sk} value={d.sk}>
                    NF {d.fiscal_document_number} — {desc} — {d.actual_amount_kg} kg ({d.issue_date})
                  </option>
                );
              })}
            </select>
          </label>
        )}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.receiveDateTime')} *
            <input type="datetime-local" required value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.fiscalDocumentNumber')} *
            <input type="text" required value={fiscalDocumentNumber} onChange={(e) => setFiscalDocumentNumber(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.actualAmountKg')} *
            <input type="number" required min="0" step="1" value={actualAmountKg} onChange={(e) => setActualAmountKg(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.feedType')} *
            <select required value={feedType} onChange={(e) => selectRawMaterial(e.target.value)} className="form-input">
              <option value="">—</option>
              {feedRawMaterials.map((r) => (
                <option key={r.code} value={r.code}>{r.description} ({r.code})</option>
              ))}
            </select>
          </label>

          {pendingSchedule.length > 0 && (
            <label className="form-label">
              {t('pigs.feedSchedule')}
              <select value={feedScheduleId} onChange={(e) => setFeedScheduleId(e.target.value)} className="form-input">
                <option value="">—</option>
                {pendingSchedule.map((s) => (
                  <option key={s.sk} value={s.sk}>{scheduleLabel(s)}</option>
                ))}
              </select>
            </label>
          )}

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
