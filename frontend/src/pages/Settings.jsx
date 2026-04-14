import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState({});
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    api.getSettings()
      .then(data => { setSettings(data); setForm(data); })
      .catch(err => console.error('Failed to load settings:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      const updates = {};
      if (form.llm_model !== settings.llm_model) updates.llm_model = form.llm_model;
      if (form.llm_api_base !== settings.llm_api_base) updates.llm_api_base = form.llm_api_base;
      if (form.llm_api_key) updates.llm_api_key = form.llm_api_key;
      if (form.dingtalk_app_key !== settings.dingtalk_app_key) updates.dingtalk_app_key = form.dingtalk_app_key;
      if (form.dingtalk_app_secret) updates.dingtalk_app_secret = form.dingtalk_app_secret;
      if (form.prompt_shield_enabled !== settings.prompt_shield_enabled) updates.prompt_shield_enabled = !!form.prompt_shield_enabled;
      if (form.pii_sanitization_enabled !== settings.pii_sanitization_enabled) updates.pii_sanitization_enabled = !!form.pii_sanitization_enabled;
      if (form.langsmith_tracing !== settings.langsmith_tracing) updates.langsmith_tracing = !!form.langsmith_tracing;
      if ((form.langsmith_project || '') !== (settings.langsmith_project || '')) updates.langsmith_project = form.langsmith_project || '';

      const res = await api.updateSettings(updates);
      setSettings(res);
      setForm(res);
      setSaveMsg('设置已保存');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (err) {
      setSaveMsg(`保存失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConnection();
      setTestResult(res);
    } catch (err) {
      setTestResult({ success: false, error: err.message });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full text-sm text-slate-400">加载设置...</div>;
  }

  return (
    <div className="pt-8 pb-12 px-8 h-full max-w-4xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-extrabold text-on-surface tracking-tight mb-2">系统设置</h2>
        <p className="text-sm text-on-surface-variant">管理 AI 模型配置、钉钉集成和安全策略</p>
      </div>

      <div className="space-y-6">
        {/* LLM 配置 */}
        <section className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-outline-variant/10">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-primary-container rounded-xl flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-[20px]">psychology</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-on-surface">AI 模型配置</h3>
              <p className="text-xs text-on-surface-variant">配置 LLM API 连接参数</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">模型名称</label>
              <input type="text"
                className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm outline-none"
                value={form.llm_model || ''} onChange={e => setForm({...form, llm_model: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">模型服务地址</label>
              <input type="text"
                className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm outline-none"
                value={form.llm_api_base || ''} onChange={e => setForm({...form, llm_api_base: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">模型密钥（当前：{settings?.llm_api_key_masked || '未设置'}）</label>
              <input type="password"
                className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm outline-none"
                placeholder="留空则不修改" value={form.llm_api_key || ''} onChange={e => setForm({...form, llm_api_key: e.target.value})}
              />
            </div>
            <div className="flex items-end">
              <button onClick={handleTestConnection} disabled={testing}
                className="w-full px-4 py-3 rounded-xl text-sm font-bold bg-surface-container-high text-on-surface hover:bg-surface-container-highest transition-colors flex items-center justify-center disabled:opacity-50">
                <span className="material-symbols-outlined mr-2 text-[18px]">speed</span>
                {testing ? '测试中...' : '测试连接'}
              </button>
            </div>
          </div>
          {testResult && (
            <div className={`mt-4 p-4 rounded-xl text-sm flex items-center ${testResult.success ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
              <span className="material-symbols-outlined mr-2">{testResult.success ? 'check_circle' : 'error'}</span>
              {testResult.success
                ? `连接成功！模型: ${testResult.model}, 延迟: ${testResult.latency_ms}ms`
                : `连接失败: ${testResult.error}`
              }
            </div>
          )}
        </section>

        {/* 钉钉配置 */}
        <section className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-outline-variant/10">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-[20px]">chat</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-on-surface">钉钉集成</h3>
              <p className="text-xs text-on-surface-variant">群机器人 Stream 连接配置</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">应用 Key</label>
              <input type="text"
                className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm outline-none"
                value={form.dingtalk_app_key || ''} onChange={e => setForm({...form, dingtalk_app_key: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">应用 Secret（当前：{settings?.dingtalk_app_secret_masked || '未设置'}）</label>
              <input type="password"
                className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm outline-none"
                placeholder="留空则不修改"
                value={form.dingtalk_app_secret || ''}
                onChange={e => setForm({...form, dingtalk_app_secret: e.target.value})}
              />
            </div>
          </div>
        </section>

        {/* 安全策略 */}
        <section className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-outline-variant/10">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-[20px]">shield</span>
            </div>
            <div>
              <h3 className="text-sm font-bold text-on-surface">安全策略</h3>
              <p className="text-xs text-on-surface-variant">Prompt Shield 与隐私保护</p>
            </div>
          </div>
          <div className="space-y-4">
            <label className="flex items-center justify-between p-4 bg-surface rounded-xl cursor-pointer">
              <div>
                <p className="text-sm font-bold text-on-surface">Prompt Shield 防注入</p>
                <p className="text-xs text-on-surface-variant">检测并阻止恶意提示词注入攻击</p>
              </div>
              <input
                type="checkbox"
                className="w-5 h-5 accent-primary"
                checked={!!form.prompt_shield_enabled}
                onChange={e => setForm({ ...form, prompt_shield_enabled: e.target.checked })}
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-surface rounded-xl cursor-pointer">
              <div>
                <p className="text-sm font-bold text-on-surface">PII 脱敏处理</p>
                <p className="text-xs text-on-surface-variant">自动哈希处理会话中的个人标识信息</p>
              </div>
              <input
                type="checkbox"
                className="w-5 h-5 accent-primary"
                checked={!!form.pii_sanitization_enabled}
                onChange={e => setForm({ ...form, pii_sanitization_enabled: e.target.checked })}
              />
            </label>

            <div className="p-4 bg-surface rounded-xl">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-bold text-on-surface">LangSmith 追踪</p>
                  <p className="text-xs text-on-surface-variant">开启后会把链路数据上报到 LangSmith</p>
                </div>
                <input
                  type="checkbox"
                  className="w-5 h-5 accent-primary"
                  checked={!!form.langsmith_tracing}
                  onChange={e => setForm({ ...form, langsmith_tracing: e.target.checked })}
                />
              </div>
              <label className="block text-xs font-bold text-on-surface-variant mb-2">LangSmith 项目名</label>
              <input
                type="text"
                className="w-full bg-surface-container-low px-3 py-2 rounded-lg border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 text-sm outline-none"
                placeholder="例如: market-research-agent"
                value={form.langsmith_project || ''}
                onChange={e => setForm({ ...form, langsmith_project: e.target.value })}
              />
            </div>
          </div>
        </section>

        {/* Save Bar */}
        <div className="flex items-center justify-between pt-4">
          {saveMsg && (
            <p className={`text-sm font-bold ${saveMsg.includes('失败') ? 'text-red-500' : 'text-emerald-600'}`}>{saveMsg}</p>
          )}
          <div className="flex-1"></div>
          <button onClick={handleSave} disabled={saving}
            className="px-8 py-3 rounded-xl text-sm font-bold bg-primary text-white shadow-md hover:shadow-lg hover:bg-primary/90 transition-all active:scale-[0.98] flex items-center disabled:opacity-50">
            <span className="material-symbols-outlined mr-2 text-[18px]">save</span>
            {saving ? '保存中...' : '保存设置'}
          </button>
        </div>
      </div>
    </div>
  );
}
