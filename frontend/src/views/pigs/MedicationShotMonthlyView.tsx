import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listMedicationShots } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type { MedicationShot } from '../../types/models';

function getCurrentMonth(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

function getDaysInMonth(month: string): number {
  const [y, m] = month.split('-').map(Number);
  return new Date(y, m, 0).getDate();
}

function formatMonthLabel(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const date = new Date(y, m - 1, 1);
  return date.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
}

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  const ny = d.getFullYear();
  const nm = String(d.getMonth() + 1).padStart(2, '0');
  return `${ny}-${nm}`;
}

interface ShotMap {
  [medicationName: string]: { [day: number]: number };
}

function buildShotMap(shots: MedicationShot[], month: string): { map: ShotMap; medications: string[] } {
  const map: ShotMap = {};
  const medSet = new Set<string>();
  for (const s of shots) {
    const shotDate = s.date;
    if (!shotDate.startsWith(month)) continue;
    const day = parseInt(shotDate.substring(8, 10), 10);
    medSet.add(s.medication_name);
    if (!map[s.medication_name]) map[s.medication_name] = {};
    map[s.medication_name][day] = (map[s.medication_name][day] || 0) + s.shot_count;
  }
  return { map, medications: Array.from(medSet).sort() };
}

export default function MedicationShotMonthlyView() {
  const { t } = useTranslation();
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [month, setMonth] = useState(getCurrentMonth);

  const id = batchId ?? '';

  const fetchShots = useCallback(
    () => listMedicationShots(id, month),
    [id, month],
  );

  const { data: shots, loading, error, refetch } = useApi(fetchShots);

  const daysInMonth = useMemo(() => getDaysInMonth(month), [month]);
  const dayNumbers = useMemo(() => Array.from({ length: daysInMonth }, (_, i) => i + 1), [daysInMonth]);

  const { map, medications } = useMemo(
    () => buildShotMap(shots ?? [], month),
    [shots, month],
  );

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.batchDetail'), to: `/pigs/batches/${encodeURIComponent(id)}` },
    { label: t('pigs.medicationShots') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 style={titleStyle}>{t('pigs.medicationShots')}</h1>

      {/* Month selector */}
      <div style={monthNav}>
        <button type="button" style={navBtn} onClick={() => setMonth((m) => shiftMonth(m, -1))}>◀</button>
        <span style={monthLabel}>{formatMonthLabel(month)}</span>
        <button type="button" style={navBtn} onClick={() => setMonth((m) => shiftMonth(m, 1))}>▶</button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        medications.length === 0 ? (
          <div style={emptyStyle}>{t('common.noData')}</div>
        ) : (
          <div style={tableWrapper}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={{ ...thStyle, position: 'sticky', left: 0, zIndex: 2, backgroundColor: '#f5f5f5' }}>
                    {t('pigs.medicationName')}
                  </th>
                  {dayNumbers.map((d) => (
                    <th key={d} style={thStyle}>{d}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {medications.map((med) => (
                  <tr key={med}>
                    <td style={{ ...tdStyle, position: 'sticky', left: 0, zIndex: 1, backgroundColor: '#fff', fontWeight: 600 }}>
                      {med}
                    </td>
                    {dayNumbers.map((d) => {
                      const count = map[med]?.[d];
                      return (
                        <td key={d} style={{ ...tdStyle, textAlign: 'center' }}>
                          {count != null ? count : ''}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      <div style={backBar}>
        <button type="button" style={backBtn} onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const monthNav: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' };
const navBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', border: '1px solid #ccc', borderRadius: '6px',
  background: '#fff', cursor: 'pointer', fontSize: '1rem',
};
const monthLabel: React.CSSProperties = { fontSize: '1rem', fontWeight: 600, textTransform: 'capitalize' };
const tableWrapper: React.CSSProperties = { overflowX: 'auto', WebkitOverflowScrolling: 'touch', width: '100%' };
const tableStyle: React.CSSProperties = { borderCollapse: 'collapse', fontSize: '0.85rem', minWidth: '100%' };
const thStyle: React.CSSProperties = {
  padding: '0.5rem 0.4rem', borderBottom: '2px solid #ddd', whiteSpace: 'nowrap',
  fontWeight: 600, backgroundColor: '#f5f5f5', textAlign: 'center',
};
const tdStyle: React.CSSProperties = { padding: '0.5rem 0.4rem', borderBottom: '1px solid #eee', whiteSpace: 'nowrap' };
const emptyStyle: React.CSSProperties = { padding: '2rem', textAlign: 'center', color: '#888' };
const backBar: React.CSSProperties = { marginTop: '1.5rem' };
const backBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#e3f2fd', color: '#1976d2', border: '1px solid #1976d2', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
