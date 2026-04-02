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
  const [fiscalDocumentNumber, setFiscalDocumentNumber] = useState('');
  const [animalWeight, setAnimalWeight] = useState('');
  const [gtaNumber, setGtaNumber] = useState('');
  const [mossa, setMossa] = useState('');
  const [suplierCode, setSuplierCode] = useState('');
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
        ...(fiscalDocumentNumber ? { fiscal_document_number: fiscalDocumentNumber } : {}),
        ...(animalWeight ? { animal_weight: Number(animalWeight) } : {}),
        ...(gtaNumber ? { gta_number: gtaNumber } : {}),
        ...(mossa ? { mossa } : {}),
        ...(suplierCode ? { suplier_code: Number(suplierCode) } : {}),
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
        <h2 className="modal-title">{t('pigs.newPigTruckArrival')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.animalCount')} *
            <input type="number" required min="1" step="1" value={animalCount} onChange={(e) => setAnimalCount(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.sex')} *
            <select required value={sex} onChange={(e) => setSex(e.target.value as 'Male' | 'Female')} className="form-input">
              <option value="Male">{t('pigs.male')}</option>
              <option value="Female">{t('pigs.female')}</option>
            </select>
          </label>

          <label className="form-label">
            {t('pigs.arrivalDate')} *
            <input type="date" required value={arrivalDate} onChange={(e) => setArrivalDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.pigAgeDays')} *
            <input type="number" required min="0" step="1" value={pigAgeDays} onChange={(e) => setPigAgeDays(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.originName')} *
            <input type="text" required value={originName} onChange={(e) => setOriginName(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.originType')} *
            <select required value={originType} onChange={(e) => setOriginType(e.target.value as 'UPL' | 'Creche')} className="form-input">
              <option value="UPL">{t('pigs.upl')}</option>
              <option value="Creche">{t('pigs.creche')}</option>
            </select>
          </label>

          <label className="form-label">
            {t('pigs.fiscalDocumentNumber')}
            <input type="text" value={fiscalDocumentNumber} onChange={(e) => setFiscalDocumentNumber(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.animalWeight')}
            <input type="number" min="0" step="1" value={animalWeight} onChange={(e) => setAnimalWeight(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.gtaNumber')}
            <input type="text" value={gtaNumber} onChange={(e) => setGtaNumber(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.mossa')}
            <input type="text" value={mossa} onChange={(e) => setMossa(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.suplierCode')}
            <input type="number" min="0" step="1" value={suplierCode} onChange={(e) => setSuplierCode(e.target.value)} className="form-input" />
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
