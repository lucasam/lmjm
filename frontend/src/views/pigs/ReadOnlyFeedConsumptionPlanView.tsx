import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getBatch, getFeedConsumptionPlan, generateFeedPlan } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import type { FeedConsumptionPlanEntry } from '../../types/models';

export default function ReadOnlyFeedConsumptionPlanView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { batchId } = useParams<{ batchId: string }>();
  const { user, logout } = useAuth();

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchData = useCallback(() => getFeedConsumptionPlan(id), [id]);
  const { data: batch } = useApi(fetchBatch);
  const { data, loading, error, refetch } = useApi(fetchData);

  const [showModal, setShowModal] = useState(false);
  const [formStartDate, setFormStartDate] = useState('');
  const [formWeight, setFormWeight] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const openModal = () => {
    setFormStartDate(batch?.average_start_date ?? '');
    setFormWeight(batch?.initial_animal_weight != null ? String(batch.initial_animal_weight) : '');
    setGenerateError(null);
    setShowModal(true);
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    setGenerateError(null);
    try {
      await generateFeedPlan(id, {
        ...(formStartDate ? { average_start_date: formStartDate } : {}),
        ...(formWeight ? { initial_animal_weight: Number(formWeight) } : {}),
      });
      setShowModal(false);
      refetch();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setGenerateError(message);
    } finally {
      setGenerating(false);
    }
  };

  const columns: Column<FeedConsumptionPlanEntry>[] = [
    { header: t('feedConsumptionPlan.dayNumber', 'Dia'), accessor: (r) => r.day_number },
    { header: t('feedConsumptionPlan.date', 'Data'), accessor: (r) => r.date },
    { header: t('feedConsumptionPlan.expectedPigletWeight', 'Peso Esperado (kg)'), accessor: (r) => r.expected_piglet_weight },
    { header: t('feedConsumptionPlan.expectedKgPerAnimal', 'Kg/Animal Esperado'), accessor: (r) => r.expected_kg_per_animal },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('feedConsumptionPlan.batchDetail', 'Batch Detail'), to: `/pigs/batches/${id}` },
    { label: t('feedConsumptionPlan.title', 'Feed Consumption Plan') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <div className="action-bar" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('feedConsumptionPlan.title', 'Feed Consumption Plan')}</h1>
        <button
          type="button"
          className="btn btn-primary"
          disabled={loading}
          onClick={openModal}
        >
          {t('pigs.generatePlanFromTemplate', 'Gerar Plano a partir do Template')}
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        <DataTable
          columns={columns}
          data={[...(data ?? [])].sort((a, b) => a.day_number - b.day_number)}
          keyExtractor={(r) => String(r.day_number)}
        />
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${id}`)}>
          {t('common.back')}
        </button>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)} role="presentation">
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h2 className="modal-title">{t('pigs.generatePlanFromTemplate', 'Gerar Plano a partir do Template')}</h2>

            {generateError && <div className="alert alert-error">{generateError}</div>}

            <form onSubmit={handleGenerate}>
              <label className="form-label">
                {t('pigs.averageStartDate', 'Data Início')}
                <input
                  type="date"
                  value={formStartDate}
                  onChange={(e) => setFormStartDate(e.target.value)}
                  className="form-input"
                />
              </label>

              <label className="form-label">
                {t('pigs.initialAnimalWeight', 'Peso Inicial Animal')}
                <input
                  type="number"
                  step="0.01"
                  value={formWeight}
                  onChange={(e) => setFormWeight(e.target.value)}
                  className="form-input"
                />
              </label>

              <div className="modal-btn-row">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  {t('common.cancel')}
                </button>
                <button type="submit" className="btn btn-primary" disabled={generating}>
                  {generating ? t('common.loading') : t('pigs.generatePlanFromTemplate', 'Gerar Plano')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
