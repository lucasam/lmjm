import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getProcedure, listCattleAnimals, confirmProcedure, cancelProcedure } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import ProcedureActionForm from '../../components/ProcedureActionForm';
import ProcedureSummary from '../../components/ProcedureSummary';
import type { CattleAnimal, ConfirmProcedureResult } from '../../types/models';

function getReproductiveStatus(r: CattleAnimal): string {
  const statuses: string[] = [];
  if (r.pregnant) statuses.push('Prenhe');
  if (r.implanted) statuses.push('Implantada');
  if (r.inseminated) statuses.push('Inseminada');
  if (r.lactating) statuses.push('Lactante');
  if (r.transferred) statuses.push('Transferida');
  return statuses.length > 0 ? statuses.join(', ') : 'Vazia';
}

export default function ProcedureDetailView() {
  const { t } = useTranslation();
  const { procedureId } = useParams<{ procedureId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [search, setSearch] = useState('');
  const [selectedEarTag, setSelectedEarTag] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmResult, setConfirmResult] = useState<ConfirmProcedureResult | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const fetchProcedure = useCallback(() => getProcedure(procedureId!), [procedureId]);
  const fetchAnimals = useCallback(() => listCattleAnimals(), []);

  const { data: procedureDetail, loading: loadingProcedure, error: errorProcedure, refetch: refetchProcedure } = useApi(fetchProcedure);
  const { data: animals, loading: loadingAnimals, error: errorAnimals, refetch: refetchAnimals } = useApi(fetchAnimals);

  const loading = loadingProcedure || loadingAnimals;
  const error = errorProcedure || errorAnimals;

  const isConfirmed = procedureDetail?.procedure.status === 'confirmed';
  const isCancelled = procedureDetail?.procedure.status === 'cancelled';
  const isLocked = isConfirmed || isCancelled;

  // Set of ear_tags that have been processed (appear in summary.animals)
  const processedEarTags = useMemo(() => {
    if (!procedureDetail?.summary?.animals) return new Set<string>();
    return new Set(procedureDetail.summary.animals.map((a) => a.ear_tag));
  }, [procedureDetail]);

  // Active animals sorted by ear_tag (numeric first)
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

  // Filter animals by search query
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

  const handleActionSuccess = () => {
    setSelectedEarTag(null);
    refetchProcedure();
  };

  const handleConfirm = async () => {
    setConfirming(true);
    setConfirmError(null);
    setConfirmResult(null);
    try {
      const result = await confirmProcedure(procedureId!);
      setConfirmResult(result);
      refetchProcedure();
    } catch (err) {
      setConfirmError(err instanceof Error ? err.message : String(err));
    } finally {
      setConfirming(false);
    }
  };

  const [cancelling, setCancelling] = useState(false);

  const handleCancel = async () => {
    if (!window.confirm(t('procedure.confirmCancel', 'Cancelar este manejo? Todas as ações serão removidas.'))) return;
    setCancelling(true);
    try {
      await cancelProcedure(procedureId!);
      navigate('/cattle');
    } catch (err) {
      setConfirmError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancelling(false);
    }
  };

  const procedureDate = procedureDetail?.procedure.procedure_date ?? '';

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: `${t('procedure.procedure', 'Manejo')} ${procedureDate}` },
  ];

  const refetch = () => {
    refetchProcedure();
    refetchAnimals();
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">
        {t('procedure.procedure', 'Manejo')} — {procedureDate}
        {isConfirmed && (
          <span style={{ marginLeft: 'var(--space-sm)', fontSize: '0.8em', color: 'var(--text-secondary)' }}>
            ✓ {t('procedure.confirmed', 'Confirmado')}
          </span>
        )}
        {isCancelled && (
          <span style={{ marginLeft: 'var(--space-sm)', fontSize: '0.8em', color: 'var(--error)' }}>
            ✗ {t('procedure.cancelled', 'Cancelado')}
          </span>
        )}
      </h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}

      {!loading && !error && procedureDetail && (
        <div style={{ display: 'flex', gap: 'var(--space-lg)', flexWrap: 'wrap', alignItems: 'flex-start' }}>
          {/* Left section: Animal list + action form */}
          <div style={{ flex: '1 1 400px', minWidth: 0 }}>
            {/* Search */}
            <div style={{ marginBottom: 'var(--space-md)' }}>
              <input
                type="text"
                className="form-input"
                placeholder={t('common.search')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* Animal table */}
            {displayAnimals.length === 0 && (
              <div className="table-empty">{t('common.noData')}</div>
            )}
            {displayAnimals.length > 0 && (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ width: '30px' }}></th>
                      <th>{t('cattle.earTag')}</th>
                      <th>{t('cattle.breed')}</th>
                      <th>{t('cattle.reproductiveStatus', 'Situação')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayAnimals.map((animal) => {
                      const tag = animal.ear_tag ?? '';
                      const isProcessed = processedEarTags.has(tag);
                      const isSelected = selectedEarTag === tag;

                      return (
                        <tr
                          key={tag}
                          className="table-row-clickable"
                          onClick={() => {
                            if (!isLocked) {
                              setSelectedEarTag(isSelected ? null : tag);
                            }
                          }}
                          tabIndex={0}
                          role="button"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !isLocked) {
                              setSelectedEarTag(isSelected ? null : tag);
                            }
                          }}
                          style={{
                            opacity: isProcessed ? 0.6 : 1,
                            background: isSelected ? 'var(--primary-light)' : undefined,
                          }}
                        >
                          <td style={{ textAlign: 'center', fontSize: '1.1rem' }}>
                            {isProcessed ? '✅' : '⬜'}
                          </td>
                          <td style={{ fontWeight: isSelected ? 600 : 400 }}>{tag}</td>
                          <td>{animal.breed ?? '—'}</td>
                          <td>{getReproductiveStatus(animal)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Action form for selected animal */}
            {selectedEarTag && !isLocked && (
              <div style={{ marginTop: 'var(--space-md)' }}>
                <ProcedureActionForm
                  procedureId={procedureId!}
                  earTag={selectedEarTag}
                  procedureDate={procedureDate}
                  onSuccess={handleActionSuccess}
                  disabled={isLocked}
                />
              </div>
            )}
          </div>

          {/* Right section: Summary + Confirm */}
          <div style={{ flex: '1 1 350px', minWidth: 0 }}>
            <h2 style={{ fontSize: '1.1rem', marginBottom: 'var(--space-md)' }}>
              {t('procedure.summaryTitle', 'Resumo do Manejo')}
            </h2>

            <ProcedureSummary
              procedureId={procedureId!}
              summary={procedureDetail.summary}
              totalActiveAnimals={activeAnimals.length}
              isConfirmed={isLocked}
              onRefresh={refetchProcedure}
            />

            {/* Confirm button */}
            {!isLocked && (
              <>
              <div style={{ marginTop: 'var(--space-md)', display: 'flex', gap: 'var(--space-sm)' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleConfirm}
                  disabled={confirming || cancelling || procedureDetail.summary.total_actions === 0}
                  style={{ flex: 1 }}
                >
                  {confirming
                    ? t('common.loading')
                    : t('procedure.confirm', 'Confirmar Manejo')}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCancel}
                  disabled={confirming || cancelling}
                  style={{ color: 'var(--error)' }}
                >
                  {cancelling
                    ? t('common.loading')
                    : t('procedure.cancel', 'Cancelar')}
                </button>
              </div>

              {confirmError && (
                <div className="alert alert-error" style={{ marginTop: 'var(--space-sm)' }}>
                  {confirmError}
                </div>
              )}
              </>
            )}

            {/* Confirmation result */}
            {confirmResult && (
              <div style={{
                marginTop: 'var(--space-md)',
                padding: 'var(--space-md)',
                background: 'var(--surface)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
              }}>
                <h3 style={{ fontSize: '1rem', marginBottom: 'var(--space-sm)', color: 'var(--primary)' }}>
                  {t('procedure.confirmResult', 'Resultado da Confirmação')}
                </h3>
                <div style={{ display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap', marginBottom: 'var(--space-sm)' }}>
                  <span>
                    ✓ {t('procedure.applied', 'Aplicados')}: <b>{confirmResult.applied_count}</b>
                  </span>
                  <span>
                    ✗ {t('procedure.failed', 'Falhas')}: <b>{confirmResult.failed_count}</b>
                  </span>
                </div>

                {confirmResult.failures && confirmResult.failures.length > 0 && (
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)', fontSize: '0.9rem' }}>
                      {t('procedure.failureDetails', 'Detalhes das Falhas')}:
                    </div>
                    <div className="table-wrapper">
                      <table className="table" style={{ fontSize: '0.85rem' }}>
                        <thead>
                          <tr>
                            <th>{t('cattle.earTag')}</th>
                            <th>{t('procedure.actionType', 'Tipo')}</th>
                            <th>{t('procedure.reason', 'Motivo')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {confirmResult.failures.map((f, i) => (
                            <tr key={i}>
                              <td>{f.ear_tag}</td>
                              <td>{f.action_type}</td>
                              <td>{f.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
