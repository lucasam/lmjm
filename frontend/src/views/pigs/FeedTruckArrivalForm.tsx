import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postFeedTruckArrival } from '../../api/client';
import type { FeedSchedule } from '../../types/models';

interface FeedTruckArrivalFormProps {
  batchId: string;
  feedSchedule: FeedSchedule[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function FeedTruckArrivalForm({ batchId, feedSchedule, onClose, onSuccess }: FeedTruckArrivalFormProps) {
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
    <div style={overlayStyle} onClick={onClose} role="presentation">
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={modalTitle}>{t('pigs.newFeedTruckArrival')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('pigs.receiveDate')} *
            <input type="date" required value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.fiscalDocumentNumber')} *
            <input type="text" required value={fiscalDocumentNumber} onChange={(e) => setFiscalDocumentNumber(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.actualAmountKg')} *
            <input type="number" required min="0" step="any" value={actualAmountKg} onChange={(e) => setActualAmountKg(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.feedType')} *
            <input type="text" required value={feedType} onChange={(e) => setFeedType(e.target.value)} style={inputStyle} />
          </label>

          {pendingSchedule.length > 0 && (
            <label style={labelStyle}>
              {t('pigs.feedSchedule')}
              <select value={feedScheduleId} onChange={(e) => setFeedScheduleId(e.target.value)} style={inputStyle}>
                <option value="">—</option>
                {pendingSchedule.map((s) => (
                  <option key={s.sk} value={s.sk}>{s.feed_type} — {s.planned_date} ({s.expected_amount_kg} kg)</option>
                ))}
              </select>
            </label>
          )}

          <div style={btnRow}>
            <button type="button" style={cancelBtn} onClick={onClose}>{t('common.cancel')}</button>
            <button type="submit" style={submitBtn} disabled={submitting}>
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 500, padding: '1rem',
};
const modalStyle: React.CSSProperties = {
  backgroundColor: '#fff', borderRadius: '8px', padding: '1.5rem',
  width: '100%', maxWidth: '480px', maxHeight: '90vh', overflowY: 'auto',
};
const modalTitle: React.CSSProperties = { fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem' };
const labelStyle: React.CSSProperties = { display: 'block', marginBottom: '1rem', fontSize: '0.9rem', fontWeight: 500, color: '#333' };
const inputStyle: React.CSSProperties = {
  display: 'block', width: '100%', padding: '10px', marginTop: '0.25rem',
  border: '1px solid #ccc', borderRadius: '4px', fontSize: '1rem', boxSizing: 'border-box', minHeight: '44px',
};
const btnRow: React.CSSProperties = { display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' };
const cancelBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#eee', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem',
};
const submitBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
const successMsg: React.CSSProperties = { padding: '0.75rem', marginBottom: '0.75rem', backgroundColor: '#e8f5e9', borderRadius: '4px', color: '#2e7d32' };
const errorMsg: React.CSSProperties = { padding: '0.75rem', marginBottom: '0.75rem', backgroundColor: '#fdecea', borderRadius: '4px', color: '#721c24' };
