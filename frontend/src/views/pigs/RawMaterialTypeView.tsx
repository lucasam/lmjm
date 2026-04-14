import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listRawMaterialTypes, postRawMaterialType } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import type { RawMaterialType } from '../../types/models';

interface FormState {
  code: string;
  description: string;
  category: 'feed' | 'medicine';
}

const emptyForm: FormState = {
  code: '',
  description: '',
  category: 'feed',
};

const PAGE_SIZE = 30;

export default function RawMaterialTypeView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const fetchData = useCallback(() => listRawMaterialTypes(), []);
  const { data, loading, error, refetch } = useApi(fetchData);

  const [form, setForm] = useState<FormState>(emptyForm);
  const [editing, setEditing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [page, setPage] = useState(0);

  const totalPages = Math.ceil((data?.length ?? 0) / PAGE_SIZE);
  const pageData = (data ?? []).slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const setField = (field: keyof FormState, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleRowClick = (row: RawMaterialType) => {
    setForm({
      code: row.code,
      description: row.description,
      category: row.category,
    });
    setEditing(true);
    setShowForm(true);
    setSubmitError(null);
    setSubmitSuccess(false);
  };

  const handleNew = () => {
    setForm(emptyForm);
    setEditing(false);
    setShowForm(true);
    setSubmitError(null);
    setSubmitSuccess(false);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditing(false);
    setForm(emptyForm);
    setSubmitError(null);
    setSubmitSuccess(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      await postRawMaterialType({
        code: form.code,
        description: form.description,
        category: form.category,
      });
      setSubmitSuccess(true);
      setShowForm(false);
      setEditing(false);
      setForm(emptyForm);
      refetch();
      setTimeout(() => setSubmitSuccess(false), 2000);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const columns: Column<RawMaterialType>[] = [
    { header: t('rawMaterialType.code', 'Código'), accessor: (r) => r.code },
    { header: t('rawMaterialType.description', 'Descrição'), accessor: (r) => r.description },
    { header: t('rawMaterialType.category', 'Categoria'), accessor: (r) => r.category },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('rawMaterialType.title', 'Tipos de Matéria Prima') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <div className="action-bar" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('rawMaterialType.title', 'Tipos de Matéria Prima')}</h1>
        <button type="button" className="btn btn-primary" onClick={handleNew}>
          {t('rawMaterialType.new', 'Novo Tipo')}
        </button>
      </div>

      {submitSuccess && <div className="alert alert-success">✓ {t('common.save')}</div>}
      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        <>
          <DataTable
            columns={columns}
            data={pageData}
            keyExtractor={(r) => r.sk}
            onRowClick={handleRowClick}
          />

          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
              <button
                type="button"
                className="btn btn-outline"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                {t('common.previous', 'Anterior')}
              </button>
              <span>{page + 1} / {totalPages}</span>
              <button
                type="button"
                className="btn btn-outline"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                {t('common.next', 'Próximo')}
              </button>
            </div>
          )}
        </>
      )}

      {showForm && (
        <div className="modal-overlay" onClick={handleCancel} role="presentation">
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h2 className="modal-title">
              {editing ? t('common.edit') : t('rawMaterialType.new', 'Novo Tipo')}
            </h2>

            {submitError && <div className="alert alert-error">{submitError}</div>}

            <form onSubmit={handleSubmit}>
              <label className="form-label">
                {t('rawMaterialType.code', 'Código')} *
                <input
                  type="text"
                  required
                  value={form.code}
                  onChange={(e) => setField('code', e.target.value)}
                  className="form-input"
                  readOnly={editing}
                />
              </label>

              <label className="form-label">
                {t('rawMaterialType.description', 'Descrição')} *
                <input
                  type="text"
                  required
                  value={form.description}
                  onChange={(e) => setField('description', e.target.value)}
                  className="form-input"
                />
              </label>

              <label className="form-label">
                {t('rawMaterialType.category', 'Categoria')} *
                <select
                  required
                  value={form.category}
                  onChange={(e) => setField('category', e.target.value)}
                  className="form-input"
                >
                  <option value="feed">{t('rawMaterialType.feed', 'feed')}</option>
                  <option value="medicine">{t('rawMaterialType.medicine', 'medicine')}</option>
                </select>
              </label>

              <div className="modal-btn-row">
                <button type="button" className="btn btn-secondary" onClick={handleCancel}>{t('common.cancel')}</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? t('common.loading') : t('common.submit')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate('/pigs')}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
