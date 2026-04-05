import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postFeedTruckArrival } from '../../api/client';
import { getFeedTypeDescription } from '../../constants/feedTypes';
import type { FeedSchedule, FeedScheduleFiscalDocument, RawMaterialType } from '../../types/models';

interface FeedTruckArrivalFormProps {
  batchId: string;
  feedSchedule: FeedSchedule[];
  pendingFiscalDocs?: FeedScheduleFiscalDocument[];
  rawMaterialTypes?: RawMaterialType[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function FeedTruckArrivalForm({ batchId, feedSchedule, pendingFiscalDocs, rawMaterialTypes, onClose, onSuccess }: FeedTruckArrivalFormProps) {
  const { t } = useTranslation();
  const [receiveDate, setReceiveDate] = useState('');
  const [fiscalDocumentNumber, setFiscalDocumentNumber] = useState('');
  const [actualAmountKg, setActualAmountKg] = useState('');
  const [feedType, setFeedType] = useState('');
  const [feedScheduleId, setFeedScheduleId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const pendingSchedule = feedSchedule.filter((s) => !s.fulfilled_by);
  const pendingDocs = (pendingFiscalDocs ?? []).filter((d) => d.status === 'pending');

  const handleFiscalDocSelect = (fiscalDocNumber: string) => {
    if (!fiscalDocNumber) return;
    const doc = pendingDocs.find((d) => d.fiscal_document_number === fiscalDocNumber);
    if (!doc) return;

    // Convert issue_date YYYY-MM-DD to YYYY-MM-DD (already correct format for date input)
    setReceiveDate(doc.issue_date);
    setFiscalDocumentNumber(doc.fiscal_document_number);
    setActualAmountKg(String(doc.actual_amount_kg));

    // Map product_code to feed type code via RawMaterialType
    setFeedType(doc.product_code);

    // Pre-fill feed_schedule_id if present
    if (doc.feed_schedule_id) {
      setFeedScheduleId(doc.feed_schedule_id);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postFeedTruckArrival(batchId, {
        receive_date: receiveDate.replace(/-/g, ''),
        fiscal_document_number: fiscalDocumentNumber,
        actual_amount_kg: Number(actualAmountKg),
        feed_type: feedType,
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

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('pigs.newFeedTruckArrival')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        {pendingDocs.length > 0 && (
          <label className="form-label">
            Preencher com NF-e
            <select
              onChange={(e) => handleFiscalDocSelect(e.target.value)}
              className="form-input"
              defaultValue=""
            >
              <option value="">—</option>
              {pendingDocs.map((d) => {
                const rmt = (rawMaterialTypes ?? []).find((r) => r.code === d.product_code);
                const feedDesc = rmt ? rmt.description : d.product_code;
                return (
                  <option key={d.fiscal_document_number} value={d.fiscal_document_number}>
                    NF {d.fiscal_document_number} — {feedDesc} — {d.actual_amount_kg} kg ({d.issue_date})
                  </option>
                );
              })}
            </select>
          </label>
        )}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.receiveDate')} *
            <input type="date" required value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.fiscalDocumentNumber')} *
            <input type="text" required value={fiscalDocumentNumber} onChange={(e) => setFiscalDocumentNumber(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.actualAmountKg')} *
            <input type="number" required min="0" step="any" value={actualAmountKg} onChange={(e) => setActualAmountKg(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.feedType')} *
            <select required value={feedType} onChange={(e) => setFeedType(e.target.value)} className="form-input">
              <option value="">—</option>
              {(rawMaterialTypes ?? []).filter((r) => r.category === 'feed').map((r) => (
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
                  <option key={s.sk} value={s.sk}>{getFeedTypeDescription(s.feed_type)} — {s.planned_date} ({s.expected_amount_kg} kg)</option>
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
