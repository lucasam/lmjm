import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { addAnimalNote } from '../../api/client';

interface NoteFormProps {
  earTag: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function NoteForm({ earTag, onClose, onSuccess }: NoteFormProps) {
  const { t } = useTranslation();
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = note.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await addAnimalNote(earTag, trimmed);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('cattle.newNote', 'Nova Anotação')}</h2>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('cattle.note', 'Anotação')} *
            <textarea
              required
              autoFocus
              rows={4}
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
