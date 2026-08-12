import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getCattleAnimal, createCattleAnimal, updateCattleAnimal, type AnimalPayload } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';

const BOOLEAN_FIELDS = ['pregnant', 'implanted', 'inseminated', 'lactating', 'transferred'] as const;
type BooleanField = (typeof BOOLEAN_FIELDS)[number];

// Mirrors the backend AnimalStatus enum (value == name).
const ANIMAL_STATUSES = ['Ativa', 'Vendida', 'Morto', 'Baixa'] as const;

export default function AnimalFormView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { earTag } = useParams<{ earTag: string }>();
  const { user, logout } = useAuth();

  const isEdit = !!earTag;
  const currentTag = earTag ?? '';

  const [tag, setTag] = useState('');
  const [breed, setBreed] = useState('');
  const [sex, setSex] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [mother, setMother] = useState('');
  const [batch, setBatch] = useState('');
  const [status, setStatus] = useState(isEdit ? '' : 'Ativa');
  const [flags, setFlags] = useState<Record<BooleanField, boolean>>({
    pregnant: false,
    implanted: false,
    inseminated: false,
    lactating: false,
    transferred: false,
  });
  const [tagsInput, setTagsInput] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnimal = useCallback(
    () => (isEdit ? getCattleAnimal(currentTag) : Promise.resolve(null)),
    [isEdit, currentTag],
  );
  const { data: animal, loading, error: loadError } = useApi(fetchAnimal);

  // Prefill the form once the animal loads in edit mode.
  useEffect(() => {
    if (!animal) return;
    setTag(animal.ear_tag ?? '');
    setBreed(animal.breed ?? '');
    setSex(animal.sex ?? '');
    setBirthDate(animal.birth_date ?? '');
    setMother(animal.mother ?? '');
    setBatch(animal.batch ?? '');
    setStatus(animal.status ?? '');
    setFlags({
      pregnant: !!animal.pregnant,
      implanted: !!animal.implanted,
      inseminated: !!animal.inseminated,
      lactating: !!animal.lactating,
      transferred: !!animal.transferred,
    });
    setTagsInput((animal.tags ?? []).join(', '));
  }, [animal]);

  const orNull = (value: string): string | null => {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const tagsArray = tagsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: AnimalPayload = {
      breed: orNull(breed),
      sex: orNull(sex),
      birth_date: orNull(birthDate),
      mother: orNull(mother),
      batch: orNull(batch),
      status: orNull(status),
      pregnant: flags.pregnant,
      implanted: flags.implanted,
      inseminated: flags.inseminated,
      lactating: flags.lactating,
      transferred: flags.transferred,
      tags: tagsArray.length > 0 ? tagsArray : null,
    };

    setSubmitting(true);
    try {
      if (isEdit) {
        await updateCattleAnimal(currentTag, payload);
        navigate(`/cattle/${encodeURIComponent(currentTag)}`);
      } else {
        const newTag = tag.trim();
        if (!newTag) {
          setError(t('cattle.earTagRequired', 'O número do brinco é obrigatório'));
          setSubmitting(false);
          return;
        }
        const created = await createCattleAnimal({ ...payload, ear_tag: newTag });
        navigate(`/cattle/${encodeURIComponent(created.ear_tag ?? newTag)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  const title = isEdit
    ? t('cattle.editAnimal', 'Editar Animal')
    : t('cattle.newAnimal', 'Novo Animal');

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: isEdit ? currentTag : title },
  ];

  const cancelTo = isEdit ? `/cattle/${encodeURIComponent(currentTag)}` : '/cattle';

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{title}</h1>

      {isEdit && loading && <LoadingSpinner />}
      {isEdit && loadError && <ErrorMessage message={loadError} />}
      {error && <div className="alert alert-error">{error}</div>}

      {(!isEdit || (!loading && !loadError)) && (
        <form onSubmit={handleSubmit} style={{ maxWidth: '480px' }}>
          <label className="form-label">
            {t('cattle.earTag')} *
            {isEdit ? (
              <input type="text" value={tag} disabled className="form-input" />
            ) : (
              <input
                type="text"
                required
                autoFocus
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                className="form-input"
              />
            )}
          </label>
          {isEdit && (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '-0.5rem' }}>
              {t('cattle.earTagEditHint', 'Use "Alterar Número do Brinco" na tela de detalhes para renomear.')}
            </p>
          )}

          <label className="form-label">
            {t('cattle.breed')}
            <input type="text" value={breed} onChange={(e) => setBreed(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.sex')}
            <select value={sex} onChange={(e) => setSex(e.target.value)} className="form-input">
              <option value="">—</option>
              <option value="F">{t('cattle.female', 'Fêmea')}</option>
              <option value="M">{t('cattle.male', 'Macho')}</option>
            </select>
          </label>

          <label className="form-label">
            {t('cattle.birthDate')}
            <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.mother')}
            <input type="text" value={mother} onChange={(e) => setMother(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.batch')}
            <input type="text" value={batch} onChange={(e) => setBatch(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.status')}
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="form-input">
              <option value="">—</option>
              {/* Preserve an unexpected legacy value so editing doesn't silently drop it. */}
              {status !== '' && !ANIMAL_STATUSES.includes(status as (typeof ANIMAL_STATUSES)[number]) && (
                <option value={status}>{status}</option>
              )}
              {ANIMAL_STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>

          <fieldset style={{ border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: 'var(--space-sm) var(--space-md)', marginTop: 'var(--space-sm)' }}>
            <legend style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {t('cattle.reproductiveStatus', 'Situação')}
            </legend>
            {BOOLEAN_FIELDS.map((field) => (
              <label key={field} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', padding: '2px 0' }}>
                <input
                  type="checkbox"
                  checked={flags[field]}
                  onChange={(e) => setFlags((prev) => ({ ...prev, [field]: e.target.checked }))}
                />
                {t(`cattle.${field}`)}
              </label>
            ))}
          </fieldset>

          <label className="form-label">
            {t('cattle.tags')}
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              className="form-input"
              placeholder={t('cattle.tagsHint', 'Separe por vírgula')}
            />
          </label>

          <div style={{ marginTop: 'var(--space-md)', display: 'flex', gap: 'var(--space-sm)' }}>
            <button type="button" className="btn btn-secondary" onClick={() => navigate(cancelTo)}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? t('common.loading') : isEdit ? t('common.save') : t('common.create')}
            </button>
          </div>
        </form>
      )}
    </Layout>
  );
}
