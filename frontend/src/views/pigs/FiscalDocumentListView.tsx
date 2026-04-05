import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { listAllFiscalDocuments, reprocessFiscalDocument } from '../../api/client';
import { formatDate, formatNumber } from '../../i18n';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';
import type { FiscalDocument } from '../../types/models';

export default function FiscalDocumentListView() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [reprocessing, setReprocessing] = useState<string | null>(null);
  const [reprocessResult, setReprocessResult] = useState<string | null>(null);

  const fetchDocs = useCallback(() => listAllFiscalDocuments(), []);
  const { data: docs, loading, error, refetch } = useApi(fetchDocs);

  const handleReprocess = async (doc: FiscalDocument) => {
    const key = doc.fiscal_document_number;
    setReprocessing(key);
    setReprocessResult(null);
    try {
      await reprocessFiscalDocument(doc.pk, doc.fiscal_document_number);
      setReprocessResult(`✓ ${key}`);
      refetch();
    } catch (err) {
      setReprocessResult(`✗ ${key}: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setReprocessing(null);
    }
  };

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.pigs'), to: '/pigs' },
    { label: t('pigs.fiscalDocuments', 'Notas Fiscais') },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{t('pigs.fiscalDocuments', 'Notas Fiscais')}</h1>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}
      {reprocessResult && (
        <div className={reprocessResult.startsWith('✓') ? 'alert alert-success' : 'alert alert-error'} style={{ marginBottom: '0.75rem' }}>
          {reprocessResult}
        </div>
      )}

      {!loading && !error && (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('pigs.fiscalDocumentNumber')}</th>
                <th>{t('pigs.issueDate', 'Emissão')}</th>
                <th>{t('pigs.productDescription', 'Produto')}</th>
                <th>{t('pigs.actualAmountKg')}</th>
                <th>{t('pigs.supplierName', 'Fornecedor')}</th>
                <th>{t('pigs.orderNumber', 'Pedido')}</th>
                <th>{t('pigs.batchPk', 'Lote PK')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(docs ?? []).map((doc) => (
                <tr key={`${doc.pk}-${doc.fiscal_document_number}`}>
                  <td>{doc.fiscal_document_number}</td>
                  <td>{formatDate(doc.issue_date)}</td>
                  <td>{doc.product_description}</td>
                  <td>{formatNumber(doc.actual_amount_kg)}</td>
                  <td>{doc.supplier_name}</td>
                  <td>{doc.order_number}</td>
                  <td style={{ fontSize: '0.75rem', maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.pk === 'UNMATCHED_FISCAL' ? '⚠️ Sem lote' : doc.pk.substring(0, 8)}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                      onClick={() => handleReprocess(doc)}
                      disabled={reprocessing === doc.fiscal_document_number}
                    >
                      {reprocessing === doc.fiscal_document_number ? '...' : '🔄'}
                    </button>
                  </td>
                </tr>
              ))}
              {(docs ?? []).length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center' }}>{t('common.noData')}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
