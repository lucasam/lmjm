import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postFeedBalance } from '../../api/client';

interface FeedBalanceFormProps {
  batchId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function FeedBalanceForm({ batchId, onClose, onSuccess }: FeedBalanceFormProps) {
  const { t } = useTranslation();
  const [measurementDate, setMeasurementDate] = useState('');
  const [balanceKg, setBalanceKg] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postFeedBalance(batchId, {
        measurement_date: measurementDate.replace(/-/g, ''),
        balance_kg: Number(balanceKg),
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
        <h2 className="modal-title">{t('pigs.newFeedBalance')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.measurementDate')} *
            <input type="date" required value={measurementDate} onChange={(e) => setMeasurementDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.balanceKg')} *
            <input type="number" required min="0" step="any" value={balanceKg} onChange={(e) => setBalanceKg(e.target.value)} className="form-input" />
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
