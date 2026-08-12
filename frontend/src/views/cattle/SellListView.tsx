import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listSells } from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';

function money(value: number | undefined): string {
  if (value == null) return '—';
  return `R$ ${formatNumber(value)}`;
}

export default function SellListView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const fetchSells = useCallback(() => listSells(), []);
  const { data: sells, loading, error, refetch } = useApi(fetchSells);

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: t('cattle.sells', 'Vendas') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{t('cattle.sells', 'Vendas')}</h1>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/cattle/sells/new')}>
          {t('cattle.newSell', 'Nova Venda')}
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}
      {!loading && !error && (!sells || sells.length === 0) && (
        <div className="table-empty">{t('common.noData')}</div>
      )}
      {!loading && !error && sells && sells.length > 0 && (
        <div className="table-wrapper" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>{t('cattle.sellDate', 'Data')}</th>
                <th>{t('cattle.numberOfAnimals', 'Nº Animais')}</th>
                <th>{t('cattle.sex', 'Sexo')}</th>
                <th>{t('cattle.buyer', 'Comprador')}</th>
                <th>{t('cattle.batch', 'Lote')}</th>
                <th>{t('cattle.averageWeight', 'Peso Médio')}</th>
                <th>{t('cattle.unitValue', 'Valor Unitário')}</th>
                <th>{t('cattle.pricePerArroba', 'Preço/@')}</th>
                <th>{t('cattle.totalValue', 'Valor Total')}</th>
                <th>{t('cattle.netValue', 'Valor Líquido')}</th>
              </tr>
            </thead>
            <tbody>
              {sells.map((sell) => (
                <tr
                  key={sell.pk}
                  className="table-row-clickable"
                  onClick={() => navigate(`/cattle/sells/${encodeURIComponent(sell.pk.replace('Sell|', ''))}/edit`)}
                  tabIndex={0}
                  role="button"
                  onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/cattle/sells/${encodeURIComponent(sell.pk.replace('Sell|', ''))}/edit`); }}
                >
                  <td>{formatDate(sell.sell_date)}</td>
                  <td>{sell.number_of_animals}</td>
                  <td>{sell.sex === 'M' ? t('cattle.male', 'Macho') : sell.sex === 'F' ? t('cattle.female', 'Fêmea') : '—'}</td>
                  <td>{sell.buyer ?? '—'}</td>
                  <td>{sell.batch ?? '—'}</td>
                  <td>{sell.average_weight ? `${formatNumber(sell.average_weight)} kg` : '—'}</td>
                  <td>{money(sell.unit_value)}</td>
                  <td
                    title={
                      sell.price_per_arroba
                        ? `${t('cattle.pricePerKg', 'Preço/kg')}: ${money(sell.price_per_arroba / 30)}`
                        : undefined
                    }
                    style={sell.price_per_arroba ? { cursor: 'help' } : undefined}
                  >
                    {money(sell.price_per_arroba)}
                  </td>
                  <td>{money(sell.total_value)}</td>
                  <td>{money(sell.net_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
