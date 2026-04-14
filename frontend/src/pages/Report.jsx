import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';

export default function Report() {
  const [searchParams] = useSearchParams();
  const reportId = searchParams.get('id');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [shareMsg, setShareMsg] = useState('');

  useEffect(() => {
    if (!reportId) { setLoading(false); return; }
    api.getReport(reportId)
      .then(setReport)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [reportId]);

  if (!reportId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <span className="material-symbols-outlined text-6xl text-slate-300 mb-4 block">analytics</span>
          <h2 className="text-xl font-bold text-on-surface mb-2">选择报告查看</h2>
          <p className="text-sm text-on-surface-variant mb-6">请从<a href="/docs" className="text-primary hover:underline font-bold">报告中心</a>选择一份报告查看详情</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="flex items-center justify-center h-full text-sm text-slate-400">加载报告...</div>;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-red-500">
          <span className="material-symbols-outlined text-4xl mb-2 block">error</span>
          <p className="text-sm">加载失败: {error}</p>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const meta = report.meta || {};
  const brief = report.research_brief || {};
  const voices = report.consumer_voice || [];
  const synthesis = report.synthesis || {};
  const summary = synthesis.research_summary || {};
  const recommendation = synthesis.structured_recommendation || {};
  const metrics = report.evaluation_metrics || {};

  // 购买意向分布
  const intentDist = {};
  voices.forEach(v => {
    const intent = v.purchase_intent || 'unknown';
    intentDist[intent] = (intentDist[intent] || 0) + 1;
  });

  const intentColors = { buy: 'bg-emerald-500', maybe: 'bg-amber-500', reject: 'bg-red-500', unknown: 'bg-slate-300' };
  const intentLabels = { buy: '购买', maybe: '观望', reject: '拒绝', unknown: '未知' };

  const handleShare = async () => {
    try {
      const res = await api.shareReport(reportId);
      const absoluteUrl = `${window.location.origin}${res.share_url}`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(absoluteUrl);
      }
      setShareMsg(`分享链接已复制（7天有效，过期时间: ${res.expires_at || '未知'}）`);
    } catch (err) {
      setShareMsg(`分享失败: ${err.message}`);
    }
    setTimeout(() => setShareMsg(''), 3500);
  };

  return (
    <div className="pt-8 pb-16 px-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm border border-outline-variant/10 mb-8">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-extrabold text-on-surface tracking-tight mb-2">
              {meta.report_title || brief.research_goal || reportId}
            </h1>
            <div className="flex items-center space-x-4 text-xs text-on-surface-variant">
              <span>{meta.created_at || ''}</span>
              <span>·</span>
              <span>类型：{meta.question_type || brief.task_type || '—'}</span>
              <span>·</span>
              <span>{voices.length} 个画像参与</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={api.getReportDownloadUrl(reportId)}
              className="flex items-center px-4 py-2 bg-surface-container-high text-on-surface text-sm font-bold rounded-xl hover:bg-surface-container-highest transition-colors"
            >
              下载数据
            </a>
            <button
              type="button"
              onClick={handleShare}
              className="flex items-center px-4 py-2 bg-surface-container-high text-on-surface text-sm font-bold rounded-xl hover:bg-surface-container-highest transition-colors"
            >
              分享
            </button>
            <a href={api.getReportHtmlUrl(reportId)} target="_blank" rel="noopener noreferrer"
              className="flex items-center px-4 py-2 bg-primary text-white text-sm font-bold rounded-xl hover:bg-primary/90 transition-colors">
              网页报告
            </a>
          </div>
        </div>
      </div>

      {shareMsg && (
        <div className={`mb-4 text-sm font-bold ${shareMsg.includes('失败') ? 'text-red-500' : 'text-emerald-600'}`}>
          {shareMsg}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
          <p className="text-xs font-bold uppercase tracking-widest text-outline mb-2">总延迟</p>
          <p className="text-2xl font-extrabold text-primary latex-stat">{(metrics.pipeline_total_latency_ms / 1000).toFixed(1)}s</p>
        </div>
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
          <p className="text-xs font-bold uppercase tracking-widest text-outline mb-2">画像分歧度</p>
          <p className="text-2xl font-extrabold text-primary latex-stat">{((metrics.inter_persona_divergence_score || 0) * 100).toFixed(0)}%</p>
        </div>
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
          <p className="text-xs font-bold uppercase tracking-widest text-outline mb-2">少数派保留率</p>
          <p className="text-2xl font-extrabold text-primary latex-stat">{((metrics.minority_survival_rate || 0) * 100).toFixed(0)}%</p>
        </div>
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
          <p className="text-xs font-bold uppercase tracking-widest text-outline mb-2">重复短语率</p>
          <p className="text-2xl font-extrabold text-primary latex-stat">{((metrics.repeated_phrase_rate || 0) * 100).toFixed(1)}%</p>
        </div>
      </div>

      {/* Purchase Intent Distribution */}
      <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10 mb-8">
        <h3 className="text-sm font-bold text-on-surface mb-4">购买意向分布</h3>
        <div className="flex items-center space-x-1 mb-3 h-6 rounded-lg overflow-hidden">
          {Object.entries(intentDist).map(([intent, count]) => (
            <div key={intent} className={`${intentColors[intent] || 'bg-slate-300'} h-full transition-all`}
              style={{ width: `${(count / voices.length) * 100}%` }}
              title={`${intentLabels[intent] || intent}: ${count}`}></div>
          ))}
        </div>
        <div className="flex space-x-6">
          {Object.entries(intentDist).map(([intent, count]) => (
            <div key={intent} className="flex items-center text-xs">
              <div className={`w-3 h-3 rounded-full ${intentColors[intent] || 'bg-slate-300'} mr-2`}></div>
              <span className="text-on-surface-variant">{intentLabels[intent] || intent}: <strong className="text-on-surface">{count}</strong></span>
            </div>
          ))}
        </div>
      </div>

      {/* Consumer Voices */}
      <div className="mb-8">
        <h3 className="text-sm font-bold text-on-surface mb-4">画像评估详情</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {voices.map((voice, i) => {
            const intent = voice.purchase_intent || 'unknown';
            const score = voice.purchase_score || 0;
            return (
              <div key={i} className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                      <span className="text-sm font-bold text-primary">{voice.persona_id || '?'}</span>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-on-surface">{voice.persona_name || voice.persona_id}</p>
                      <p className="text-xs text-outline">{voice.stance || ''}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex px-2 py-1 rounded-full text-xs font-bold ${
                      intent === 'buy' ? 'bg-emerald-100 text-emerald-700' :
                      intent === 'reject' ? 'bg-red-100 text-red-700' :
                      'bg-amber-100 text-amber-700'
                    }`}>{intentLabels[intent] || intent}</span>
                    <p className="text-xs text-outline mt-1">得分：{typeof score === 'number' ? score.toFixed(2) : score}</p>
                  </div>
                </div>
                <p className="text-xs text-on-surface-variant italic mb-3">"{voice.voice_line || voice.verbatim_answer || '—'}"</p>
                {/* Rubric scores */}
                {voice.rubric_scores && (
                  <div className="flex space-x-3 mt-2">
                    {Object.entries(voice.rubric_scores).map(([dim, val]) => {
                      const dimShort = { efficacy_clarity: '功效', trust_signal: '信任', convenience: '便利', price_fit: '价格' };
                      return (
                        <div key={dim} className="text-center">
                          <p className="text-xs text-outline">{dimShort[dim] || dim}</p>
                          <p className={`text-sm font-bold ${val >= 4 ? 'text-emerald-600' : val <= 2 ? 'text-red-500' : 'text-amber-600'}`}>{val}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Research Summary */}
      {Object.keys(summary).length > 0 && (
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10 mb-8">
          <h3 className="text-sm font-bold text-on-surface mb-4">研究总结</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Object.entries(summary).map(([key, items]) => {
              const labels = { consensus: '共识', differences: '分歧', pain_points: '痛点', drivers: '驱动力', barriers: '障碍', copy_insights: '文案洞察', recommendations: '建议' };
              if (!Array.isArray(items) || items.length === 0) return null;
              return (
                <div key={key}>
                  <h4 className="text-xs font-bold text-primary mb-2">{labels[key] || key}</h4>
                  <ul className="space-y-1">
                    {items.map((item, i) => (
                      <li key={i} className="text-xs text-on-surface-variant flex items-start">
                        <span className="w-1.5 h-1.5 bg-primary rounded-full mt-1.5 mr-2 shrink-0"></span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Structured Recommendation */}
      {Object.keys(recommendation).length > 0 && (
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10">
          <h3 className="text-sm font-bold text-on-surface mb-4">结构化建议</h3>
          <div className="space-y-4">
            {Object.entries(recommendation).map(([key, items]) => {
              const labels = {
                objective_answers: '客观回答', cross_persona_consensus: '跨画像共识', cross_persona_differences: '跨画像差异',
                key_risks: '关键风险', opportunity_areas: '机会领域', recommended_actions: '推荐行动',
                copy_or_product_adjustments: '文案/产品调整', evidence_gaps: '证据缺口', confidence_assessment: '信心评估'
              };
              if (!Array.isArray(items) || items.length === 0) return null;
              return (
                <div key={key}>
                  <h4 className="text-xs font-bold text-primary mb-2">{labels[key] || key}</h4>
                  <ul className="space-y-1.5">
                    {items.map((item, i) => (
                      <li key={i} className="text-xs text-on-surface-variant pl-4 border-l-2 border-primary/20 py-1">{item}</li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
