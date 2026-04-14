import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function PersonaLibrary() {
  const [personas, setPersonas] = useState([]);
  const [activePersona, setActivePersona] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [avatarUrl, setAvatarUrl] = useState('');
  const [avatarLoading, setAvatarLoading] = useState(false);

  // 加载画像列表
  useEffect(() => {
    api.getPersonas()
      .then(res => {
        const list = res.personas || [];
        setPersonas(list);
        if (list.length > 0) setActivePersona(list[0]);
      })
      .catch(err => console.error('Failed to load personas:', err))
      .finally(() => setLoading(false));
  }, []);

  // 加载选中画像的详情
  useEffect(() => {
    if (!activePersona) return;
    api.getPersona(activePersona.id)
      .then(setDetail)
      .catch(err => console.error('Failed to load persona detail:', err));
  }, [activePersona?.id]);

  // 根据画像信息生成头像
  useEffect(() => {
    const run = async () => {
      if (!detail?.id) {
        setAvatarUrl('');
        return;
      }
      setAvatarLoading(true);
      try {
        const prompt = [
          `中国妈妈消费者画像头像，半身近景，写实风格，干净背景`,
          `画像ID: ${detail.id}`,
          `名称: ${detail.name || ''}`,
          `预算层级: ${detail.budget_band || ''}`,
          `标签: ${(detail.tags || []).join('、')}`,
          `要求：自然亲和、细节真实、无文字、无水印`
        ].join('；');

        const res = await api.generateAvatar({
          prompt,
          size: '2K',
          response_format: 'url',
          watermark: false,
          cache_key: `persona-avatar:${detail.id}`,
          use_cache: true,
        });
        const first = Array.isArray(res?.data) ? res.data[0] : null;
        setAvatarUrl(first?.url || '');
      } catch (err) {
        console.error('Failed to generate avatar:', err);
        setAvatarUrl('');
      } finally {
        setAvatarLoading(false);
      }
    };

    run();
  }, [detail?.id]);

  if (loading) {
    return <div className="flex items-center justify-center h-full text-sm text-slate-400">加载画像库...</div>;
  }

  const d = detail || {};
  const weights = d.decision_weights || {};
  const rubric = d.feature_scoring_rubric || {};
  const vetoRules = d.veto_rules || [];
  const samples = d.representative_samples || [];

  // 为雷达图计算 SVG 点坐标
  const dims = Object.keys(weights);
  const dimLabels = { efficacy_clarity: '功效', trust_signal: '信任', convenience: '便利', price_fit: '价格' };

  return (
    <div className="flex h-full relative">
      {/* Sidebar: Persona List */}
      <section className="w-80 bg-surface-container-low border-r border-outline-variant/10 overflow-y-auto custom-scrollbar p-6 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold uppercase tracking-widest text-outline">画像库 ({personas.length})</h3>
        </div>
        <div className="space-y-3">
          {personas.map(p => (
            <div key={p.id} onClick={() => setActivePersona(p)}
              className={p.id === activePersona?.id
                ? "bg-surface-container-lowest p-4 rounded-xl shadow-sm border-l-4 border-primary ring-1 ring-black/5 transition-all cursor-pointer"
                : "bg-surface-container-low hover:bg-white p-4 rounded-xl transition-all cursor-pointer group border border-transparent hover:border-outline-variant/30"
              }
            >
              <div className="flex justify-between items-start mb-2">
                <span className={`text-sm font-semibold ${p.id === activePersona?.id ? 'text-on-surface' : 'text-on-surface group-hover:text-primary'}`}>
                  {p.name}
                </span>
                {p.id === activePersona?.id ? (
                  <span className="text-xs px-1.5 py-0.5 bg-primary-fixed text-on-primary-fixed rounded font-bold">当前</span>
                ) : (
                  <span className="text-xs text-slate-400 font-bold">{p.id}</span>
                )}
              </div>
              <p className="text-xs text-on-surface-variant line-clamp-1 mb-3">{p.budget_band === 'high' ? '高预算人群' : p.budget_band === 'mid' ? '中预算人群' : '低预算人群'}</p>
              {p.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {p.tags.slice(0, 3).map(tag => (
                    <span key={tag} className="text-xs bg-surface-container px-2 py-0.5 rounded-full text-on-secondary-fixed-variant">#{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Main Detail Pane */}
      <section className="flex-1 bg-surface p-8 overflow-y-auto custom-scrollbar relative">
        {!detail ? (
          <div className="flex items-center justify-center h-full text-sm text-slate-400">选择一个画像查看详情</div>
        ) : (
          <>
            {/* Header */}
            <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[0px_20px_40px_rgba(25,28,30,0.06)] mb-8 border border-outline-variant/10">
              <div className="flex items-start justify-between">
                <div className="space-y-4 max-w-2xl">
                  <div className="flex items-center space-x-3">
                    <h2 className="text-4xl font-headline font-extrabold text-on-surface tracking-tight">{d.name}</h2>
                    <span className="bg-primary-fixed text-on-primary-fixed px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">{d.budget_band}</span>
                  </div>
                  <div className="flex items-center space-x-8 pt-2">
                    {dims.map(dim => (
                      <div key={dim} className="flex flex-col">
                        <span className="text-xs uppercase tracking-widest text-outline font-bold">{dimLabels[dim] || dim}</span>
                        <span className="text-sm font-semibold text-on-surface">{(weights[dim] * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="w-20 h-20 bg-surface-container-low rounded-2xl flex items-center justify-center border border-outline-variant/10 overflow-hidden">
                  {avatarUrl ? (
                    <img src={avatarUrl} alt={`${d.name || d.id} 头像`} className="w-full h-full object-cover" />
                  ) : avatarLoading ? (
                    <span className="text-xs text-on-surface-variant">生成中</span>
                  ) : (
                    <span className="text-3xl font-extrabold text-primary">{d.id}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Detail Cards */}
            <div className="grid grid-cols-12 gap-6 mb-8">
              {/* Veto Rules */}
              <div className="col-span-12 lg:col-span-6 bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-outline-variant/10">
                <div className="flex items-center space-x-2 mb-4 text-tertiary">
                  <span className="material-symbols-outlined">block</span>
                  <h4 className="text-sm font-bold">一票否决条件</h4>
                </div>
                <p className="text-xs text-on-surface-variant mb-4 italic">{d.veto_trigger}</p>
                <ul className="space-y-3">
                  {vetoRules.map((rule, i) => (
                    <li key={i} className="flex items-start space-x-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-tertiary mt-1.5 shrink-0"></span>
                      <p className="text-xs text-on-surface-variant leading-relaxed">
                        <strong className="text-on-surface block mb-0.5">{rule.code}</strong>
                        {rule.description}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Scoring Rubric */}
              <div className="col-span-12 lg:col-span-6 bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-outline-variant/10">
                <div className="flex items-center space-x-2 mb-4 text-primary">
                  <span className="material-symbols-outlined">rule</span>
                  <h4 className="text-sm font-bold">评分标准</h4>
                </div>
                <div className="space-y-4">
                  {Object.entries(rubric).map(([dim, levels]) => (
                    <div key={dim}>
                      <h5 className="text-xs font-bold text-on-surface mb-2">{dimLabels[dim] || dim}</h5>
                      <div className="space-y-1">
                        {Object.entries(levels).sort((a, b) => Number(b[0]) - Number(a[0])).map(([score, desc]) => (
                          <div key={score} className="flex items-start text-xs">
                            <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold mr-2 shrink-0 ${
                              Number(score) >= 4 ? 'bg-emerald-100 text-emerald-700' : Number(score) <= 2 ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                            }`}>{score}</span>
                            <span className="text-on-surface-variant">{desc}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Representative Samples */}
            {samples.length > 0 && (
              <div className="space-y-6 pb-20">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-outline">代表性样本 ({samples.length})</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {samples.slice(0, 6).map((sample, i) => {
                    const profile = sample.basic_profile || {};
                    return (
                      <div key={i} className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10 hover:shadow-md transition-shadow">
                        <div className="flex items-center space-x-3 mb-3">
                          <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                            <span className="text-sm font-bold text-primary">{(profile.nickname || '?')[0]}</span>
                          </div>
                          <div>
                            <p className="text-sm font-bold text-on-surface">{profile.nickname || '未命名'}</p>
                            <p className="text-xs text-outline font-medium">{profile.age || ''}岁 · {profile.city || ''}</p>
                          </div>
                        </div>
                        <p className="text-xs text-on-surface-variant leading-relaxed italic">"{sample.persona_quote || profile.personality || '—'}"</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
