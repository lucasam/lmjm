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
          <h1 className="page-title">{mod.name}</h1>
          <div className="detail-grid">
            <DetailRow label={t('pigs.moduleNumber')} value={String(mod.module_number)} />
            <DetailRow label={t('pigs.moduleName')} value={mod.name} />
            <DetailRow label={t('pigs.area')} value={String(mod.area)} />
            <DetailRow label={t('pigs.supportedAnimalCount')} value={String(mod.supported_animal_count)} />
            <DetailRow label={t('pigs.siloCapacity')} value={String(mod.silo_capacity)} />
          </div>
          <button type="button" className="btn btn-primary" onClick={() => setEditing(true)}>
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
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{t('pigs.editModule', 'Editar Módulo')}</h2>
        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {formError && <div className="alert alert-error">{formError}</div>}
        <form onSubmit={handleSubmit}>
          <label className="form-label">
            {t('pigs.moduleName')} *
            <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.area')}
            <input type="number" min="0" step="1" value={area} onChange={(e) => setArea(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.supportedAnimalCount')}
            <input type="number" min="0" step="1" value={supportedAnimalCount} onChange={(e) => setSupportedAnimalCount(e.target.value)} className="form-input" />
          </label>
          <label className="form-label">
            {t('pigs.siloCapacity')}
            <input type="number" min="0" step="1" value={siloCapacity} onChange={(e) => setSiloCapacity(e.target.value)} className="form-input" />
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

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="detail-row">
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value ?? '—'}</span>
    </div>
  );
}
