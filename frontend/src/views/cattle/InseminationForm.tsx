import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postInsemination } from '../../api/client';

interface InseminationFormProps {
  earTag: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function InseminationForm({ earTag, onClose, onSuccess }: InseminationFormProps) {
  const { t } = useTranslation();
  const [inseminationDate, setInseminationDate] = useState('');
  const [semen, setSemen] = useState('');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postInsemination(earTag, {
        insemination_date: inseminationDate.replace(/-/g, ''),
        semen,
        ...(note ? { note } : {}),
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
        <h2 className="modal-title">{t('cattle.newInsemination')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('cattle.inseminationDate')} *
            <input
              type="date"
              required
              value={inseminationDate}
              onChange={(e) => setInseminationDate(e.target.value)}
              className="form-input"
            />
          </label>

          <label className="form-label">
            {t('cattle.semen')} *
            <input
              type="text"
              required
              value={semen}
              onChange={(e) => setSemen(e.target.value)}
              className="form-input"
            />
          </label>

          <label className="form-label">
            {t('cattle.notes')}
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
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
