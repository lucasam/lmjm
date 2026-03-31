import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postPigTruckArrival } from '../../api/client';

interface PigTruckArrivalFormProps {
  batchId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function PigTruckArrivalForm({ batchId, onClose, onSuccess }: PigTruckArrivalFormProps) {
  const { t } = useTranslation();
  const [animalCount, setAnimalCount] = useState('');
  const [sex, setSex] = useState<'Male' | 'Female'>('Male');
  const [arrivalDate, setArrivalDate] = useState('');
  const [pigAgeDays, setPigAgeDays] = useState('');
  const [originName, setOriginName] = useState('');
  const [originType, setOriginType] = useState<'UPL' | 'Creche'>('UPL');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postPigTruckArrival(batchId, {
        animal_count: Number(animalCount),
        sex,
        arrival_date: arrivalDate.replace(/-/g, ''),
        pig_age_days: Number(pigAgeDays),
        origin_name: originName,
        origin_type: originType,
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
        <h2 style={modalTitle}>{t('pigs.newPigTruckArrival')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('pigs.animalCount')} *
            <input type="number" required min="1" step="1" value={animalCount} onChange={(e) => setAnimalCount(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('cattle.sex')} *
            <select required value={sex} onChange={(e) => setSex(e.target.value as 'Male' | 'Female')} style={inputStyle}>
              <option value="Male">{t('pigs.male')}</option>
              <option value="Female">{t('pigs.female')}</option>
            </select>
          </label>

          <label style={labelStyle}>
            {t('pigs.arrivalDate')} *
            <input type="date" required value={arrivalDate} onChange={(e) => setArrivalDate(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.pigAgeDays')} *
            <input type="number" required min="0" step="1" value={pigAgeDays} onChange={(e) => setPigAgeDays(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.originName')} *
            <input type="text" required value={originName} onChange={(e) => setOriginName(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.originType')} *
            <select required value={originType} onChange={(e) => setOriginType(e.target.value as 'UPL' | 'Creche')} style={inputStyle}>
              <option value="UPL">{t('pigs.upl')}</option>
              <option value="Creche">{t('pigs.creche')}</option>
            </select>
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
