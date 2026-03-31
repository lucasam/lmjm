import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listModules, getModule, createBatch } from '../../api/client';
import { useApi } from '../../hooks/useApi';
import type { Module, Warehouse } from '../../types/models';

interface BatchFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

export default function BatchForm({ onClose, onSuccess }: BatchFormProps) {
  const { t } = useTranslation();

  const fetchModules = useCallback(() => listModules(), []);
  const { data: modules } = useApi(fetchModules);

  const [moduleId, setModuleId] = useState('');
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [warehouseIds, setWarehouseIds] = useState<string[]>([]);
  const [supplyId, setSupplyId] = useState('');
  const [pigCount, setPigCount] = useState('');
  const [receiveDate, setReceiveDate] = useState('');
  const [minFeedStockThreshold, setMinFeedStockThreshold] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!moduleId) {
      setWarehouses([]);
      setWarehouseIds([]);
      return;
    }
    let cancelled = false;
    getModule(moduleId).then((mod) => {
      if (!cancelled) {
        setWarehouses(mod.warehouses);
        setWarehouseIds([]);
      }
    }).catch(() => {
      if (!cancelled) setWarehouses([]);
    });
    return () => { cancelled = true; };
  }, [moduleId]);

  const toggleWarehouse = (wId: string) => {
    setWarehouseIds((prev) =>
      prev.includes(wId) ? prev.filter((id) => id !== wId) : [...prev, wId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createBatch({
        supply_id: Number(supplyId),
        module_id: moduleId,
        warehouse_ids: warehouseIds,
        pig_count: Number(pigCount),
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
    <div style={overlayStyle} onClick={onClose} role="presentation">
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={modalTitle}>{t('pigs.newBatch')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('pigs.supplyId')} *
            <input type="number" required min="1" step="1" value={supplyId} onChange={(e) => setSupplyId(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.modules')} *
            <select required value={moduleId} onChange={(e) => setModuleId(e.target.value)} style={inputStyle}>
              <option value="">{t('common.search')}</option>
              {(modules ?? []).map((m: Module) => (
                <option key={m.pk} value={m.pk}>{m.name} (#{m.module_number})</option>
              ))}
            </select>
          </label>

          {moduleId && warehouses.length > 0 && (
            <fieldset style={fieldsetStyle}>
              <legend style={legendStyle}>{t('pigs.warehouses')} *</legend>
              {warehouses.map((w) => {
                const wId = w.sk.replace('Warehouse|', '');
                return (
                  <label key={w.sk} style={checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={warehouseIds.includes(wId)}
                      onChange={() => toggleWarehouse(wId)}
                      style={checkboxInput}
                    />
                    {w.name}
                  </label>
                );
              })}
            </fieldset>
          )}

          <label style={labelStyle}>
            {t('pigs.pigCount')} *
            <input type="number" required min="1" step="1" value={pigCount} onChange={(e) => setPigCount(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.receiveDate')} *
            <input type="date" required value={receiveDate} onChange={(e) => setReceiveDate(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.minFeedStockThreshold')} *
            <input type="number" required min="0" step="any" value={minFeedStockThreshold} onChange={(e) => setMinFeedStockThreshold(e.target.value)} style={inputStyle} />
          </label>

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
const modalStyle: React.CSSProperties = {
  backgroundColor: '#fff', borderRadius: '8px', padding: '1.5rem',
  width: '100%', maxWidth: '480px', maxHeight: '90vh', overflowY: 'auto',
};
const modalTitle: React.CSSProperties = { fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem' };
const labelStyle: React.CSSProperties = { display: 'block', marginBottom: '1rem', fontSize: '0.9rem', fontWeight: 500, color: '#333' };
const inputStyle: React.CSSProperties = {
  display: 'block', width: '100%', padding: '10px', marginTop: '0.25rem',
  border: '1px solid #ccc', borderRadius: '4px', fontSize: '1rem', boxSizing: 'border-box', minHeight: '44px',
};
const fieldsetStyle: React.CSSProperties = { border: '1px solid #ccc', borderRadius: '4px', padding: '0.75rem', marginBottom: '1rem' };
const legendStyle: React.CSSProperties = { fontSize: '0.9rem', fontWeight: 500, color: '#333' };
const checkboxLabel: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0', minHeight: '44px', cursor: 'pointer' };
const checkboxInput: React.CSSProperties = { width: '20px', height: '20px' };
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
