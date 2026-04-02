import { useTranslation } from 'react-i18next';

interface ErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  const { t } = useTranslation();

  return (
    <div className="error-container" role="alert">
      <div className="error-title">⚠ {t('common.error')}</div>
      <div>{message || t('errors.generic')}</div>
      {onRetry && (
        <button type="button" className="error-retry-btn" onClick={onRetry}>
          {t('common.retry', 'Tentar novamente')}
        </button>
      )}
    </div>
  );
}
