import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    lng: 'pt-BR',
    fallbackLng: 'pt-BR',
    supportedLngs: ['pt-BR'],
    interpolation: {
      escapeValue: false,
    },
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

/**
 * Format a Date or ISO date/datetime string to pt-BR convention.
 * - Datetime strings (YYYY-MM-DDTHH:MM) → DD/MM/YYYY HH:MM
 * - Date-only strings (YYYY-MM-DD) → DD/MM/YYYY (legacy)
 * - Date objects → DD/MM/YYYY via toLocaleDateString
 */
export function formatDate(value: Date | string): string {
  if (typeof value === 'string') {
    // Datetime: YYYY-MM-DDTHH:MM
    const dtMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/);
    if (dtMatch) {
      return `${dtMatch[3]}/${dtMatch[2]}/${dtMatch[1]} ${dtMatch[4]}:${dtMatch[5]}`;
    }
    // Date-only: YYYY-MM-DD (legacy)
    const dateMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateMatch) {
      return `${dateMatch[3]}/${dateMatch[2]}/${dateMatch[1]}`;
    }
  }
  const date = typeof value === 'string' ? new Date(value) : value;
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/**
 * Format a number using pt-BR locale (comma decimal, period thousands).
 */
export function formatNumber(value: number, decimals?: number): string {
  return value.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export default i18n;
