import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { putFeedConsumptionPlan } from '../../api/client';
import type { FeedConsumptionPlanEntry } from '../../types/models';

interface FeedConsumptionPlanFormProps {
  batchId: string;
  receiveDate: string;
  existing: FeedConsumptionPlanEntry[];
  onClose: () => void;
  onSuccess: () => void;
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function FeedConsumptionPlanForm({ batchId, receiveDate, existing, onClose, onSuccess }: FeedConsumptionPlanFormProps) {
  const { t } = useTranslation();

  const existingMap = useMemo(() => {
    const m = new Map<number, number>();
    existing.forEach((e) => m.set(e.day_number, e.expected_grams_per_animal));
    return m;
  }, [existing]);

  const [values, setValues] = useState<string[]>(
    Array.from({ length: 130 }, (_, i) => {
      const v = existingMap.get(i + 1);
      return v !== undefined ? String(v) : '';
    }),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const updateValue = (idx: number, val: string) => {
    setValues((prev) => {
      const next = [...prev];
      next[idx] = val;
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data: FeedConsumptionPlanEntry[] = values.map((v, i) => ({
        day_number: i + 1,
        expected_grams_per_animal: Number(v) || 0,
        date: addDays(receiveDate, i),
      }));
      await putFeedConsumptionPlan(batchId, data);
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
        <h2 style={modalTitle}>{t('pigs.feedConsumptionPlan')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div style={tableWrapper}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>{t('pigs.dayNumber')}</th>
                  <th style={thStyle}>{t('pigs.date')}</th>
                  <th style={thStyle}>{t('pigs.expectedGramsPerAnimal')}</th>
                </tr>
              </thead>
              <tbody>
                {values.map((val, i) => (
                  <tr key={i}>
                    <td style={tdStyle}>{i + 1}</td>
                    <td style={tdStyle}>{addDays(receiveDate, i)}</td>
                    <td style={tdStyle}>
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={val}
                        onChange={(e) => updateValue(i, e.target.value)}
                        style={cellInput}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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
  width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto',
};
const modalTitle: React.CSSProperties = { fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem' };
const tableWrapper: React.CSSProperties = { overflowX: 'auto', WebkitOverflowScrolling: 'touch', marginBottom: '1rem' };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' };
const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '0.5rem', borderBottom: '2px solid #ddd',
  whiteSpace: 'nowrap', fontWeight: 600, backgroundColor: '#f5f5f5', position: 'sticky', top: 0,
};
const tdStyle: React.CSSProperties = { padding: '0.25rem 0.5rem', borderBottom: '1px solid #eee', whiteSpace: 'nowrap' };
const cellInput: React.CSSProperties = {
  width: '100%', padding: '6px', border: '1px solid #ccc', borderRadius: '4px',
  fontSize: '0.85rem', boxSizing: 'border-box', minHeight: '44px',
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
