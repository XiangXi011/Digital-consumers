import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const navItems = [
  { path: '/', icon: 'dashboard', label: '仪表盘' },
  { path: '/new', icon: 'add_box', label: '新建评审' },
  { path: '/personas', icon: 'face', label: '数字画像库', fill: true },
  { path: '/reports', icon: 'assessment', label: '评审项目' },
  { path: '/docs', icon: 'description', label: '报告中心' },
  { path: '/settings', icon: 'settings', label: '系统设置' },
];

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth();
  const initials = user?.display_name
    ? user.display_name.slice(0, 1).toUpperCase()
    : user?.email?.slice(0, 1).toUpperCase() || '?';
  return (
    <aside className={`bg-slate-100 h-screen w-64 fixed left-0 top-0 flex flex-col p-4 space-y-2 font-['Manrope'] antialiased z-50 border-r border-slate-200 transition-transform duration-300 md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="mb-8 px-2 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">数字体验官</h1>
          <p className="text-xs text-slate-500 font-medium tracking-wider mt-1">数字体验官平台</p>
        </div>
        <button
          onClick={onClose}
          aria-label="关闭侧栏"
          className="md:hidden text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-200 transition-colors"
        >
          <span className="material-symbols-outlined" aria-hidden="true">close</span>
        </button>
      </div>
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={onClose}
            className={({ isActive }) =>
              isActive
                ? "flex items-center space-x-3 px-3 py-2 text-primary bg-white font-bold rounded-lg transition-all duration-200 nav-active-glow border border-primary/10"
                : "flex items-center space-x-3 px-3 py-2 text-slate-500 hover:text-primary hover:bg-slate-200 transition-colors duration-200 rounded-lg group"
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`material-symbols-outlined ${isActive && item.fill ? 'nav-active-icon-glow' : ''}`}
                  style={item.fill && isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
                >
                  {item.icon}
                </span>
                <span className="text-sm font-medium">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto p-4 bg-white/50 rounded-xl">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-white text-xs font-bold">{initials}</div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-slate-900 truncate">{user?.display_name || user?.email || '用户'}</p>
            <p className="text-xs text-slate-500">{user?.role || ''}</p>
          </div>
          <button
            onClick={logout}
            title="退出登录"
            aria-label="退出登录"
            className="text-slate-400 hover:text-red-500 p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
