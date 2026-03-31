import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { updateFeedSchedule } from '../../api/client';
import type { FeedSchedule } from '../../types/models';

interface FeedScheduleEntry {
  feed_type: string;
  planned_date: string;
  expected_amount_kg: string;
}

interface FeedScheduleFormProps {
  batchId: string;
  existing: FeedSchedule[];
  onClose: () => void;
  onSuccess: () => void;
}

function toEntry(s: FeedSchedule): FeedScheduleEntry {
  return {
    feed_type: s.feed_type,
    planned_date: s.planned_date,
    expected_amount_kg: String(s.expected_amount_kg),
  };
}

export default function FeedScheduleForm({ batchId, existing, onClose, onSuccess }: FeedScheduleFormProps) {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<FeedScheduleEntry[]>(
    existing.length > 0 ? existing.map(toEntry) : [{ feed_type: '', planned_date: '', expected_amount_kg: '' }],
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const updateEntry = (idx: number, field: keyof FeedScheduleEntry, value: string) => {
    setEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, [field]: value } : e)));
  };

  const addEntry = () => {
    setEntries((prev) => [...prev, { feed_type: '', planned_date: '', expected_amount_kg: '' }]);
  };

  const removeEntry = (idx: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = entries.map((entry) => ({
        pk: '',
        sk: '',
        feed_type: entry.feed_type,
        planned_date: entry.planned_date,
        expected_amount_kg: Number(entry.expected_amount_kg),
      }));
      await updateFeedSchedule(batchId, data);
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
      <div style={wideModalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={modalTitle}>{t('pigs.feedSchedule')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          {entries.map((entry, idx) => (
            <div key={idx} style={entryRow}>
              <label style={inlineLabel}>
                {t('pigs.feedType')}
                <input type="text" required value={entry.feed_type} onChange={(e) => updateEntry(idx, 'feed_type', e.target.value)} style={inlineInput} />
              </label>
              <label style={inlineLabel}>
                {t('pigs.plannedDate')}
                <input type="date" required value={entry.planned_date} onChange={(e) => updateEntry(idx, 'planned_date', e.target.value)} style={inlineInput} />
              </label>
              <label style={inlineLabel}>
                {t('pigs.expectedAmountKg')}
                <input type="number" required min="0" step="any" value={entry.expected_amount_kg} onChange={(e) => updateEntry(idx, 'expected_amount_kg', e.target.value)} style={inlineInput} />
              </label>
              <button type="button" style={removeBtn} onClick={() => removeEntry(idx)} aria-label={t('common.delete')}>✕</button>
            </div>
          ))}

          <button type="button" style={addBtn} onClick={addEntry}>+ {t('common.create')}</button>

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
const wideModalStyle: React.CSSProperties = {
  backgroundColor: '#fff', borderRadius: '8px', padding: '1.5rem',
  width: '100%', maxWidth: '640px', maxHeight: '90vh', overflowY: 'auto',
};
const modalTitle: React.CSSProperties = { fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem' };
const entryRow: React.CSSProperties = {
  display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap',
  marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid #eee',
};
const inlineLabel: React.CSSProperties = { display: 'flex', flexDirection: 'column', fontSize: '0.85rem', fontWeight: 500, color: '#333', flex: '1 1 120px' };
const inlineInput: React.CSSProperties = {
  padding: '8px', marginTop: '0.25rem', border: '1px solid #ccc', borderRadius: '4px',
  fontSize: '0.9rem', boxSizing: 'border-box', minHeight: '44px',
};
const removeBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '8px',
  backgroundColor: '#fdecea', color: '#721c24', border: 'none', borderRadius: '4px',
  cursor: 'pointer', fontSize: '1rem', fontWeight: 600, alignSelf: 'flex-end',
};
const addBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#e3f2fd', color: '#1976d2', border: 'none', borderRadius: '4px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600, marginBottom: '1rem',
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
