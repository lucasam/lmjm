import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listCattleAnimals } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type { CattleAnimal } from '../../types/models';

function computeAge(birthDate?: string): string {
  if (!birthDate) return '—';
  const [y, m, d] = birthDate.split('-').map(Number);
  const birth = new Date(y, m - 1, d);
  const now = new Date();
  let years = now.getFullYear() - birth.getFullYear();
  let months = now.getMonth() - birth.getMonth();
  if (now.getDate() < birth.getDate()) months--;
  if (months < 0) { years--; months += 12; }
  if (years > 0) return `${years}a ${months}m`;
  return `${months}m`;
}

function getReproductiveStatus(r: CattleAnimal): string {
  const statuses: string[] = [];
  if (r.pregnant) statuses.push('Prenhe');
  if (r.implanted) statuses.push('Implantada');
  if (r.inseminated) statuses.push('Inseminada');
  if (r.lactating) statuses.push('Lactante');
  if (r.transferred) statuses.push('Transferida');
  return statuses.length > 0 ? statuses.join(', ') : 'Vazia';
}

export default function AnimalListView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [search, setSearch] = useState('');
  const [expandedNotes, setExpandedNotes] = useState<Set<string>>(new Set());

  const fetchAnimals = useCallback(() => listCattleAnimals(), []);
  const { data: animals, loading, error, refetch } = useApi(fetchAnimals);

  const activeAnimals = useMemo(() => {
    const filtered = (animals ?? []).filter((a) => a.status === 'Ativa');
    return filtered.sort((a, b) => {
      const aNum = Number(a.ear_tag);
      const bNum = Number(b.ear_tag);
      const aIsNum = !isNaN(aNum);
      const bIsNum = !isNaN(bNum);
      if (aIsNum && bIsNum) return aNum - bNum;
      if (aIsNum) return -1;
      if (bIsNum) return 1;
      return (a.ear_tag ?? '').localeCompare(b.ear_tag ?? '');
    });
  }, [animals]);

  const displayAnimals = useMemo(() => {
    if (!search.trim()) return activeAnimals;
    const q = search.toLowerCase();
    return activeAnimals.filter((a) =>
      (a.ear_tag ?? '').toLowerCase().includes(q) ||
      (a.breed ?? '').toLowerCase().includes(q) ||
      (a.sex ?? '').toLowerCase().includes(q) ||
      (a.tags ?? []).some((tag) => tag.toLowerCase().includes(q)) ||
      getReproductiveStatus(a).toLowerCase().includes(q)
    );
  }, [activeAnimals, search]);

  const toggleNotes = (earTag: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedNotes((prev) => {
      const next = new Set(prev);
      if (next.has(earTag)) next.delete(earTag);
      else next.add(earTag);
      return next;
    });
  };

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle') },
  ];

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">{t('cattle.animalList')}</h1>

      {!loading && !error && (
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <input
            type="text"
            className="form-input"
            placeholder={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}
      {!loading && !error && displayAnimals.length === 0 && (
        <div className="table-empty">{t('common.noData')}</div>
      )}
      {!loading && !error && displayAnimals.length > 0 && (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('cattle.earTag')}</th>
                <th>{t('cattle.breed')}</th>
                <th>{t('cattle.sex')}</th>
                <th>{t('cattle.age', 'Idade')}</th>
                <th>{t('cattle.reproductiveStatus', 'Situação')}</th>
                <th>{t('cattle.tags')}</th>
                <th>{t('cattle.notes')}</th>
              </tr>
            </thead>
            <tbody>
              {displayAnimals.map((animal) => {
                const tag = animal.ear_tag ?? '';
                const hasNotes = animal.notes && animal.notes.length > 0;
                const isExpanded = expandedNotes.has(tag);

                return (
                  <AnimalRow
                    key={tag}
                    animal={animal}
                    hasNotes={!!hasNotes}
                    isExpanded={isExpanded}
                    onRowClick={() => navigate(`/cattle/${encodeURIComponent(tag)}`)}
                    onToggleNotes={(e) => toggleNotes(tag, e)}
                    t={t}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}

function AnimalRow({ animal, hasNotes, isExpanded, onRowClick, onToggleNotes, t }: {
  animal: CattleAnimal;
  hasNotes: boolean;
  isExpanded: boolean;
  onRowClick: () => void;
  onToggleNotes: (e: React.MouseEvent) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  t: any;
}) {
  return (
    <>
      <tr
        className="table-row-clickable"
        onClick={onRowClick}
        tabIndex={0}
        role="button"
        onKeyDown={(e) => { if (e.key === 'Enter') onRowClick(); }}
      >
        <td>{animal.ear_tag}</td>
        <td>{animal.breed ?? '—'}</td>
        <td>{animal.sex ?? '—'}</td>
        <td>{computeAge(animal.birth_date)}</td>
        <td>{getReproductiveStatus(animal)}</td>
        <td style={{ whiteSpace: 'normal', maxWidth: '150px' }}>{animal.tags ? [...animal.tags].reverse().join(', ') : '—'}</td>
        <td>
          {hasNotes ? (
            <button
              type="button"
              onClick={onToggleNotes}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '1rem',
                padding: '4px 8px',
                minWidth: '44px',
                minHeight: '44px',
                borderRadius: 'var(--radius-sm)',
                transition: 'background-color 0.15s',
              }}
              aria-label={t('cattle.notes')}
            >
              {isExpanded ? '📝 ▲' : `📝 ${animal.notes!.length}`}
            </button>
          ) : '—'}
        </td>
      </tr>
      {isExpanded && hasNotes && (
        <tr>
          <td colSpan={7} style={{ padding: 0 }}>
            <div style={{
              backgroundColor: 'var(--primary-light)',
              padding: 'var(--space-sm) var(--space-md)',
              borderLeft: '3px solid var(--primary)',
              fontSize: '0.85rem',
              lineHeight: '1.6',
            }}>
              {animal.notes!.map((note, i) => (
                <div key={i} style={{
                  padding: '4px 0',
                  borderBottom: i < animal.notes!.length - 1 ? '1px solid var(--border-light)' : 'none',
                }}>
                  {note}
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
