import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthProvider';

export default function LoginView() {
  const { t } = useTranslation();
  const { login } = useAuth();

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo-area">
          <span className="login-emoji" role="img" aria-label="livestock">🌿</span>
          <h1 className="login-title">LMJM</h1>
          <p className="login-subtitle">Livestock Management</p>
        </div>
        <button type="button" className="login-btn" onClick={login}>
          {t('auth.loginWithGoogle')}
        </button>
      </div>
    </div>
  );
}
