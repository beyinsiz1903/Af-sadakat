import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import tr from './locales/tr.json';
import en from './locales/en.json';
import ar from './locales/ar.json';
import de from './locales/de.json';
import ru from './locales/ru.json';

export const SUPPORTED_LANGS = [
  { code: 'tr', label: 'Türkçe', flag: '🇹🇷', dir: 'ltr' },
  { code: 'en', label: 'English', flag: '🇬🇧', dir: 'ltr' },
  { code: 'ar', label: 'العربية', flag: '🇸🇦', dir: 'rtl' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪', dir: 'ltr' },
  { code: 'ru', label: 'Русский', flag: '🇷🇺', dir: 'ltr' },
];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { tr: { translation: tr }, en: { translation: en }, ar: { translation: ar }, de: { translation: de }, ru: { translation: ru } },
    fallbackLng: 'tr',
    supportedLngs: SUPPORTED_LANGS.map((l) => l.code),
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'omnihub_lang',
    },
  });

function applyDirection(lng) {
  const found = SUPPORTED_LANGS.find((l) => l.code === lng);
  const dir = found?.dir || 'ltr';
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('dir', dir);
    document.documentElement.setAttribute('lang', lng);
  }
}

i18n.on('languageChanged', applyDirection);
applyDirection(i18n.language || 'tr');

export default i18n;
