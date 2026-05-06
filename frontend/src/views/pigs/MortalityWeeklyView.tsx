import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getBatch, listMortalities } from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type { Batch, Mortality } from '../../types/models';

interface WeekRow {
  week: number;
  startDate: Date;
  endDate: Date;
  deathCount: number;
  weeklyPct: number;
  cumulativePct: number;
}

function computeWeeklyData(batch: Batch, mortalities: Mortality[]): WeekRow[] {
  const totalAnimals = batch.total_animal_count ?? 0;
  if (totalAnimals === 0) return [];

  const receiveDate = new Date((batch.average_start_date ?? '') + 'T00:00:00');

  const weekDeaths: Record<number, number> = {};
  let maxWeek = 0;
  for (const m of mortalities) {
    const mDate = new Date(m.mortality_date + 'T00:00:00');
    const diffMs = mDate.getTime() - receiveDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays < 0) continue;
    const week = Math.floor(diffDays / 7) + 1;
    weekDeaths[week] = (weekDeaths[week] || 0) + 1;
    if (week > maxWeek) maxWeek = week;
  }

  const rows: WeekRow[] = [];
  let cumulativeDeaths = 0;
  const weeksToShow = Math.max(maxWeek, 1);

  for (let w = 1; w <= weeksToShow; w++) {
    const deaths = weekDeaths[w] || 0;
    cumulativeDeaths += deaths;
    const startDate = new Date(receiveDate.getTime() + (w - 1) * 7 * 86400000);
    const endDate = new Date(receiveDate.getTime() + w * 7 * 86400000 - 86400000);
    rows.push({
      week: w,
      startDate,
      endDate,
      deathCount: deaths,
      weeklyPct: (deaths / totalAnimals) * 100,
      cumulativePct: (cumulativeDeaths / totalAnimals) * 100,
    });
  }

  return rows;
}

// --- Cumulative Mortality Line Chart ---

function MortalityChart({ rows }: { rows: WeekRow[] }) {
  const [hovered, setHovered] = useState<number | null>(null);

  if (rows.length === 0) return null;

  const W = 700;
  const H = 280;
  const PAD_L = 60;
  const PAD_R = 20;
  const PAD_T = 30;
  const PAD_B = 50;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const maxY = Math.max(rows[rows.length - 1].cumulativePct * 1.2, 1);
  const minY = 0;

  const xStep = rows.length > 1 ? plotW / (rows.length - 1) : 0;
  const toX = (i: number) => PAD_L + i * xStep;
  const toY = (v: number) => PAD_T + plotH - ((v - minY) / (maxY - minY)) * plotH;

  const pathD = rows
    .map((r, i) => `${i === 0 ? 'M' : 'L'}${toX(i).toFixed(1)},${toY(r.cumulativePct).toFixed(1)}`)
    .join(' ');

  const tickCount = 5;
  const yTicks = Array.from({ length: tickCount + 1 }, (_, i) => minY + (maxY - minY) * (i / tickCount));

  // Cumulative deaths for tooltip
  let cumDeaths = 0;
  const cumulativeDeaths = rows.map(r => { cumDeaths += r.deathCount; return cumDeaths; });

  return (
    <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
      <h3 style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>Mortalidade Acumulada (%)</h3>
      <svg width={W} height={H} style={{ fontFamily: 'inherit', fontSize: '11px' }}>
        {/* Grid lines */}
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={PAD_L} y1={toY(v)} x2={W - PAD_R} y2={toY(v)} stroke="#e0e0e0" />
            <text x={PAD_L - 6} y={toY(v) + 4} textAnchor="end" fill="#666">{v.toFixed(2)}%</text>
          </g>
        ))}

        {/* Line */}
        <path d={pathD} fill="none" stroke="#d32f2f" strokeWidth={2} />

        {/* Area fill */}
        <path
          d={`${pathD} L${toX(rows.length - 1).toFixed(1)},${toY(0).toFixed(1)} L${toX(0).toFixed(1)},${toY(0).toFixed(1)} Z`}
          fill="#d32f2f"
          fillOpacity={0.08}
        />

        {/* Dots + hover areas */}
        {rows.map((r, i) => (
          <g key={i}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            <rect x={toX(i) - 15} y={PAD_T} width={30} height={plotH} fill="transparent" />
            <circle cx={toX(i)} cy={toY(r.cumulativePct)} r={hovered === i ? 5 : 3} fill="#d32f2f" />
          </g>
        ))}

        {/* Tooltip */}
        {hovered != null && (() => {
          const r = rows[hovered];
          const x = toX(hovered);
          const y = toY(r.cumulativePct);
          const label = `${formatNumber(r.cumulativePct, 2)}% (${cumulativeDeaths[hovered]} mortes)`;
          const textW = label.length * 6.5;
          const boxX = Math.min(Math.max(x - textW / 2 - 6, 0), W - textW - 16);
          return (
            <g>
              <rect x={boxX} y={y - 32} width={textW + 12} height={20} rx={4} fill="#333" fillOpacity={0.9} />
              <text x={boxX + 6} y={y - 18} fill="#fff" fontSize="11">{label}</text>
            </g>
          );
        })()}

        {/* X-axis labels */}
        {rows.map((r, i) => (
          <text key={i} x={toX(i)} y={H - PAD_B + 16} textAnchor="middle" fill="#666" fontSize="10">
            S{r.week}
          </text>
        ))}
      </svg>
    </div>
  );
}

// --- Mortality Pie Chart by death_reason_description ---

const PIE_COLORS = [
  '#d32f2f', '#1976d2', '#388e3c', '#f57c00', '#7b1fa2',
  '#00796b', '#c2185b', '#455a64', '#fbc02d', '#5d4037',
  '#0097a7', '#689f38', '#e64a19', '#512da8', '#afb42b',
];

