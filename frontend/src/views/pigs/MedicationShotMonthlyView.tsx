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
      <h1 className="page-title">{t('pigs.medicationShots')}</h1>

      {/* Month selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <button type="button" className="btn btn-secondary" style={{ padding: '8px 14px' }} onClick={() => setMonth((m) => shiftMonth(m, -1))}>◀</button>
        <span style={{ fontSize: '1rem', fontWeight: 600, textTransform: 'capitalize' }}>{formatMonthLabel(month)}</span>
        <button type="button" className="btn btn-secondary" style={{ padding: '8px 14px' }} onClick={() => setMonth((m) => shiftMonth(m, 1))}>▶</button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && (
        medications.length === 0 ? (
          <div className="table-empty">{t('common.noData')}</div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ position: 'sticky', left: 0, zIndex: 2 }}>
                    {t('pigs.medicationName')}
                  </th>
                  {dayNumbers.map((d) => (
                    <th key={d} style={{ textAlign: 'center' }}>{d}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {medications.map((med) => (
                  <tr key={med}>
                    <td style={{ position: 'sticky', left: 0, zIndex: 1, backgroundColor: 'var(--surface)', fontWeight: 600 }}>
                      {med}
                    </td>
                    {dayNumbers.map((d) => {
                      const count = map[med]?.[d];
                      return (
                        <td key={d} style={{ textAlign: 'center' }}>
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

      <div style={{ marginTop: '1.5rem' }}>
        <button type="button" className="btn btn-outline" onClick={() => navigate(`/pigs/batches/${encodeURIComponent(id)}`)}>
          {t('common.back')}
        </button>
      </div>
    </Layout>
  );
}
