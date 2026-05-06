import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { createProcedure } from '../../api/client';
import Layout from '../../components/Layout';

function todayISO(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export default function ProcedureCreateView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [procedureDate, setProcedureDate] = useState(todayISO());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: t('cattle.newProcedure', 'Novo Manejo') },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const dateForApi = procedureDate.replace(/-/g, '');
      const procedure = await createProcedure({ procedure_date: dateForApi });
      const procedureId = procedure.pk.replace('Procedure|', '');
      navigate(`/cattle/procedures/${encodeURIComponent(procedureId)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <h1 className="page-title">{t('cattle.newProcedure', 'Novo Manejo')}</h1>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit} style={{ maxWidth: '400px' }}>
        <label className="form-label">
          {t('cattle.procedureDate', 'Data do Manejo')} *
          <input
            type="date"
            required
            value={procedureDate}
            onChange={(e) => setProcedureDate(e.target.value)}
            className="form-input"
          />
        </label>

        <div style={{ marginTop: 'var(--space-md)', display: 'flex', gap: 'var(--space-sm)' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/cattle')}
          >
            {t('common.cancel')}
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? t('common.loading') : t('common.create')}
          </button>
        </div>
      </form>
    </Layout>
  );
}