interface PieSlice {
  label: string;
  count: number;
  pct: number;
}

function MortalityPieChart({ mortalities }: { mortalities: Mortality[] }) {
  const [hoveredSlice, setHoveredSlice] = useState<number | null>(null);

  if (mortalities.length === 0) return null;

  // Group by death_reason_description
  const countByReason: Record<string, number> = {};
  for (const m of mortalities) {
    const reason = m.death_reason_description || 'Não informado';
    countByReason[reason] = (countByReason[reason] || 0) + 1;
  }

  const total = mortalities.length;
  const slices: PieSlice[] = Object.entries(countByReason)
    .map(([label, count]) => ({ label, count, pct: (count / total) * 100 }))
    .sort((a, b) => b.count - a.count);

  const SIZE = 260;
  const CX = SIZE / 2;
  const CY = SIZE / 2;
  const R = 100;

  let startAngle = -Math.PI / 2;
  const arcs = slices.map((s, i) => {
    const angle = (s.count / total) * 2 * Math.PI;
    const endAngle = startAngle + angle;
    const largeArc = angle > Math.PI ? 1 : 0;
    const x1 = CX + R * Math.cos(startAngle);
    const y1 = CY + R * Math.sin(startAngle);
    const x2 = CX + R * Math.cos(endAngle);
    const y2 = CY + R * Math.sin(endAngle);
    const d = slices.length === 1
      ? `M ${CX} ${CY - R} A ${R} ${R} 0 1 1 ${CX - 0.01} ${CY - R} Z`
      : `M ${CX} ${CY} L ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    startAngle = endAngle;
    return { d, color: PIE_COLORS[i % PIE_COLORS.length], slice: s, index: i };
  });

  return (
    <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
      <h3 style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>Mortalidade por Causa</h3>
      <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <svg width={SIZE} height={SIZE} style={{ fontFamily: 'inherit', fontSize: '11px' }}>
          {arcs.map((a) => (
            <path
              key={a.index}
              d={a.d}
              fill={a.color}
              stroke="#fff"
              strokeWidth={1.5}
              opacity={hoveredSlice != null && hoveredSlice !== a.index ? 0.5 : 1}
              onMouseEnter={() => setHoveredSlice(a.index)}
              onMouseLeave={() => setHoveredSlice(null)}
              style={{ cursor: 'pointer', transition: 'opacity 0.15s' }}
            />
          ))}
          {/* Center label on hover */}
          {hoveredSlice != null && (
            <g>
              <text x={CX} y={CY - 6} textAnchor="middle" fill="#333" fontSize="12" fontWeight="bold">
                {slices[hoveredSlice].count}
              </text>
              <text x={CX} y={CY + 10} textAnchor="middle" fill="#666" fontSize="10">
                {formatNumber(slices[hoveredSlice].pct, 1)}%
              </text>
            </g>
          )}
        </svg>

        {/* Legend */}
        <div style={{ fontSize: '0.82rem', lineHeight: '1.8' }}>
          {slices.map((s, i) => (
            <div
              key={i}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', opacity: hoveredSlice != null && hoveredSlice !== i ? 0.5 : 1, transition: 'opacity 0.15s' }}
              onMouseEnter={() => setHoveredSlice(i)}
              onMouseLeave={() => setHoveredSlice(null)}
            >
              <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
              <span>{s.label} ({s.count} — {formatNumber(s.pct, 1)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function MortalityWeeklyView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const id = batchId ?? '';

  const fetchBatch = useCallback(() => getBatch(id), [id]);
  const fetchMortalities = useCallback(() => listMortalities(id), [id]);

  const { data: batch, loading: l1, error: e1, refetch: r1 } = useApi(fetchBatch);
  const { data: mortalities, loading: l2, error: e2, refetch: r2 } = useApi(fetchMortalities);

  const loading = l1 || l2;
  const error = e1 || e2;
  const refetchAll = () => { r1(); r2(); };

  const weeklyData = useMemo(
    () => (batch && mortalities ? computeWeeklyData(batch, mortalities) : []),
    [batch, mortalities],
  );

  const noStartSummary = batch != null && batch.total_animal_count == null;

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.mortalityWeekly') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.mortalityWeekly')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetchAll} />}

      {!loading && !error && noStartSummary && (
        <div className="alert alert-error" style={{ backgroundColor: '#fff3cd', borderColor: '#ffc107', color: '#856404' }}>
          {t('pigs.startSummaryRequired', 'O resumo inicial deve ser gerado antes de calcular a mortalidade semanal.')}
        </div>
      )}

      {!loading && !error && !noStartSummary && (
        <>
          <MortalityChart rows={weeklyData} />
          {mortalities && <MortalityPieChart mortalities={mortalities} />}

          <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('pigs.weekNumber', 'Semana')}</th>
                <th>{t('pigs.dateRange', 'Período')}</th>
                <th>{t('pigs.deathCount', 'Mortes')}</th>
                <th>{t('pigs.weeklyPct', '% Semanal')}</th>
                <th>{t('pigs.cumulativePct', '% Acumulada')}</th>
              </tr>
            </thead>
            <tbody>
              {weeklyData.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-empty">{t('common.noData')}</td>
                </tr>
              ) : (
                weeklyData.map((row) => (
                  <tr key={row.week}>
                    <td>{row.week}</td>
                    <td>{formatDate(row.startDate)} – {formatDate(row.endDate)}</td>
                    <td>{row.deathCount}</td>
                    <td>{formatNumber(row.weeklyPct, 2)}%</td>
                    <td>{formatNumber(row.cumulativePct, 2)}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          </div>
        </>
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
