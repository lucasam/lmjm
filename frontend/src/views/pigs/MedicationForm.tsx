import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postMedication } from '../../api/client';

interface MedicationFormProps {
  batchId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function MedicationForm({ batchId, onClose, onSuccess }: MedicationFormProps) {
  const { t } = useTranslation();
  const [medicationName, setMedicationName] = useState('');
  const [expirationDate, setExpirationDate] = useState('');
  const [partNumber, setPartNumber] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postMedication(batchId, {
        medication_name: medicationName,
        expiration_date: expirationDate.replace(/-/g, ''),
        part_number: partNumber,
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
        <h2 className="modal-title">{t('pigs.newMedication')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.medicationName')} *
            <input type="text" required value={medicationName} onChange={(e) => setMedicationName(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.expirationDate')} *
            <input type="date" required value={expirationDate} onChange={(e) => setExpirationDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.partNumber')} *
            <input type="text" required value={partNumber} onChange={(e) => setPartNumber(e.target.value)} className="form-input" />
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
