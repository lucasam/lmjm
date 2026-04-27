import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postDiagnostic } from '../../api/client';

interface DiagnosticFormProps {
  earTag: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function DiagnosticForm({ earTag, onClose, onSuccess }: DiagnosticFormProps) {
  const { t } = useTranslation();
  const [diagnosticDate, setDiagnosticDate] = useState('');
  const [pregnant, setPregnant] = useState(true);
  const [note, setNote] = useState('');
  const [tags, setTags] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postDiagnostic(earTag, {
        diagnostic_date: diagnosticDate.replace(/-/g, ''),
        pregnant,
        ...(note.trim() ? { note: note.trim() } : {}),
        ...(tags.trim() ? { tags: tags.trim() } : {}),
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
        <h2 className="modal-title">{t('cattle.newDiagnostic', 'Diagnóstico')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('cattle.diagnosticDate', 'Data do Diagnóstico')} *
            <input type="date" required value={diagnosticDate} onChange={(e) => setDiagnosticDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.pregnant', 'Prenhe')} *
            <select required value={String(pregnant)} onChange={(e) => setPregnant(e.target.value === 'true')} className="form-input">
              <option value="true">{t('common.yes', 'Sim')}</option>
              <option value="false">{t('common.no', 'Não')}</option>
            </select>
          </label>

          <label className="form-label">
            {t('cattle.note', 'Observação')}
            <input type="text" value={note} onChange={(e) => setNote(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.tags', 'Tags')}
            <input type="text" value={tags} onChange={(e) => setTags(e.target.value)} className="form-input" />
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
