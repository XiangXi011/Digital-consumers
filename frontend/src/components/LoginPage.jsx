import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (isRegister) {
        await register(email, password, displayName);
      } else {
        await login(email, password);
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="w-full max-w-md bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/10 p-8">
        <h1 className="text-2xl font-extrabold text-on-surface text-center mb-6 tracking-tight">
          {isRegister ? '注册' : '登录'}
        </h1>

        {error && (
          <div className="mb-4 p-3 bg-error-container text-on-error-container text-xs rounded-xl flex items-center">
            <span className="material-symbols-outlined mr-2 text-sm">error</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">显示名称</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none"
                placeholder="可选，默认取邮箱前缀"
              />
            </div>
          )}
          <div>
            <label className="block text-xs font-bold text-on-surface-variant mb-2">邮箱</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-on-surface-variant mb-2">密码</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none"
              placeholder="至少 6 位"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-primary text-white rounded-xl text-sm font-bold hover:bg-primary/90 shadow-md hover:shadow-lg transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {submitting ? '处理中...' : isRegister ? '注册' : '登录'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-on-surface-variant">
          {isRegister ? '已有账号？' : '没有账号？'}
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            className="ml-1 text-primary font-bold hover:underline"
          >
            {isRegister ? '去登录' : '去注册'}
          </button>
        </p>
      </div>
    </div>
  );
}
