import { useTranslation } from 'react-i18next';

export default function LoadingSpinner() {
  const { t } = useTranslation();

  return (
    <div className="spinner-container" role="status" aria-live="polite">
      <div className="spinner-dot" />
      <span className="spinner-text">{t('common.loading')}</span>
    </div>
  );
}
