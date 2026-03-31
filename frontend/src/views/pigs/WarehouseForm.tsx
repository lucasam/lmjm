import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { createWarehouse, updateWarehouse } from '../../api/client';
import type { Warehouse } from '../../types/models';

interface WarehouseFormProps {
  moduleId: string;
  warehouse: Warehouse | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function WarehouseForm({ moduleId, warehouse, onClose, onSuccess }: WarehouseFormProps) {
  const { t } = useTranslation();
  const isEdit = warehouse !== null;

  const [name, setName] = useState(warehouse?.name ?? '');
  const [area, setArea] = useState(warehouse ? String(warehouse.area) : '');
  const [supportedAnimalCount, setSupportedAnimalCount] = useState(warehouse ? String(warehouse.supported_animal_count) : '');
  const [siloCapacity, setSiloCapacity] = useState(warehouse ? String(warehouse.silo_capacity) : '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = {
        name,
        area: Number(area),
        supported_animal_count: Number(supportedAnimalCount),
        silo_capacity: Number(siloCapacity),
      };
      if (isEdit) {
        const warehouseId = warehouse.sk.replace('Warehouse|', '');
        await updateWarehouse(moduleId, warehouseId, data);
      } else {
        await createWarehouse(moduleId, data);
      }
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
        <h2 style={modalTitle}>{isEdit ? t('pigs.editWarehouse') : t('pigs.newWarehouse')}</h2>

        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {error && <div style={errorMsg}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('pigs.warehouseName')} *
            <input type="text" required value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.area')} *
            <input type="number" required min="0" step="any" value={area} onChange={(e) => setArea(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.supportedAnimalCount')} *
            <input type="number" required min="1" step="1" value={supportedAnimalCount} onChange={(e) => setSupportedAnimalCount(e.target.value)} style={inputStyle} />
          </label>

          <label style={labelStyle}>
            {t('pigs.siloCapacity')} *
            <input type="number" required min="0" step="any" value={siloCapacity} onChange={(e) => setSiloCapacity(e.target.value)} style={inputStyle} />
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
