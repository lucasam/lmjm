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
    <div style={overlayStyle} onClick={onClose} role="presentation">
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={modalTitle}>{t('pigs.newMedicationShot')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('pigs.medicationName')} *
            <select required value={medicationName} onChange={(e) => setMedicationName(e.target.value)} style={inputStyle}>
              <option value="">—</option>
              {medications.map((m) => (
                <option key={m.sk} value={m.medication_name}>{m.medication_name}</option>
              ))}
            </select>
          </label>

          <label style={labelStyle}>
            {t('pigs.shotCount')} *
            <input type="number" required min="1" step="1" value={shotCount} onChange={(e) => setShotCount(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.date')} *
            <input type="date" required value={date} onChange={(e) => setDate(e.target.value)} style={inputStyle} />
          </label>

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
