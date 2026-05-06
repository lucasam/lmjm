import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postProcedureAction } from '../api/client';
import type { ProcedureActionType } from '../types/models';

interface ProcedureActionFormProps {
  procedureId: string;
  earTag: string;
  procedureDate: string; // YYYY-MM-DD
  onSuccess: () => void;
  disabled: boolean;
}

const ACTION_TYPES: ProcedureActionType[] = ['weight', 'insemination', 'diagnostic', 'observation', 'implant', 'inspected'];

export default function ProcedureActionForm({ procedureId, earTag, procedureDate, onSuccess, disabled }: ProcedureActionFormProps) {
  const { t } = useTranslation();

  const [actionType, setActionType] = useState<ProcedureActionType>('weight');

  // Weight fields
  const [weightKg, setWeightKg] = useState('');

  // Insemination fields
  const [semen, setSemen] = useState('');
  const [inseminationNote, setInseminationNote] = useState('');

  // Diagnostic fields
  const [pregnant, setPregnant] = useState(true);
  const [diagnosticNote, setDiagnosticNote] = useState('');
  const [tags, setTags] = useState('');

  // Observation fields
  const [observationNote, setObservationNote] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const resetFields = () => {
    setWeightKg('');
    setSemen('');
    setInseminationNote('');
    setPregnant(true);
    setDiagnosticNote('');
    setTags('');
    setObservationNote('');
    setError(null);
    setSuccess(false);
  };

  const buildPayload = (): Record<string, unknown> => {
    const base: Record<string, unknown> = { action_type: actionType, ear_tag: earTag };
    const dateForApi = procedureDate.replace(/-/g, '');

    switch (actionType) {
      case 'weight':
        return { ...base, weighing_date: dateForApi, weight_kg: Number(weightKg) };
      case 'insemination':
        return {
          ...base,
          insemination_date: dateForApi,
          semen,
          ...(inseminationNote.trim() ? { note: inseminationNote.trim() } : {}),
        };
      case 'diagnostic':
        return {
          ...base,
          diagnostic_date: dateForApi,
          pregnant,
          ...(diagnosticNote.trim() ? { note: diagnosticNote.trim() } : {}),
          ...(tags.trim() ? { tags: tags.trim() } : {}),
        };
      case 'observation':
        return { ...base, note: observationNote.trim() };
      case 'inspected':
        return base;
      case 'implant':
        return base;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(false);
    try {
      await postProcedureAction(procedureId, buildPayload());
      setSuccess(true);
      resetFields();
      setTimeout(() => {
        setSuccess(false);
        onSuccess();
      }, 600);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const actionTypeLabel = (type: ProcedureActionType): string => {
    switch (type) {
      case 'weight': return t('procedure.actionWeight', 'Pesagem');
      case 'insemination': return t('procedure.actionInsemination', 'Inseminação');
      case 'diagnostic': return t('procedure.actionDiagnostic', 'Diagnóstico');
      case 'observation': return t('procedure.actionObservation', 'Observação');
      case 'inspected': return t('procedure.actionInspected', 'Inspecionado');
      case 'implant': return t('procedure.actionImplant', 'Implante');
    }
  };

  return (
    <div style={{ padding: 'var(--space-md)', background: 'var(--surface)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)' }}>
      <h3 style={{ margin: '0 0 var(--space-sm) 0', fontSize: '1rem' }}>
        {t('procedure.newAction', 'Nova Ação')} — {earTag}
      </h3>

      {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <label className="form-label">
          {t('procedure.actionType', 'Tipo de Ação')} *
          <select
            required
            value={actionType}
            onChange={(e) => { setActionType(e.target.value as ProcedureActionType); setError(null); }}
            className="form-input"
            disabled={disabled}
          >
            {ACTION_TYPES.map((type) => (
              <option key={type} value={type}>{actionTypeLabel(type)}</option>
            ))}
          </select>
        </label>

        {actionType === 'weight' && (
          <>
            <label className="form-label">
              {t('cattle.weight')} *
              <input
                type="number"
                required
                min={1}
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                className="form-input"
                disabled={disabled}
              />
            </label>
          </>
        )}

        {actionType === 'insemination' && (
          <>
            <label className="form-label">
              {t('cattle.semen')} *
              <input
                type="text"
                required
                value={semen}
                onChange={(e) => setSemen(e.target.value)}
                className="form-input"
                disabled={disabled}
              />
            </label>
            <label className="form-label">
              {t('cattle.notes')}
              <input
                type="text"
                value={inseminationNote}
                onChange={(e) => setInseminationNote(e.target.value)}
                className="form-input"
                disabled={disabled}
              />
            </label>
          </>
        )}

        {actionType === 'diagnostic' && (
          <>
            <label className="form-label">
              {t('cattle.pregnant', 'Prenhe')} *
              <select
                required
                value={String(pregnant)}
                onChange={(e) => setPregnant(e.target.value === 'true')}
                className="form-input"
                disabled={disabled}
              >
                <option value="true">{t('common.yes', 'Sim')}</option>
                <option value="false">{t('common.no', 'Não')}</option>
              </select>
            </label>
            <label className="form-label">
              {t('cattle.notes')}
              <input
                type="text"
                value={diagnosticNote}
                onChange={(e) => setDiagnosticNote(e.target.value)}
                className="form-input"
                disabled={disabled}
              />
            </label>
            <label className="form-label">
              {t('cattle.tags', 'Tags')}
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="form-input"
                disabled={disabled}
              />
            </label>
          </>
        )}

        {actionType === 'observation' && (
          <label className="form-label">
            {t('cattle.notes')} *
            <input
              type="text"
              required
              value={observationNote}
              onChange={(e) => setObservationNote(e.target.value)}
              className="form-input"
              disabled={disabled}
            />
          </label>
        )}

        {actionType === 'inspected' && (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 'var(--space-sm) 0' }}>
            {t('procedure.inspectedHint', 'Animal será marcado como inspecionado, sem alterações.')}
          </p>
        )}

        {actionType === 'implant' && (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 'var(--space-sm) 0' }}>
            {t('procedure.implantHint', 'Animal será marcado como implantado.')}
          </p>
        )}

        <div style={{ marginTop: 'var(--space-sm)', display: 'flex', gap: 'var(--space-sm)' }}>
          <button type="submit" className="btn btn-primary" disabled={submitting || disabled}>
            {submitting ? t('common.loading') : t('common.submit')}
          </button>
        </div>
      </form>
    </div>
  );
}
