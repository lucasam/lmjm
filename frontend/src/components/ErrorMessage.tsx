import { useTranslation } from 'react-i18next';

interface ErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

const containerStyle: React.CSSProperties = {
  padding: '1rem',
  margin: '1rem 0',
  backgroundColor: '#fdecea',
  border: '1px solid #f5c6cb',
  borderRadius: '6px',
  color: '#721c24',
};

const titleStyle: React.CSSProperties = {
  fontWeight: 600,
  marginBottom: '0.5rem',
};

const retryBtnStyle: React.CSSProperties = {
  marginTop: '0.75rem',
  padding: '10px 20px',
  minWidth: '44px',
  minHeight: '44px',
  backgroundColor: '#d32f2f',
  color: '#fff',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.9rem',
};

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  const { t } = useTranslation();

  return (
    <div style={containerStyle} role="alert">
      <div style={titleStyle}>{t('common.error')}</div>
      <div>{message || t('errors.generic')}</div>
      {onRetry && (
        <button type="button" style={retryBtnStyle} onClick={onRetry}>
          {t('common.retry', 'Tentar novamente')}
        </button>
      )}
    </div>
  );
}
