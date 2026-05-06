import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { deleteProcedureAction } from '../api/client';
import type { ProcedureSummary as ProcedureSummaryType, ProcedureAction, ProcedureActionType } from '../types/models';

interface ProcedureSummaryProps {
  procedureId: string;
  summary: ProcedureSummaryType;
  totalActiveAnimals: number;
  isConfirmed: boolean;
  onRefresh: () => void;
}

const actionTypeLabel = (type: ProcedureActionType, t: (key: string, fallback: string) => string): string => {
  switch (type) {
    case 'weight': return t('procedure.actionWeight', 'Pesagem');
    case 'insemination': return t('procedure.actionInsemination', 'Inseminação');
    case 'diagnostic': return t('procedure.actionDiagnostic', 'Diagnóstico');
    case 'observation': return t('procedure.actionObservation', 'Observação');
    case 'inspected': return t('procedure.actionInspected', 'Inspecionado');
    case 'implant': return t('procedure.actionImplant', 'Implante');
  }
};

function actionDetail(action: ProcedureAction): string {
  switch (action.action_type) {
    case 'weight':
      return `${action.weight_kg ?? '—'} kg — ${action.weighing_date ?? ''}`;
    case 'insemination':
      return `${action.semen ?? '—'} — ${action.insemination_date ?? ''}`;
    case 'diagnostic':
      return `${action.pregnant ? '✓ Prenhe' : '✗ Vazia'} — ${action.diagnostic_date ?? ''}`;
    case 'observation':
      return action.note ?? '—';
    case 'inspected':
      return '';
    case 'implant':
      return '';
  }
}

export default function ProcedureSummary({
  procedureId,
  summary,
  totalActiveAnimals,
  isConfirmed,
  onRefresh,
}: ProcedureSummaryProps) {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [deletingAction, setDeletingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filteredAnimals = summary.animals.filter((animal) =>
    animal.ear_tag.toLowerCase().includes(search.toLowerCase()),
  );

  const handleDelete = async (actionSk: string) => {
    setDeletingAction(actionSk);
    setError(null);
    try {
      await deleteProcedureAction(procedureId, actionSk);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingAction(null);
    }
  };

  return (
    <div>
      {/* Action counts */}
      <div style={{
        display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap',
        marginBottom: 'var(--space-md)',
      }}>
        <div style={{
          flex: '1 1 300px', background: 'var(--surface)',
          border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)',
          padding: 'var(--space-sm) var(--space-md)', fontSize: '0.85rem',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)', color: 'var(--primary)' }}>
            {t('procedure.summaryTitle', 'Resumo do Manejo')}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0 var(--space-md)' }}>
            <span>{t('procedure.actionWeight', 'Pesagem')}: <b>{summary.weight_count}</b></span>
            <span>{t('procedure.actionInsemination', 'Inseminação')}: <b>{summary.insemination_count}</b></span>
            <span>{t('procedure.actionDiagnostic', 'Diagnóstico')}: <b>{summary.diagnostic_count}</b></span>
            <span style={{ color: 'green' }}>✓ {t('procedure.confirmed', 'Confirmado')}: <b>{summary.diagnostic_confirmed}</b></span>
            <span style={{ color: '#e65100' }}>✗ {t('procedure.failed', 'Falha')}: <b>{summary.diagnostic_failed}</b></span>
            <span>{t('procedure.actionObservation', 'Observação')}: <b>{summary.observation_count}</b></span>
            <span>{t('procedure.actionInspected', 'Inspecionado')}: <b>{summary.inspected_count}</b></span>
            <span>{t('procedure.actionImplant', 'Implante')}: <b>{summary.implant_count}</b></span>
            <span>Total: <b>{summary.total_actions}</b></span>
          </div>
        </div>

        <div style={{
          flex: '0 0 auto', background: 'var(--surface)',
          border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)',
          padding: 'var(--space-sm) var(--space-md)', fontSize: '0.85rem',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)', color: 'var(--primary)' }}>
            {t('procedure.processedAnimals', 'Animais Processados')}
          </div>
          <div>
            <b>{summary.processed_animal_count}</b> / {totalActiveAnimals}
          </div>
        </div>

        {summary.prenhez_total > 0 && (
          <div style={{
            flex: '0 0 auto', background: 'var(--surface)',
            border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)',
            padding: 'var(--space-sm) var(--space-md)', fontSize: '0.85rem',
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
          }}>
            <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)', color: 'var(--primary)' }}>
              {t('procedure.pregnancyRate', 'Taxa de Prenhez (Inseminadas)')}
            </div>
            <div>
              <b>{summary.prenhez_rate ?? 0}%</b>
              <span style={{ color: 'var(--text-secondary)', marginLeft: 'var(--space-sm)' }}>
                ({summary.prenhez_confirmed} / {summary.prenhez_total})
              </span>
            </div>
          </div>
        )}
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 'var(--space-sm)' }}>{error}</div>}

      {/* Search filter */}
      <div style={{ marginBottom: 'var(--space-sm)' }}>
        <input
          type="text"
          className="form-input"
          placeholder={t('procedure.searchByEarTag', 'Buscar por brinco...')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Actions grouped by animal */}
      {filteredAnimals.length === 0 && (
        <div className="table-empty">{t('common.noData')}</div>
      )}

      {filteredAnimals.map((animal) => (
        <div
          key={animal.ear_tag}
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-sm) var(--space-md)',
            marginBottom: 'var(--space-sm)',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 'var(--space-xs)' }}>
            🐄 {animal.ear_tag}
            <span style={{ fontWeight: 400, color: 'var(--text-secondary)', marginLeft: 'var(--space-sm)', fontSize: '0.85rem' }}>
              ({animal.actions.length} {animal.actions.length === 1
                ? t('procedure.action', 'ação')
                : t('procedure.actions', 'ações')})
            </span>
          </div>

          <div className="table-wrapper">
            <table className="table" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th>{t('procedure.actionType', 'Tipo')}</th>
                  <th>{t('procedure.detail', 'Detalhe')}</th>
                  {!isConfirmed && <th style={{ width: '60px' }}></th>}
                </tr>
              </thead>
              <tbody>
                {animal.actions.map((action: ProcedureAction) => (
                  <tr key={action.sk}>
                    <td>{actionTypeLabel(action.action_type, t)}</td>
                    <td>{actionDetail(action)}</td>
                    {!isConfirmed && (
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: '2px 8px', fontSize: '0.8rem', minWidth: '44px', minHeight: '44px' }}
                          disabled={deletingAction === action.sk}
                          onClick={() => handleDelete(action.sk)}
                          aria-label={t('common.delete', 'Excluir')}
                        >
                          {deletingAction === action.sk ? '…' : '✕'}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
