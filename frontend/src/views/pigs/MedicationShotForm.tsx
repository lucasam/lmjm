import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postMedicationShot } from '../../api/client';
import type { Medication } from '../../types/models';

interface MedicationShotFormProps {
  batchId: string;
  medications: Medication[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function MedicationShotForm({ batchId, medications, onClose, onSuccess }: MedicationShotFormProps) {
  const { t } = useTranslation();
  const [medicationName, setMedicationName] = useState('');
  const [shotCount, setShotCount] = useState('');
  const [date, setDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postMedicationShot(batchId, {
        medication_name: medicationName,
        shot_count: Number(shotCount),
        date: date.replace(/-/g, ''),
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
        <h2 className="modal-title">{t('pigs.newMedicationShot')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.medicationName')} *
            <select required value={medicationName} onChange={(e) => setMedicationName(e.target.value)} className="form-input">
              <option value="">—</option>
              {medications.map((m) => (
                <option key={m.sk} value={m.medication_name}>{m.raw_material_code ? `${m.raw_material_code} — ` : ''}{m.medication_name}</option>
              ))}
            </select>
          </label>

          <label className="form-label">
            {t('pigs.shotCount')} *
            <input type="number" required min="1" step="1" value={shotCount} onChange={(e) => setShotCount(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.date')} *
            <input type="date" required value={date} onChange={(e) => setDate(e.target.value)} className="form-input" />
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
