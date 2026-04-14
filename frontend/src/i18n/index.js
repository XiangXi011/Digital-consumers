import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import zhCN from './zh-CN.json';
import en from './en.json';

const savedLang = typeof localStorage !== 'undefined'
  ? localStorage.getItem('app_language') || 'zh-CN'
  : 'zh-CN';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      'zh-CN': { translation: zhCN },
      en: { translation: en },
    },
    lng: savedLang,
    fallbackLng: 'zh-CN',
    interpolation: {
      escapeValue: false,
    },
  });

export function changeLanguage(lang) {
  i18n.changeLanguage(lang);
  localStorage.setItem('app_language', lang);
}

export default i18n;
