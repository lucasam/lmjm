import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { replaceEarTag } from '../../api/client';

interface EarTagFormProps {
  earTag: string;
  onClose: () => void;
  onSuccess: (newEarTag: string) => void;
}

export default function EarTagForm({ earTag, onClose, onSuccess }: EarTagFormProps) {
  const { t } = useTranslation();
  const [newEarTag, setNewEarTag] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newEarTag.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      const updated = await replaceEarTag(earTag, trimmed);
      onSuccess(updated.ear_tag ?? trimmed);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('cattle.changeEarTag', 'Alterar Número do Brinco')}</h2>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('cattle.currentEarTag', 'Número Atual')}
            <input type="text" value={earTag} disabled className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.newEarTag', 'Novo Número')} *
            <input
              type="text"
              required
              autoFocus
              value={newEarTag}
              onChange={(e) => setNewEarTag(e.target.value)}
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
