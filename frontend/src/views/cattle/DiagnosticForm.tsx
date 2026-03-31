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
  const [pregnant, setPregnant] = useState(false);
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
        ...(note ? { note } : {}),
        ...(tags ? { tags } : {}),
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
        <h2 style={modalTitle}>{t('cattle.newDiagnostic')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('cattle.diagnosticDate')} *
            <input
              type="date"
              required
              value={diagnosticDate}
              onChange={(e) => setDiagnosticDate(e.target.value)}
              style={inputStyle}
            />
          </label>

          <div style={toggleRow}>
            <span style={toggleLabel}>{t('cattle.pregnant')} *</span>
            <button
              type="button"
              style={{
                ...toggleBtn,
                backgroundColor: pregnant ? '#2e7d32' : '#bbb',
              }}
              onClick={() => setPregnant((p) => !p)}
              aria-pressed={pregnant}
            >
              {pregnant ? t('common.yes') : t('common.no')}
            </button>
          </div>

          <label style={labelStyle}>
            {t('cattle.notes')}
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              style={inputStyle}
            />
          </label>

          <label style={labelStyle}>
            {t('cattle.tags')}
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              style={inputStyle}
            />
          </label>

          <div style={btnRow}>
            <button type="button" style={cancelBtn} onClick={onClose}>
              {t('common.cancel')}
            </button>
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
  border: '1px solid #ccc', borderRadius: '4px', fontSize: '1rem', boxSizing: 'border-box',
  minHeight: '44px',
};
const toggleRow: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' };
const toggleLabel: React.CSSProperties = { fontSize: '0.9rem', fontWeight: 500, color: '#333' };
const toggleBtn: React.CSSProperties = {
  minWidth: '64px', minHeight: '44px', padding: '8px 16px',
  color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer',
  fontSize: '0.9rem', fontWeight: 600, transition: 'background-color 0.15s',
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
