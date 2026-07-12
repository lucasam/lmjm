import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { addAnimalTag } from '../../api/client';

interface TagFormProps {
  earTag: string;
  existingTags: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function TagForm({ earTag, existingTags, onClose, onSuccess }: TagFormProps) {
  const { t } = useTranslation();
  const [tag, setTag] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = tag.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await addAnimalTag(earTag, trimmed);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('cattle.newTag', 'Nova Tag')}</h2>

        {error && <div className="alert alert-error">{error}</div>}

        {existingTags.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)', marginBottom: 'var(--space-sm)' }}>
            {existingTags.map((tg) => (
              <span
                key={tg}
                style={{
                  padding: '2px 8px',
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.8rem',
                }}
              >
                {tg}
              </span>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('cattle.tag', 'Tag')} *
            <input
              type="text"
              required
              autoFocus
              value={tag}
              onChange={(e) => setTag(e.target.value)}
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
