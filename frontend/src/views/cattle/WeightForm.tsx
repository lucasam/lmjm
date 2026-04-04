import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postWeight } from '../../api/client';

interface WeightFormProps {
  earTag: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function WeightForm({ earTag, onClose, onSuccess }: WeightFormProps) {
  const { t } = useTranslation();
  const [weighingDate, setWeighingDate] = useState('');
  const [weightKg, setWeightKg] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postWeight(earTag, {
        weighing_date: weighingDate.replace(/-/g, ''),
        weight_kg: Number(weightKg),
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
        <h2 className="modal-title">{t('cattle.newWeight')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('cattle.weighingDate')} *
            <input
              type="date"
              required
              value={weighingDate}
              onChange={(e) => setWeighingDate(e.target.value)}
              className="form-input"
            />
          </label>

          <label className="form-label">
            {t('cattle.weight')} *
            <input
              type="number"
              required
              min={1}
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
              className="form-input"
            />
          </label>

          <div className="modal-btn-row">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
