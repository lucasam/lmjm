import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { putFeedConsumptionPlan } from '../../api/client';
import { formatDate } from '../../i18n';
import type { FeedConsumptionPlanEntry } from '../../types/models';

interface FeedConsumptionPlanFormProps {
  batchId: string;
  receiveDate: string;
  existing: FeedConsumptionPlanEntry[];
  onClose: () => void;
  onSuccess: () => void;
}

/** Add days to a YYYY-MM-DD string without timezone issues. */
function addDays(dateStr: string, days: number): string {
  const [y, m, d] = dateStr.split('-').map(Number);
  const date = new Date(y, m - 1, d + days);
  const ny = date.getFullYear();
  const nm = String(date.getMonth() + 1).padStart(2, '0');
  const nd = String(date.getDate()).padStart(2, '0');
  return `${ny}-${nm}-${nd}`;
}

export default function FeedConsumptionPlanForm({ batchId, receiveDate, existing, onClose, onSuccess }: FeedConsumptionPlanFormProps) {
  const { t } = useTranslation();

  const existingMap = useMemo(() => {
    const m = new Map<number, number>();
    const sorted = [...existing].sort((a, b) => a.day_number - b.day_number);
    sorted.forEach((e) => m.set(e.day_number, e.expected_grams_per_animal));
    return m;
  }, [existing]);

  const [values, setValues] = useState<string[]>(
    Array.from({ length: 130 }, (_, i) => {
      const v = existingMap.get(i + 1);
      return v !== undefined && v > 0 ? String(v) : '';
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
        expected_grams_per_animal: v ? Number(v) : 0,
        date: addDays(receiveDate, i + 1),
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
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" style={{ maxWidth: '600px' }} onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('pigs.feedConsumptionPlan')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="table-wrapper" style={{ marginBottom: '1rem' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>{t('pigs.dayNumber')}</th>
                  <th>{t('pigs.date')}</th>
                  <th>{t('pigs.expectedGramsPerAnimal')}</th>
                </tr>
              </thead>
              <tbody>
                {values.map((val, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{formatDate(addDays(receiveDate, i + 1))}</td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={val}
                        onChange={(e) => updateValue(i, e.target.value)}
                        className="form-input"
                        style={{ padding: '6px', fontSize: '0.85rem' }}
                        placeholder="—"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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
