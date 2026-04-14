import { useLocation } from 'react-router-dom';
import LanguageSwitch from '../LanguageSwitch';

const PAGE_TITLES = {
  '/': '仪表盘',
  '/new': '新建评审',
  '/personas': null,
  '/reports': '评审结果报告',
  '/docs': '报告中心',
  '/settings': '系统设置',
};

export default function Header({ onMenuClick }) {
  const location = useLocation();

  const title = PAGE_TITLES[location.pathname] ?? '数字体验官';

  return (
    <header className="fixed top-0 right-0 left-0 md:left-64 h-16 bg-white/85 backdrop-blur-md z-30 border-b border-slate-200/50 flex items-center justify-between px-4 md:px-8">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          aria-label="打开菜单"
          className="md:hidden text-slate-500 hover:text-slate-700 p-2 rounded-lg hover:bg-slate-100 transition-colors"
        >
          <span className="material-symbols-outlined" aria-hidden="true">menu</span>
        </button>
        {title && <h2 className="text-sm font-bold text-on-surface">{title}</h2>}
      </div>

      <div className="flex items-center space-x-2 md:space-x-4">
        {location.pathname === '/personas' && (
          <div className="hidden sm:flex items-center bg-surface-container px-3 py-1.5 rounded-full">
            <span className="material-symbols-outlined text-outline text-sm mr-2">search</span>
            <input aria-label="搜索画像或标签" className="bg-transparent border-none outline-none focus:ring-0 text-xs w-48 placeholder:text-outline p-0" placeholder="搜索画像或标签..." type="text"/>
          </div>
        )}

        <LanguageSwitch />

        <button aria-label="通知" className="hover:bg-slate-50 rounded-full p-2 text-slate-500 transition-all relative">
          <span className="material-symbols-outlined" aria-hidden="true">notifications</span>
        </button>

        {location.pathname !== '/' && (
          <img alt="Profile" className="w-8 h-8 rounded-full object-cover border-2 border-white shadow-sm" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDdkDXWIbI6XuU6jyZNZa7o_MfiCA_2VvOWc4fai2v1lrrh-wJ8vt4Uljnbdlm3ddlqvnoSawv21N5eatylEatWZNERkgnhQSQVbC3E7y_8kyPV9KMrv1Cjr6JOpT2zU7Sn9ByBIrR5mllYGWxw-a4CLprWWJFpQW2XZ_jvgMmWaD-K1LfugG124vZEiw8DFO3h8UaFh4KXSdkFyeh_My8nu9ho1Won-K3PfDjfpQVRHWoi6WAsOfUBXa9iVN93CiXD8IejSgWqdRwe"/>
        )}
      </div>
    </header>
  );
}
