import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getCattleAnimal, listWeights, listInseminations } from '../../api/client';
import { formatDate } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import WeightForm from './WeightForm';
import DiagnosticForm from './DiagnosticForm';
import type { Weight } from '../../types/models';

export default function AnimalDetailView() {
  const { t } = useTranslation();
  const { earTag } = useParams<{ earTag: string }>();
  const { user, logout } = useAuth();
  const [showWeightForm, setShowWeightForm] = useState(false);
  const [showDiagnosticForm, setShowDiagnosticForm] = useState(false);

  const tag = earTag ?? '';

  const fetchAnimal = useCallback(() => getCattleAnimal(tag), [tag]);
  const fetchWeights = useCallback(() => listWeights(tag), [tag]);
  const fetchInseminations = useCallback(() => listInseminations(tag), [tag]);

  const { data: animal, loading: loadingAnimal, error: errorAnimal, refetch: refetchAnimal } = useApi(fetchAnimal);
  const { data: weights, loading: loadingWeights, error: errorWeights, refetch: refetchWeights } = useApi(fetchWeights);
  const { data: inseminations } = useApi(fetchInseminations);

  const latestInsemination = useMemo(() => {
    if (!inseminations || inseminations.length === 0) return null;
    return [...inseminations].sort((a, b) => b.insemination_date.localeCompare(a.insemination_date))[0];
  }, [inseminations]);

  const loading = loadingAnimal || loadingWeights;
  const error = errorAnimal || errorWeights;

  const weightCols: Column<Weight>[] = [
    { header: t('cattle.weighingDate'), accessor: (r) => formatDate(r.weighing_date) },
    { header: t('cattle.weight'), accessor: (r) => `${r.weight_kg} kg` },
  ];

  // Filter weights from the last 2 years for the chart, sorted ascending by date
  const chartWeights = useMemo(() => {
    if (!weights || weights.length === 0) return [];
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
    const cutoff = twoYearsAgo.toISOString().slice(0, 10);
    return [...weights]
      .filter((w) => w.weighing_date >= cutoff)
      .sort((a, b) => a.weighing_date.localeCompare(b.weighing_date));
  }, [weights]);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: tag },
  ];

  const handleWeightSuccess = () => {
    setShowWeightForm(false);
    refetchWeights();
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">{t('cattle.animalDetail')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={() => { refetchAnimal(); refetchWeights(); }} />}

      {!loading && !error && animal && (
        <>
          <div className="detail-grid">
            <DetailRow label={t('cattle.earTag')} value={animal.ear_tag} />
            <DetailRow label={t('cattle.breed')} value={animal.breed} />
            <DetailRow label={t('cattle.sex')} value={animal.sex} />
            <DetailRow label={t('cattle.birthDate')} value={animal.birth_date ? formatDate(animal.birth_date) : undefined} />
            <DetailRow label={t('cattle.mother')} value={animal.mother} />
            <DetailRow label={t('cattle.batch')} value={animal.batch} />
            <DetailRow label={t('cattle.status')} value={animal.status} />
            <DetailRow label={t('cattle.pregnant')} value={animal.pregnant == null ? undefined : animal.pregnant ? t('common.yes') : t('common.no')} />
            <DetailRow label={t('cattle.implanted')} value={animal.implanted == null ? undefined : animal.implanted ? t('common.yes') : t('common.no')} />
            <DetailRow label={t('cattle.inseminated')} value={animal.inseminated == null ? undefined : animal.inseminated ? t('common.yes') : t('common.no')} />
            <DetailRow label={t('cattle.lactating')} value={animal.lactating == null ? undefined : animal.lactating ? t('common.yes') : t('common.no')} />
            <DetailRow label={t('cattle.transferred')} value={animal.transferred == null ? undefined : animal.transferred ? t('common.yes') : t('common.no')} />
            <DetailRow label={t('cattle.tags')} value={animal.tags?.join(', ')} />
          </div>

          {/* Notes — one per line, reversed */}
          {animal.notes && animal.notes.length > 0 && (
            <>
              <h2 className="section-title">{t('cattle.notes')}</h2>
              <div style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                marginBottom: 'var(--space-md)',
              }}>
                {[...animal.notes].reverse().map((note, i) => (
                  <div key={i} style={{
                    padding: 'var(--space-sm) var(--space-md)',
                    borderBottom: i < animal.notes!.length - 1 ? '1px solid var(--border-light)' : 'none',
                    fontSize: '0.9rem',
                    lineHeight: '1.5',
                  }}>
                    {note}
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="action-bar">
            <button type="button" className="btn btn-primary" onClick={() => setShowWeightForm(true)}>
              {t('cattle.newWeight')}
            </button>
            {animal.inseminated && (
              <button type="button" className="btn btn-primary" onClick={() => setShowDiagnosticForm(true)}>
                {t('cattle.newDiagnostic', 'Diagnóstico')}
              </button>
            )}
          </div>

          {/* Weight chart — last 2 years */}
          {chartWeights.length >= 2 && (
            <>
              <h2 className="section-title">{t('cattle.weightChart', 'Evolução de Peso')}</h2>
              <WeightChart weights={chartWeights} />
            </>
          )}

          {/* Weight history table */}
          <h2 className="section-title">{t('cattle.weights')}</h2>
          <DataTable
            columns={weightCols}
            data={weights ?? []}
            keyExtractor={(_, i) => String(i)}
          />
        </>
      )}

      {showWeightForm && (
        <WeightForm
          earTag={tag}
          onClose={() => setShowWeightForm(false)}
          onSuccess={handleWeightSuccess}
        />
      )}

      {showDiagnosticForm && (
        <DiagnosticForm
          earTag={tag}
          insemination={latestInsemination}
          onClose={() => setShowDiagnosticForm(false)}
          onSuccess={() => { setShowDiagnosticForm(false); refetchAnimal(); }}
        />
      )}
    </Layout>
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


function WeightChart({ weights }: { weights: Weight[] }) {
  if (weights.length < 2) return null;

  const padding = { top: 20, right: 16, bottom: 40, left: 50 };
  const width = 600;
  const height = 280;
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const minKg = Math.min(...weights.map((w) => w.weight_kg));
  const maxKg = Math.max(...weights.map((w) => w.weight_kg));
  const yMin = Math.max(0, minKg - 20);
  const yMax = maxKg + 20;
  const yRange = yMax - yMin || 1;

  // Parse dates as day offsets from first date
  const parseDateLocal = (d: string) => {
    const [y, m, day] = d.split('-').map(Number);
    return new Date(y, m - 1, day).getTime();
  };
  const times = weights.map((w) => parseDateLocal(w.weighing_date));
  const tMin = times[0];
  const tMax = times[times.length - 1];
  const tRange = tMax - tMin || 1;

  const toX = (t: number) => padding.left + ((t - tMin) / tRange) * chartW;
  const toY = (kg: number) => padding.top + chartH - ((kg - yMin) / yRange) * chartH;

  const points = weights.map((w, i) => ({ x: toX(times[i]), y: toY(w.weight_kg), w }));
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');

  // Y-axis ticks (5 ticks)
  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);

  // X-axis: show first, last, and a few middle dates
  const xTickCount = Math.min(weights.length, 6);
  const xTickIndices = Array.from({ length: xTickCount }, (_, i) =>
    Math.round((i * (weights.length - 1)) / (xTickCount - 1))
  );

  return (
    <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch', marginBottom: 'var(--space-md)' }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', maxWidth: `${width}px`, height: 'auto', background: 'var(--surface)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}
      >
        {/* Grid lines */}
        {yTicks.map((tick) => (
          <line
            key={tick}
            x1={padding.left}
            y1={toY(tick)}
            x2={width - padding.right}
            y2={toY(tick)}
            stroke="var(--border-light)"
            strokeWidth={1}
          />
        ))}

        {/* Y-axis labels */}
        {yTicks.map((tick) => (
          <text
            key={`yl-${tick}`}
            x={padding.left - 6}
            y={toY(tick) + 4}
            textAnchor="end"
            fontSize={11}
            fill="var(--text-secondary)"
          >
            {Math.round(tick)}
          </text>
        ))}

        {/* X-axis labels */}
        {xTickIndices.map((idx) => (
          <text
            key={`xl-${idx}`}
            x={points[idx].x}
            y={height - 6}
            textAnchor="middle"
            fontSize={10}
            fill="var(--text-secondary)"
          >
            {formatDate(weights[idx].weighing_date)}
          </text>
        ))}

        {/* Line */}
        <path d={linePath} fill="none" stroke="var(--primary)" strokeWidth={2.5} strokeLinejoin="round" />

        {/* Data points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={4} fill="var(--primary)" stroke="var(--surface)" strokeWidth={2} />
            <title>{`${formatDate(p.w.weighing_date)}: ${p.w.weight_kg} kg`}</title>
          </g>
        ))}

        {/* Y-axis unit label */}
        <text x={padding.left} y={padding.top - 6} fontSize={11} fill="var(--text-secondary)">kg</text>
      </svg>
    </div>
  );
}
