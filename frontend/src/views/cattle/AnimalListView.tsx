import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listCattleAnimals, listProcedures } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import ExportModal from '../../components/ExportModal';
import type { ExportColumnDef } from '../../utils/exportEngine';
import { formatTags, formatDate } from '../../utils/exportEngine';
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
  else statuses.push('Vazia');
  if (r.implanted) statuses.push('Implantada');
  if (r.inseminated) statuses.push('Inseminada');
  if (r.lactating) statuses.push('Lactante');
  if (r.transferred) statuses.push('Transferida');
  return statuses.join(', ');
}

export default function AnimalListView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState<string[]>([]);
  const [expandedNotes, setExpandedNotes] = useState<Set<string>>(new Set());
  const [exportOpen, setExportOpen] = useState(false);

  const fetchAnimals = useCallback(() => listCattleAnimals(), []);
  const fetchProcedures = useCallback(() => listProcedures(), []);
  const { data: animals, loading, error, refetch } = useApi(fetchAnimals);
  const { data: procedures } = useApi(fetchProcedures);

  const recentProcedures = useMemo(() => {
    return (procedures ?? []).slice(0, 3);
  }, [procedures]);

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

  const SEX_ALIASES: Record<string, string> = {
    macho: 'M',
    femea: 'F',
    fêmea: 'F',
  };

  const matchesFilter = useCallback((animal: CattleAnimal, filter: string): boolean => {
    const q = filter.toLowerCase();

    // Check sex aliases
    const sexValue = SEX_ALIASES[q];
    if (sexValue) {
      return (animal.sex ?? '').toUpperCase() === sexValue;
    }

    // General search across fields
    return (
      (animal.ear_tag ?? '').toLowerCase().includes(q) ||
      (animal.breed ?? '').toLowerCase().includes(q) ||
      (animal.tags ?? []).some((tag) => tag.toLowerCase().includes(q)) ||
      getReproductiveStatus(animal).toLowerCase().includes(q)
    );
  }, []);

  const displayAnimals = useMemo(() => {
    let result = activeAnimals;

    // Apply committed filters (AND logic)
    for (const filter of filters) {
      result = result.filter((a) => matchesFilter(a, filter));
    }

    // Apply live search (not yet committed)
    if (search.trim()) {
      const q = search.trim();
      result = result.filter((a) => matchesFilter(a, q));
    }

    return result;
  }, [activeAnimals, filters, search, matchesFilter]);

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && search.trim()) {
      e.preventDefault();
      const newFilter = search.trim();
      if (!filters.includes(newFilter.toLowerCase())) {
        setFilters((prev) => [...prev, newFilter]);
      }
      setSearch('');
    }
  };

  const removeFilter = (index: number) => {
    setFilters((prev) => prev.filter((_, i) => i !== index));
  };

  const getFilterLabel = (filter: string): string => {
    const q = filter.toLowerCase();
    const sexValue = SEX_ALIASES[q];
    if (sexValue) {
      return `Sexo: ${sexValue === 'M' ? 'Macho' : 'Fêmea'}`;
    }
    return filter;
  };

  const toggleNotes = (earTag: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedNotes((prev) => {
      const next = new Set(prev);
      if (next.has(earTag)) next.delete(earTag);
      else next.add(earTag);
      return next;
    });
  };

  const summary = useMemo(() => {
    const list = activeAnimals;
    let prenhe = 0, inseminada = 0, lactante = 0, vazia = 0;
    const tagCounts: Record<string, number> = {};

    for (const a of list) {
      const status = getReproductiveStatus(a);
      if (status.includes('Prenhe')) prenhe++;
      if (status.includes('Inseminada')) inseminada++;
      if (status.includes('Lactante')) lactante++;
      if (status === 'Vazia') vazia++;

      const lastTag = a.tags && a.tags.length > 0 ? a.tags[a.tags.length - 1] : '—';
      tagCounts[lastTag] = (tagCounts[lastTag] || 0) + 1;
    }

    const tagEntries = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
    return { total: list.length, prenhe, inseminada, lactante, vazia, tagEntries };
  }, [activeAnimals]);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle') },
  ];

  const exportColumns: ExportColumnDef[] = useMemo(() => [
    { key: 'ear_tag', label: 'Brinco', accessor: (row) => String(row.ear_tag ?? '') },
    { key: 'breed', label: 'Raça', accessor: (row) => String(row.breed ?? '—') },
    { key: 'sex', label: 'Sexo', accessor: (row) => String(row.sex ?? '—') },
    { key: 'age', label: 'Idade', accessor: (row) => computeAge(row.birth_date as string | undefined) },
    { key: 'status', label: 'Situação', accessor: (row) => getReproductiveStatus(row as unknown as CattleAnimal) },
    { key: 'tags', label: 'Tags', accessor: (row) => formatTags((row.tags as string[]) ?? [], 'excel') },
    { key: 'last_tag', label: 'Última Tag', accessor: (row) => { const tags = row.tags as string[] | undefined; return tags && tags.length > 0 ? tags[tags.length - 1] : '—'; } },
    { key: 'batch', label: 'Lote', accessor: (row) => String(row.batch ?? '—') },
    { key: 'last_weight', label: 'Último Peso', accessor: (row) => row.last_weight ? String(row.last_weight) : '—' },
    { key: 'last_weight_date', label: 'Dt Último Peso', accessor: (row) => row.last_weight_date ? formatDate(String(row.last_weight_date)) : '—' },
    { key: 'mother', label: 'Mãe', accessor: (row) => String(row.mother ?? '—') },
    { key: 'notes', label: 'Anotações', accessor: (row) => { const notes = row.notes as string[] | undefined; return notes ? notes.join('; ') : ''; } },
  ], []);

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">{t('cattle.animalList')}</h1>

      {/* Procedure section */}
      <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center', flexWrap: 'wrap', marginBottom: 'var(--space-md)' }}>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/cattle/procedures/new')}>
          {t('cattle.newProcedure', 'Novo Manejo')}
        </button>
        {recentProcedures.length > 0 && recentProcedures.map((proc) => {
          const procId = proc.pk.replace('Procedure|', '');
          const dateFormatted = proc.procedure_date ? `${proc.procedure_date.substring(8, 10)}/${proc.procedure_date.substring(5, 7)}` : '—';
          return (
            <button
              key={proc.pk}
              type="button"
              className="btn btn-outline"
              style={{ fontSize: '0.85rem' }}
              onClick={() => navigate(`/cattle/procedures/${encodeURIComponent(procId)}`)}
            >
              {dateFormatted} — {proc.status === 'confirmed' ? '✓' : '○'} ({proc.action_count ?? 0})
            </button>
          );
        })}
        <button type="button" className="btn btn-outline" style={{ fontSize: '0.85rem' }} onClick={() => navigate('/cattle/procedures')}>
          {t('cattle.viewAllProcedures', 'Ver Todos →')}
        </button>
      </div>

      {!loading && !error && (
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
            <input
              type="text"
              className="form-input"
              placeholder={t('common.search')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              style={{ flex: 1 }}
            />
            <button type="button" className="btn btn-primary" onClick={() => navigate('/cattle/new')}>
              {t('cattle.newAnimal', 'Novo Animal')}
            </button>
            <button type="button" className="btn btn-outline" onClick={() => setExportOpen(true)}>
              Exportar
            </button>
          </div>
          {filters.length > 0 && (
            <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap', marginTop: 'var(--space-xs)' }}>
              {filters.map((filter, index) => (
                <span
                  key={index}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '2px 8px',
                    backgroundColor: 'var(--primary)',
                    color: 'white',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                  }}
                >
                  {getFilterLabel(filter)}
                  <button
                    type="button"
                    onClick={() => removeFilter(index)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'white',
                      cursor: 'pointer',
                      padding: '0 2px',
                      fontSize: '1rem',
                      lineHeight: 1,
                    }}
                    aria-label={`Remove filter ${filter}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {!loading && !error && activeAnimals.length > 0 && (
        <div style={{
          display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap',
          marginBottom: 'var(--space-md)',
        }}>
          {/* Situation summary */}
          <div style={{
            flex: '1 1 200px', background: 'var(--surface)',
            border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)',
            padding: 'var(--space-sm) var(--space-md)', fontSize: '0.85rem',
          }}>
            <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)', color: 'var(--primary)' }}>
              {t('cattle.summary', 'Resumo')}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0 var(--space-md)' }}>
              <span>Total: <b>{displayAnimals.length}</b></span>
              <span>Prenhe: <b>{summary.prenhe}</b></span>
              <span>Inseminada: <b>{summary.inseminada}</b></span>
              <span>Lactante: <b>{summary.lactante}</b></span>
              <span>Vazia: <b>{summary.vazia}</b></span>
            </div>
          </div>

          {/* Tag group summary */}
          <div style={{
            flex: '1 1 200px', background: 'var(--surface)',
            border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)',
            padding: 'var(--space-sm) var(--space-md)', fontSize: '0.85rem',
          }}>
            <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)', color: 'var(--primary)' }}>
              {t('cattle.tagSummary', 'Por Última Tag')}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0 var(--space-md)' }}>
              {summary.tagEntries.map(([tag, count]) => (
                <span key={tag}>{tag}: <b>{count}</b></span>
              ))}
            </div>
          </div>
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
      <ExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        columns={exportColumns}
        data={displayAnimals as unknown as Record<string, unknown>[]}
        viewContext="animal-list"
      />
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
