import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listIntegratorWeeklyData, postIntegratorWeeklyData } from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import { computeCapMap } from '../../lib/borderoCalculator';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import type { IntegratorWeeklyData } from '../../types/models';

interface FormState {
  date_generated: string;
  validity_start: string;
  validity_end: string;
  source_data_start: string;
  source_data_end: string;
  car: string;
  mar: string;
  avg_piglet_weight: string;
  avg_slaughter_weight: string;
  average_age: string;
  number_of_samples: string;
  gdp: string;
}

const emptyForm: FormState = {
  date_generated: '',
  validity_start: '',
  validity_end: '',
  source_data_start: '',
  source_data_end: '',
  car: '',
  mar: '',
  avg_piglet_weight: '',
  avg_slaughter_weight: '',
  average_age: '',
  number_of_samples: '',
  gdp: '',
};

function parseNum(v: string): number {
  return v === '' ? NaN : Number(v);
}

export default function IntegratorWeeklyDataView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const fetchData = useCallback(() => listIntegratorWeeklyData(), []);
  const { data: records, loading, error, refetch } = useApi(fetchData);

  const [form, setForm] = useState<FormState>(emptyForm);
  const [editing, setEditing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const setField = (field: keyof FormState, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  // Live preview of computed CAP/MAP
  const preview = useMemo(() => {
    const car = parseNum(form.car);
    const mar = parseNum(form.mar);
    const avgSW = parseNum(form.avg_slaughter_weight);
    const avgPW = parseNum(form.avg_piglet_weight);
    const age = parseNum(form.average_age);
    if ([car, mar, avgSW, avgPW, age].some(isNaN)) return null;
    return computeCapMap(car, mar, avgSW, avgPW, age);
  }, [form.car, form.mar, form.avg_slaughter_weight, form.avg_piglet_weight, form.average_age]);

  const handleRowClick = (row: IntegratorWeeklyData) => {
    setForm({
      date_generated: row.date_generated,
      validity_start: row.validity_start,
      validity_end: row.validity_end,
      source_data_start: row.source_data_start,
      source_data_end: row.source_data_end,
      car: String(row.car),
      mar: String(row.mar),
      avg_piglet_weight: String(row.avg_piglet_weight),
      avg_slaughter_weight: String(row.avg_slaughter_weight),
      average_age: String(row.average_age),
      number_of_samples: String(row.number_of_samples),
      gdp: String(row.gdp),
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
      await postIntegratorWeeklyData({
        date_generated: form.date_generated,
        validity_start: form.validity_start,
        validity_end: form.validity_end,
        source_data_start: form.source_data_start,
        source_data_end: form.source_data_end,
        car: Number(form.car),
        mar: Number(form.mar),
        avg_piglet_weight: Number(form.avg_piglet_weight),
        avg_slaughter_weight: Number(form.avg_slaughter_weight),
        average_age: Number(form.average_age),
        number_of_samples: Number(form.number_of_samples),
        gdp: Number(form.gdp),
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

  const columns: Column<IntegratorWeeklyData>[] = [
    { header: t('pigs.iwdDateGenerated', 'Data Gerada'), accessor: (r) => formatDate(r.date_generated) },
    { header: t('pigs.iwdValidity', 'Vigência'), accessor: (r) => `${formatDate(r.validity_start)} – ${formatDate(r.validity_end)}` },
    { header: 'CAR', accessor: (r) => formatNumber(r.car, 4) },
    { header: 'MAR', accessor: (r) => formatNumber(r.mar, 4) },
    { header: <>CAP<br />+2 origens<br />Creche</>, accessor: (r) => formatNumber(r.cap_1, 4) },
    { header: <>CAP<br />≤2 origens<br />Creche</>, accessor: (r) => formatNumber(r.cap_2, 4) },
    { header: <>CAP<br />+2 origens<br />UPL</>, accessor: (r) => formatNumber(r.cap_3, 4) },
    { header: <>CAP<br />≤2 origens<br />UPL</>, accessor: (r) => formatNumber(r.cap_4, 4) },
    { header: <>MAP<br />+2 origens</>, accessor: (r) => formatNumber(r.map_1, 4) },
    { header: <>MAP<br />≤2 origens</>, accessor: (r) => formatNumber(r.map_2, 4) },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.integratorWeeklyData', 'Dados Semanais da Integradora') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <div className="action-bar" style={{ justifyContent: 'space-between' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('pigs.integratorWeeklyData', 'Dados Semanais da Integradora')}</h1>
        <button type="button" className="btn btn-primary" onClick={handleNew}>
          {t('pigs.iwdNew', 'Novo Registro')}
        </button>
      </div>

      {submitSuccess && <div className="alert alert-success">✓ {t('common.save')}</div>}
      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        <DataTable
          columns={columns}
          data={records ?? []}
          keyExtractor={(r) => r.sk}
          onRowClick={handleRowClick}
        />
      )}

      {showForm && (
        <div className="modal-overlay" onClick={handleCancel} role="presentation">
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <h2 className="modal-title">
              {editing ? t('common.edit') : t('pigs.iwdNew', 'Novo Registro')}
            </h2>

            {submitError && <div className="alert alert-error">{submitError}</div>}

            <form onSubmit={handleSubmit}>
              <label className="form-label">
                {t('pigs.iwdDateGenerated', 'Data Gerada')} *
                <input type="date" required value={form.date_generated} onChange={(e) => setField('date_generated', e.target.value)} className="form-input" />
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <label className="form-label">
                  {t('pigs.iwdValidityStart', 'Início Vigência')} *
                  <input type="date" required value={form.validity_start} onChange={(e) => setField('validity_start', e.target.value)} className="form-input" />
                </label>
                <label className="form-label">
                  {t('pigs.iwdValidityEnd', 'Fim Vigência')} *
                  <input type="date" required value={form.validity_end} onChange={(e) => setField('validity_end', e.target.value)} className="form-input" />
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <label className="form-label">
                  {t('pigs.iwdSourceStart', 'Início Dados Fonte')} *
                  <input type="date" required value={form.source_data_start} onChange={(e) => setField('source_data_start', e.target.value)} className="form-input" />
                </label>
                <label className="form-label">
                  {t('pigs.iwdSourceEnd', 'Fim Dados Fonte')} *
                  <input type="date" required value={form.source_data_end} onChange={(e) => setField('source_data_end', e.target.value)} className="form-input" />
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <label className="form-label">
                  CAR *
                  <input type="number" required step="any" value={form.car} onChange={(e) => setField('car', e.target.value)} className="form-input" />
                </label>
                <label className="form-label">
                  MAR *
                  <input type="number" required step="any" value={form.mar} onChange={(e) => setField('mar', e.target.value)} className="form-input" />
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <label className="form-label">
                  {t('pigs.iwdAvgPigletWeight', 'Peso Médio Leitão (kg)')} *
                  <input type="number" required step="any" value={form.avg_piglet_weight} onChange={(e) => setField('avg_piglet_weight', e.target.value)} className="form-input" />
                </label>
                <label className="form-label">
                  {t('pigs.iwdAvgSlaughterWeight', 'Peso Médio Abate (kg)')} *
                  <input type="number" required step="any" value={form.avg_slaughter_weight} onChange={(e) => setField('avg_slaughter_weight', e.target.value)} className="form-input" />
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                <label className="form-label">
                  {t('pigs.iwdAverageAge', 'Idade Média (dias)')} *
                  <input type="number" required min="0" step="any" value={form.average_age} onChange={(e) => setField('average_age', e.target.value)} className="form-input" />
                </label>
                <label className="form-label">
                  {t('pigs.iwdSamples', 'Nº Amostras')} *
                  <input type="number" required min="0" value={form.number_of_samples} onChange={(e) => setField('number_of_samples', e.target.value)} className="form-input" />
                </label>
                <label className="form-label">
                  GDP *
                  <input type="number" required step="any" value={form.gdp} onChange={(e) => setField('gdp', e.target.value)} className="form-input" />
                </label>
              </div>

              {/* Live preview of computed CAP/MAP */}
              {preview && (
                <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#f0f4f8', borderRadius: '6px' }}>
                  <strong>{t('pigs.iwdPreview', 'Prévia CAP/MAP')}</strong>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                    <span>CAP +2 origens (Creche): {formatNumber(preview.cap1, 4)}</span>
                    <span>CAP ≤2 origens (Creche): {formatNumber(preview.cap2, 4)}</span>
                    <span>CAP +2 origens (UPL): {formatNumber(preview.cap3, 4)}</span>
                    <span>CAP ≤2 origens (UPL): {formatNumber(preview.cap4, 4)}</span>
                    <span>MAP +2 origens: {formatNumber(preview.map1, 4)}</span>
                    <span>MAP ≤2 origens: {formatNumber(preview.map2, 4)}</span>
                  </div>
                </div>
              )}

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
