import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthProvider';

export default function LoginView() {
  const { t } = useTranslation();
  const { login } = useAuth();

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>LMJM</h1>
        <button type="button" style={loginBtnStyle} onClick={login}>
          {t('auth.loginWithGoogle')}
        </button>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '100vh',
  padding: '1rem',
  backgroundColor: '#f5f5f5',
};

const cardStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '2rem 1.5rem',
  backgroundColor: '#fff',
  borderRadius: '8px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  width: '100%',
  maxWidth: '360px',
};

const titleStyle: React.CSSProperties = {
  fontSize: '1.75rem',
  fontWeight: 700,
  marginBottom: '2rem',
  color: '#1976d2',
};

const loginBtnStyle: React.CSSProperties = {
  minWidth: '44px',
  minHeight: '44px',
  padding: '12px 24px',
  fontSize: '1rem',
  fontWeight: 600,
  color: '#fff',
  backgroundColor: '#1976d2',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  width: '100%',
};
