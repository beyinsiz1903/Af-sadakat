import React from 'react';
import { useTranslation } from 'react-i18next';
import { SUPPORTED_LANGS } from '../i18n';

export default function LanguageSwitcher({ className = '' }) {
  const { i18n } = useTranslation();
  const current = i18n.language?.split('-')[0] || 'tr';
  return (
    <select
      aria-label="Language"
      className={`text-sm bg-transparent border border-gray-300 rounded px-2 py-1 ${className}`}
      value={current}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
    >
      {SUPPORTED_LANGS.map((l) => (
        <option key={l.code} value={l.code}>
          {l.flag} {l.label}
        </option>
      ))}
    </select>
  );
}
