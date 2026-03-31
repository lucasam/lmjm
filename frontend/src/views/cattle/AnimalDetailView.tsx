import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getCattleAnimal, listInseminations, listDiagnostics } from '../../api/client';
import { formatDate } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import DataTable, { type Column } from '../../components/DataTable';
import InseminationForm from './InseminationForm';
import DiagnosticForm from './DiagnosticForm';
import type { Insemination, Diagnostic } from '../../types/models';

export default function AnimalDetailView() {
  const { t } = useTranslation();
  const { earTag } = useParams<{ earTag: string }>();
  const { user, logout } = useAuth();
  const [showInseminationForm, setShowInseminationForm] = useState(false);
  const [showDiagnosticForm, setShowDiagnosticForm] = useState(false);

  const tag = earTag ?? '';

  const fetchAnimal = useCallback(() => getCattleAnimal(tag), [tag]);
  const fetchInseminations = useCallback(() => listInseminations(tag), [tag]);
  const fetchDiagnostics = useCallback(() => listDiagnostics(tag), [tag]);

  const { data: animal, loading: loadingAnimal, error: errorAnimal, refetch: refetchAnimal } = useApi(fetchAnimal);
  const { data: inseminations, loading: loadingInsem, error: errorInsem, refetch: refetchInsem } = useApi(fetchInseminations);
  const { data: diagnostics, loading: loadingDiag, error: errorDiag, refetch: refetchDiag } = useApi(fetchDiagnostics);

  const loading = loadingAnimal || loadingInsem || loadingDiag;
  const error = errorAnimal || errorInsem || errorDiag;

  const inseminationCols: Column<Insemination>[] = [
    { header: t('cattle.inseminationDate'), accessor: (r) => formatDate(r.insemination_date) },
    { header: t('cattle.semen'), accessor: (r) => r.semen },
  ];

  const diagnosticCols: Column<Diagnostic>[] = [
    { header: t('cattle.diagnosticDate'), accessor: (r) => formatDate(r.diagnostic_date) },
    { header: t('cattle.pregnant'), accessor: (r) => (r.pregnant ? t('common.yes') : t('common.no')) },
    { header: t('cattle.expectedDeliveryDate'), accessor: (r) => r.expected_delivery_date ? formatDate(r.expected_delivery_date) : '—' },
    { header: t('cattle.semen'), accessor: (r) => r.semen ?? '—' },
  ];

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: tag },
  ];

  const handleInseminationSuccess = () => {
    setShowInseminationForm(false);
    refetchInsem();
    refetchAnimal();
  };

  const handleDiagnosticSuccess = () => {
    setShowDiagnosticForm(false);
    refetchDiag();
    refetchAnimal();
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 style={titleStyle}>{t('cattle.animalDetail')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={() => { refetchAnimal(); refetchInsem(); refetchDiag(); }} />}

      {!loading && !error && animal && (
        <>
          {/* Animal fields */}
          <div style={detailGrid}>
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
            <DetailRow label={t('cattle.notes')} value={animal.notes?.join('; ')} />
          </div>

          {/* Action buttons */}
          <div style={actionBar}>
            <button type="button" style={actionBtn} onClick={() => setShowInseminationForm(true)}>
              {t('cattle.newInsemination')}
            </button>
            <button type="button" style={actionBtn} onClick={() => setShowDiagnosticForm(true)}>
              {t('cattle.newDiagnostic')}
            </button>
          </div>

          {/* Insemination history */}
          <h2 style={sectionTitle}>{t('cattle.inseminations')}</h2>
          <DataTable
            columns={inseminationCols}
            data={inseminations ?? []}
            keyExtractor={(_, i) => String(i)}
          />

          {/* Diagnostic history */}
          <h2 style={sectionTitle}>{t('cattle.diagnostics')}</h2>
          <DataTable
            columns={diagnosticCols}
            data={diagnostics ?? []}
            keyExtractor={(_, i) => String(i)}
          />
        </>
      )}

      {/* Modals */}
      {showInseminationForm && (
        <InseminationForm
          earTag={tag}
          onClose={() => setShowInseminationForm(false)}
          onSuccess={handleInseminationSuccess}
        />
      )}
      {showDiagnosticForm && (
        <DiagnosticForm
          earTag={tag}
          onClose={() => setShowDiagnosticForm(false)}
          onSuccess={handleDiagnosticSuccess}
        />
      )}
    </Layout>
  );
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  return (
    <div style={detailRow}>
      <span style={detailLabel}>{label}</span>
      <span style={detailValue}>{value ?? '—'}</span>
    </div>
  );
}

const titleStyle: React.CSSProperties = { fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' };
const detailGrid: React.CSSProperties = { marginBottom: '1.5rem' };
const detailRow: React.CSSProperties = { display: 'flex', padding: '0.4rem 0', borderBottom: '1px solid #eee', gap: '0.5rem' };
const detailLabel: React.CSSProperties = { fontWeight: 600, minWidth: '140px', color: '#555' };
const detailValue: React.CSSProperties = { color: '#222' };
const actionBar: React.CSSProperties = { display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' };
const actionBtn: React.CSSProperties = {
  minWidth: '44px', minHeight: '44px', padding: '10px 18px',
  backgroundColor: '#1976d2', color: '#fff', border: 'none', borderRadius: '6px',
  cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
};
const sectionTitle: React.CSSProperties = { fontSize: '1.1rem', fontWeight: 600, margin: '1.5rem 0 0.75rem' };
