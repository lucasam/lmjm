import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import Layout from '../components/Layout';

export default function SpeciesSelectionView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <Layout userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title" style={{ textAlign: 'center' }}>{t('species.title')}</h1>
      <div className="species-grid">
        <button
          type="button"
          className="species-card"
          onClick={() => navigate('/cattle')}
        >
          <span className="species-emoji" role="img" aria-label={t('species.cattle')}>
            🐄
          </span>
          <span className="species-label">{t('species.cattle')}</span>
        </button>
        <button
          type="button"
          className="species-card"
          onClick={() => navigate('/pigs')}
        >
          <span className="species-emoji" role="img" aria-label={t('species.pigs')}>
            🐖
          </span>
          <span className="species-label">{t('species.pigs')}</span>
        </button>
      </div>
    </Layout>
  );
}
