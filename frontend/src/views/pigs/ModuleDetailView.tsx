import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getModule, updateModule } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';

export default function ModuleDetailView() {
  const { t } = useTranslation();
  const { moduleId } = useParams<{ moduleId: string }>();
  const { user, logout } = useAuth();
  const [editing, setEditing] = useState(false);

  const id = moduleId ?? '';
  const fetchModule = useCallback(() => getModule(id), [id]);
  const { data: mod, loading, error, refetch } = useApi(fetchModule);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: mod ? `${t('pigs.moduleNumber')} ${mod.module_number}` : id },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && mod && (
        <>
          <h1 style={titleStyle}>{mod.name}</h1>
          <div style={detailGrid}>
            <DetailRow label={t('pigs.moduleNumber')} value={String(mod.module_number)} />
            <DetailRow label={t('pigs.moduleName')} value={mod.name} />
            <DetailRow label={t('pigs.area')} value={String(mod.area)} />
            <DetailRow label={t('pigs.supportedAnimalCount')} value={String(mod.supported_animal_count)} />
            <DetailRow label={t('pigs.siloCapacity')} value={String(mod.silo_capacity)} />
          </div>
          <button type="button" style={editBtn} onClick={() => setEditing(true)}>
            {t('common.edit')}
          </button>
        </>
      )}

      {editing && mod && (
        <ModuleEditForm
          moduleId={id}
          initial={mod}
          onClose={() => setEditing(false)}
          onSuccess={() => { setEditing(false); refetch(); }}
        />
      )}
    </Layout>
  );
}

function ModuleEditForm({ moduleId, initial, onClose, onSuccess }: {
  moduleId: string;
  initial: { name: string; area: number; supported_animal_count: number; silo_capacity: number };
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(initial.name);
  const [area, setArea] = useState(String(initial.area));
  const [supportedAnimalCount, setSupportedAnimalCount] = useState(String(initial.supported_animal_count));
  const [siloCapacity, setSiloCapacity] = useState(String(initial.silo_capacity));
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await updateModule(moduleId, {
        name,
        area: Number(area),
        supported_animal_count: Number(supportedAnimalCount),
        silo_capacity: Number(siloCapacity),
      });
      setSuccess(true);
      setTimeout(onSuccess, 600);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose} role="presentation">
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={modalTitle}>{t('pigs.editModule', 'Editar Módulo')}</h2>
        {success && <div style={successMsg}>✓ {t('common.save')}</div>}
        {formError && <div style={errorMsg}>{formError}</div>}
        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            {t('pigs.moduleName')} *
            <input type="text" required value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            {t('pigs.area')}
            <input type="number" min="0" step="1" value={area} onChange={(e) => setArea(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            {t('pigs.supportedAnimalCount')}
            <input type="number" min="0" step="1" value={supportedAnimalCount} onChange={(e) => setSupportedAnimalCount(e.target.value)} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            {t('pigs.siloCapacity')}
            <input type="number" min="0" step="1" value={siloCapacity} onChange={(e) => setSiloCapacity(e.target.value)} style={inputStyle} />
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

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div style={detailRow}>
      <span style={detailLabel}>{label}</span>
      <span style={detailValue}>{value ?? '—'}</span>
    </div>
  );
}

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const detailGrid: React.CSSProperties = { marginBottom: '1.5rem' };
const detailRow: React.CSSProperties = { display: 'flex', padding: '0.4rem 0', borderBottom: '1px solid #eee', gap: '0.5rem' };
const detailLabel: React.CSSProperties = { fontWeight: 600, minWidth: '140px', color: '#555' };
const detailValue: React.CSSProperties = { color: '#222' };
const editBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
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
