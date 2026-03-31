import { useTranslation } from 'react-i18next';

const spinnerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '2rem',
  minHeight: '200px',
};

const dotStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  border: '4px solid #e0e0e0',
  borderTop: '4px solid #1976d2',
  borderRadius: '50%',
  animation: 'spin 0.8s linear infinite',
};

const textStyle: React.CSSProperties = {
  marginTop: '1rem',
  fontSize: '0.95rem',
  color: '#666',
};

export default function LoadingSpinner() {
  const { t } = useTranslation();

  return (
    <div style={spinnerStyle} role="status" aria-live="polite">
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={dotStyle} />
      <span style={textStyle}>{t('common.loading')}</span>
    </div>
  );
}
