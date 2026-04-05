import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { updateFeedSchedule } from '../../api/client';
import { FEED_TYPE_MAP } from '../../constants/feedTypes';
import type { FeedSchedule } from '../../types/models';

interface FeedScheduleEntry {
  sk: string;
  feed_type: string;
  planned_date: string;
  expected_amount_kg: string;
  status: string;
}

interface FeedScheduleFormProps {
  batchId: string;
  existing: FeedSchedule[];
  onClose: () => void;
  onSuccess: () => void;
}

function toEntry(s: FeedSchedule): FeedScheduleEntry {
  return {
    sk: s.sk,
    feed_type: s.feed_type,
    planned_date: s.planned_date,
    expected_amount_kg: String(s.expected_amount_kg),
    status: s.status ?? 'scheduled',
  };
}

export default function FeedScheduleForm({ batchId, existing, onClose, onSuccess }: FeedScheduleFormProps) {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<FeedScheduleEntry[]>(() => {
    if (existing.length === 0) return [{ sk: '', feed_type: '', planned_date: '', expected_amount_kg: '', status: 'scheduled' }];
    const sorted = [...existing].sort((a, b) => a.planned_date.localeCompare(b.planned_date));
    return sorted.map(toEntry);
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const updateEntry = (idx: number, field: keyof FeedScheduleEntry, value: string) => {
    setEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, [field]: value } : e)));
  };

  const addEntry = () => {
    setEntries((prev) => [...prev, { sk: '', feed_type: '', planned_date: '', expected_amount_kg: '', status: 'scheduled' }]);
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
        sk: entry.sk || '',
        feed_type: entry.feed_type,
        planned_date: entry.planned_date,
        expected_amount_kg: Number(entry.expected_amount_kg),
        status: entry.status as 'scheduled' | 'delivered' | 'canceled',
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
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" style={{ maxWidth: '720px' }} onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('pigs.feedSchedule')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          {entries.map((entry, idx) => (
            <div key={entry.sk || `new-${idx}`} style={entryRow}>
              <label style={inlineLabel}>
                {t('pigs.feedType')}
                <select required value={entry.feed_type} onChange={(e) => updateEntry(idx, 'feed_type', e.target.value)} className="form-input">
                  <option value="">—</option>
                  {Object.entries(FEED_TYPE_MAP).map(([code, desc]) => (
                    <option key={code} value={code}>{desc} ({code})</option>
                  ))}
                </select>
              </label>
              <label style={inlineLabel}>
                {t('pigs.plannedDate')}
                <input type="date" required value={entry.planned_date} onChange={(e) => updateEntry(idx, 'planned_date', e.target.value)} className="form-input" />
              </label>
              <label style={inlineLabel}>
                {t('pigs.expectedAmountKg')}
                <input type="number" required min="0" step="any" value={entry.expected_amount_kg} onChange={(e) => updateEntry(idx, 'expected_amount_kg', e.target.value)} className="form-input" />
              </label>
              <label style={inlineLabel}>
                {t('pigs.status')}
                <select value={entry.status} onChange={(e) => updateEntry(idx, 'status', e.target.value)} className="form-input">
                  <option value="scheduled">{t('pigs.feedScheduleStatusScheduled', 'Agendado')}</option>
                  <option value="delivered">{t('pigs.feedScheduleStatusDelivered', 'Entregue')}</option>
                  <option value="canceled">{t('pigs.feedScheduleStatusCanceled', 'Cancelado')}</option>
                </select>
              </label>
              <button type="button" className="btn btn-danger" style={{ alignSelf: 'flex-end', padding: '8px 12px' }} onClick={() => removeEntry(idx)} aria-label={t('common.delete')}>✕</button>
            </div>
          ))}

          <button type="button" className="btn btn-outline" style={{ marginBottom: '1rem' }} onClick={addEntry}>+ {t('common.create')}</button>

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

const entryRow: React.CSSProperties = {
  display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap',
  marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-light)',
};
const inlineLabel: React.CSSProperties = { display: 'flex', flexDirection: 'column', fontSize: '0.85rem', fontWeight: 500, color: 'var(--text)', flex: '1 1 120px' };
