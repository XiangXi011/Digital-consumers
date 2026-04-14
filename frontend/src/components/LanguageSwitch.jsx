import { useTranslation } from 'react-i18next';
import { changeLanguage } from '../i18n';

export default function LanguageSwitch() {
  const { i18n } = useTranslation();
  const current = i18n.language;

  return (
    <div className="flex items-center gap-1 bg-surface-container rounded-lg p-0.5">
      <button
        onClick={() => changeLanguage('zh-CN')}
        aria-label="切换为中文"
        className={`px-3 py-2.5 text-xs font-bold rounded-md transition-colors min-h-[44px] ${
          current.startsWith('zh')
            ? 'bg-primary text-white'
            : 'text-on-surface-variant hover:bg-surface-container-highest'
        }`}
      >
        中文
      </button>
      <button
        onClick={() => changeLanguage('en')}
        aria-label="Switch to English"
        className={`px-3 py-2.5 text-xs font-bold rounded-md transition-colors min-h-[44px] ${
          current === 'en'
            ? 'bg-primary text-white'
            : 'text-on-surface-variant hover:bg-surface-container-highest'
        }`}
      >
        EN
      </button>
    </div>
  );
}
