import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listFeedConsumptionTemplates, postFeedConsumptionTemplate } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import type { FeedConsumptionTemplate } from '../../types/models';

interface FormState {
  sequence: string;
  expected_piglet_weight: string;
  expected_kg_per_animal: string;
}

const emptyForm: FormState = {
  sequence: '',
  expected_piglet_weight: '',
  expected_kg_per_animal: '',
};

const PAGE_SIZE = 30;

export default function FeedConsumptionTemplateView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const fetchData = useCallback(() => listFeedConsumptionTemplates(), []);
  const { data, loading, error, refetch } = useApi(fetchData);

  const [form, setForm] = useState<FormState>(emptyForm);
  const [editing, setEditing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [page, setPage] = useState(0);

  const sorted = [...(data ?? [])].sort((a, b) => a.sequence - b.sequence);
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageData = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const setField = (field: keyof FormState, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleRowClick = (row: FeedConsumptionTemplate) => {
    setForm({
      sequence: String(row.sequence),
      expected_piglet_weight: String(row.expected_piglet_weight),
      expected_kg_per_animal: String(row.expected_kg_per_animal),
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
      await postFeedConsumptionTemplate({
        sequence: Number(form.sequence),
        expected_piglet_weight: Number(form.expected_piglet_weight),
        expected_kg_per_animal: Number(form.expected_kg_per_animal),
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

  const columns: Column<FeedConsumptionTemplate>[] = [
    { header: t('feedConsumptionTemplate.sequence', 'Sequência'), accessor: (r) => r.sequence },
    { header: t('feedConsumptionTemplate.expectedPigletWeight', 'Peso Esperado (kg)'), accessor: (r) => r.expected_piglet_weight },
    { header: t('feedConsumptionTemplate.expectedKgPerAnimal', 'Kg/Animal Esperado'), accessor: (r) => r.expected_kg_per_animal },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('feedConsumptionTemplate.title', 'Feed Consumption Template') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <div className="action-bar" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('feedConsumptionTemplate.title', 'Feed Consumption Template')}</h1>
        <button type="button" className="btn btn-primary" onClick={handleNew}>
          {t('feedConsumptionTemplate.new', 'Novo')}
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
              {editing ? t('common.edit') : t('feedConsumptionTemplate.new', 'Novo')}
            </h2>

            {submitError && <div className="alert alert-error">{submitError}</div>}

            <form onSubmit={handleSubmit}>
              <label className="form-label">
                {t('feedConsumptionTemplate.sequence', 'Sequência')} *
                <input
                  type="number"
                  required
                  value={form.sequence}
                  onChange={(e) => setField('sequence', e.target.value)}
                  className="form-input"
                  readOnly={editing}
                />
              </label>

              <label className="form-label">
                {t('feedConsumptionTemplate.expectedPigletWeight', 'Peso Esperado (kg)')} *
                <input
                  type="number"
                  required
                  step="0.1"
                  value={form.expected_piglet_weight}
                  onChange={(e) => setField('expected_piglet_weight', e.target.value)}
                  className="form-input"
                />
              </label>

              <label className="form-label">
                {t('feedConsumptionTemplate.expectedKgPerAnimal', 'Kg/Animal Esperado')} *
                <input
                  type="number"
                  required
                  step="0.001"
                  value={form.expected_kg_per_animal}
                  onChange={(e) => setField('expected_kg_per_animal', e.target.value)}
                  className="form-input"
                />
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
