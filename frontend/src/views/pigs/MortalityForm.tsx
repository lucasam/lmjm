import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthProvider';
import { postMortality } from '../../api/client';

interface MortalityFormProps {
  batchId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function MortalityForm({ batchId, onClose, onSuccess }: MortalityFormProps) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [mortalityDate, setMortalityDate] = useState('');
  const [sex, setSex] = useState<'Male' | 'Female'>('Male');
  const [origin, setOrigin] = useState('');
  const [deathReason, setDeathReason] = useState('');
  const [reportedBy, setReportedBy] = useState(user?.name ?? user?.email ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postMortality(batchId, {
        mortality_date: mortalityDate.replace(/-/g, ''),
        sex,
        origin,
        death_reason: deathReason,
        reported_by: reportedBy,
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
        <h2 className="modal-title">{t('pigs.newMortality')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.mortalityDate')} *
            <input type="date" required value={mortalityDate} onChange={(e) => setMortalityDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.sex')} *
            <select required value={sex} onChange={(e) => setSex(e.target.value as 'Male' | 'Female')} className="form-input">
              <option value="Male">{t('pigs.male')}</option>
              <option value="Female">{t('pigs.female')}</option>
            </select>
          </label>

          <label className="form-label">
            {t('pigs.origin')} *
            <input type="text" required value={origin} onChange={(e) => setOrigin(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.deathReason')} *
            <input type="text" required value={deathReason} onChange={(e) => setDeathReason(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.reportedBy')} *
            <input type="text" required value={reportedBy} onChange={(e) => setReportedBy(e.target.value)} className="form-input" />
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
