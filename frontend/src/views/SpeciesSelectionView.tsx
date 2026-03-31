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
      <h1 style={titleStyle}>{t('species.title')}</h1>
      <div style={gridStyle}>
        <button
          type="button"
          style={cardStyle}
          onClick={() => navigate('/cattle')}
        >
          <span style={emojiStyle} role="img" aria-label={t('species.cattle')}>
            🐄
          </span>
          <span style={labelStyle}>{t('species.cattle')}</span>
        </button>
        <button
          type="button"
          style={cardStyle}
          onClick={() => navigate('/pigs')}
        >
          <span style={emojiStyle} role="img" aria-label={t('species.pigs')}>
            🐖
          </span>
          <span style={labelStyle}>{t('species.pigs')}</span>
        </button>
      </div>
    </Layout>
  );
}

const titleStyle: React.CSSProperties = {
  fontSize: '1.25rem',
  fontWeight: 600,
  marginBottom: '1.5rem',
  textAlign: 'center',
};

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
  gap: '1rem',
  maxWidth: '400px',
  margin: '0 auto',
};

const cardStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: '44px',
  minHeight: '44px',
  padding: '2rem 1rem',
  backgroundColor: '#fff',
  border: '2px solid #e0e0e0',
  borderRadius: '12px',
  cursor: 'pointer',
  transition: 'border-color 0.15s',
  gap: '0.75rem',
};

const emojiStyle: React.CSSProperties = {
  fontSize: '3rem',
};

const labelStyle: React.CSSProperties = {
  fontSize: '1.1rem',
  fontWeight: 600,
  color: '#333',
};
