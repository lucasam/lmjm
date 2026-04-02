import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listModules, createBatch } from '../../api/client';
import { useApi } from '../../hooks/useApi';
import type { Module } from '../../types/models';

interface BatchFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

export default function BatchForm({ onClose, onSuccess }: BatchFormProps) {
  const { t } = useTranslation();

  const fetchModules = useCallback(() => listModules(), []);
  const { data: modules } = useApi(fetchModules);

  const [moduleId, setModuleId] = useState('');
  const [supplyId, setSupplyId] = useState('');
  const [receiveDate, setReceiveDate] = useState('');
  const [minFeedStockThreshold, setMinFeedStockThreshold] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createBatch({
        supply_id: Number(supplyId),
        module_id: moduleId,
        receive_date: receiveDate.replace(/-/g, ''),
        min_feed_stock_threshold: Number(minFeedStockThreshold),
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
        <h2 className="modal-title">{t('pigs.newBatch')}</h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.supplyId')} *
            <input type="number" required min="1" step="1" value={supplyId} onChange={(e) => setSupplyId(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.modules')} *
            <select required value={moduleId} onChange={(e) => setModuleId(e.target.value)} className="form-input">
              <option value="">{t('common.search')}</option>
              {(modules ?? []).map((m: Module) => (
                <option key={m.pk} value={m.pk}>{m.name} (#{m.module_number})</option>
              ))}
            </select>
          </label>

          <label className="form-label">
            {t('pigs.receiveDate')} *
            <input type="date" required value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.minFeedStockThreshold')} *
            <input type="number" required min="0" step="any" value={minFeedStockThreshold} onChange={(e) => setMinFeedStockThreshold(e.target.value)} className="form-input" />
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
