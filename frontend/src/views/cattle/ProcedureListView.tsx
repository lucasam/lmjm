import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listProcedures } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type { Procedure } from '../../types/models';

function formatDate(dateStr: string): string {
  if (!dateStr) return '—';
  const [y, m, d] = dateStr.split('-');
  if (!y || !m || !d) return dateStr;
  return `${d}/${m}/${y}`;
}

function statusLabel(status: string): string {
  if (status === 'confirmed') return 'Confirmado';
  if (status === 'cancelled') return 'Cancelado';
  return 'Aberto';
}

export default function ProcedureListView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const fetchProcedures = useCallback(() => listProcedures(), []);
  const { data: procedures, loading, error, refetch } = useApi(fetchProcedures);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: t('cattle.procedures', 'Manejos') },
  ];

  const handleRowClick = (procedure: Procedure) => {
    const procedureId = procedure.pk.replace('Procedure|', '');
    navigate(`/cattle/procedures/${encodeURIComponent(procedureId)}`);
  };

  return (
    <Layout
      breadcrumbs={breadcrumbs}
      userName={user?.name}
      userEmail={user?.email}
      onLogout={logout}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('cattle.procedures', 'Manejos')}</h1>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => navigate('/cattle/procedures/new')}
        >
          {t('cattle.newProcedure', 'Novo Manejo')}
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}
      {!loading && !error && (!procedures || procedures.length === 0) && (
        <div className="table-empty">{t('common.noData')}</div>
      )}
      {!loading && !error && procedures && procedures.length > 0 && (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('cattle.procedureDate', 'Data')}</th>
                <th>{t('cattle.status', 'Status')}</th>
                <th>{t('cattle.actionCount', 'Ações')}</th>
              </tr>
            </thead>
            <tbody>
              {procedures.map((procedure) => (
                <tr
                  key={procedure.pk}
                  className="table-row-clickable"
                  onClick={() => handleRowClick(procedure)}
                  tabIndex={0}
                  role="button"
                  onKeyDown={(e) => { if (e.key === 'Enter') handleRowClick(procedure); }}
                >
                  <td>{formatDate(procedure.procedure_date)}</td>
                  <td>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.85rem',
                      fontWeight: 500,
                      backgroundColor: procedure.status === 'confirmed' ? 'var(--success-light, #d4edda)' : procedure.status === 'cancelled' ? '#f8d7da' : 'var(--warning-light, #fff3cd)',
                      color: procedure.status === 'confirmed' ? 'var(--success, #155724)' : procedure.status === 'cancelled' ? '#721c24' : 'var(--warning, #856404)',
                    }}>
                      {statusLabel(procedure.status)}
                    </span>
                  </td>
                  <td>{procedure.action_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
