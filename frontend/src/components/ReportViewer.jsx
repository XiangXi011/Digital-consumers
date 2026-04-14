import { useState } from 'react';

const TABS = [
  { key: 'summary', label: '摘要', icon: 'summarize' },
  { key: 'personas', label: '画像反馈', icon: 'person' },
  { key: 'discussion', label: '焦点讨论', icon: 'forum' },
  { key: 'evidence', label: '证据', icon: 'fact_check' },
  { key: 'metrics', label: '指标', icon: 'bar_chart' },
];

export default function ReportViewer({ report }) {
  const [activeTab, setActiveTab] = useState('summary');

  if (!report) {
    return <p className="text-sm text-on-surface-variant">暂无报告数据</p>;
  }

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-outline-variant/10 pb-0">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1 px-4 py-2 text-xs font-bold rounded-t-lg transition-colors ${
              activeTab === tab.key
                ? 'bg-primary/10 text-primary border-b-2 border-primary'
                : 'text-on-surface-variant hover:bg-surface-container'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[200px]">
        {activeTab === 'summary' && <SummaryTab report={report} />}
        {activeTab === 'personas' && <PersonasTab report={report} />}
        {activeTab === 'discussion' && <DiscussionTab report={report} />}
        {activeTab === 'evidence' && <EvidenceTab report={report} />}
        {activeTab === 'metrics' && <MetricsTab report={report} />}
      </div>
    </div>
  );
}

function SummaryTab({ report }) {
  const summary = report.research_summary || {};
  return (
    <div className="space-y-4">
      <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10">
        <h4 className="text-sm font-bold text-on-surface mb-3">核心发现</h4>
        <p className="text-sm text-on-surface-variant leading-relaxed">
          {summary.core_findings || summary.summary || '暂无摘要'}
        </p>
      </div>
      {report.structured_recommendation && (
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10">
          <h4 className="text-sm font-bold text-on-surface mb-3">结构化建议</h4>
          <pre className="text-xs text-on-surface-variant whitespace-pre-wrap">
            {JSON.stringify(report.structured_recommendation, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function PersonasTab({ report }) {
  const voices = report.consumer_voice || [];
  return (
    <div className="space-y-3">
      {voices.map((v, i) => (
        <div key={i} className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-bold text-on-surface">{v.persona_name || `画像 ${i + 1}`}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              v.purchase_intent === 'buy' ? 'bg-emerald-100 text-emerald-800' :
              v.purchase_intent === 'reject' ? 'bg-red-100 text-red-800' :
              'bg-amber-100 text-amber-800'
            }`}>
              {v.purchase_intent || v.stance || '—'}
            </span>
          </div>
          <p className="text-xs text-on-surface-variant">{v.voice_line || ''}</p>
          {v.rubric_scores && Object.keys(v.rubric_scores).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(v.rubric_scores).map(([dim, score]) => (
                <span key={dim} className="text-xs bg-surface-container px-2 py-0.5 rounded text-on-surface-variant">
                  {dim}: {score}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
      {voices.length === 0 && <p className="text-xs text-slate-400 text-center py-8">暂无画像反馈</p>}
    </div>
  );
}

function DiscussionTab({ report }) {
  const discussion = report.group_discussion;
  if (!discussion || discussion.status === 'skipped') {
    return (
      <div className="text-center py-12 text-sm text-on-surface-variant">
        <span className="material-symbols-outlined text-4xl text-slate-300 block mb-3">forum</span>
        本次评审未启用焦点小组讨论
      </div>
    );
  }
  if (discussion.status === 'failed') {
    return <p className="text-xs text-red-600 py-4">讨论执行失败: {discussion.reason}</p>;
  }

  const rounds = discussion.discussion_rounds || [];
  return (
    <div className="space-y-6">
      {rounds.map((round, ri) => (
        <div key={ri} className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
          <h4 className="text-sm font-bold text-on-surface mb-3">
            第{round.round || ri + 1}轮 — {round.topic || '讨论'}
          </h4>
          <div className="space-y-2">
            {(round.exchanges || []).map((ex, ei) => (
              <div key={ei} className="flex gap-3">
                <span className="text-xs font-bold text-primary whitespace-nowrap mt-0.5">{ex.speaker}:</span>
                <p className="text-xs text-on-surface-variant flex-1">{ex.statement}</p>
              </div>
            ))}
          </div>
        </div>
      ))}

      {discussion.key_conflicts?.length > 0 && (
        <div className="bg-red-50 p-4 rounded-xl border border-red-100">
          <h5 className="text-xs font-bold text-red-800 mb-2">关键分歧</h5>
          <ul className="list-disc list-inside space-y-1">
            {discussion.key_conflicts.map((c, i) => (
              <li key={i} className="text-xs text-red-700">{c}</li>
            ))}
          </ul>
        </div>
      )}
      {discussion.emerging_consensus?.length > 0 && (
        <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-100">
          <h5 className="text-xs font-bold text-emerald-800 mb-2">达成共识</h5>
          <ul className="list-disc list-inside space-y-1">
            {discussion.emerging_consensus.map((c, i) => (
              <li key={i} className="text-xs text-emerald-700">{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function EvidenceTab({ report }) {
  const atoms = report.evidence_atoms || [];
  return (
    <div className="space-y-2">
      {atoms.slice(0, 50).map((e, i) => (
        <div key={i} className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant/10 flex items-start gap-3">
          <span className={`text-xs font-bold px-2 py-0.5 rounded mt-0.5 ${
            e.is_minority ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
          }`}>
            {e.is_minority ? '少数' : '多数'}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-on-surface font-semibold">{e.persona_name} — {e.field}</p>
            <p className="text-xs text-on-surface-variant truncate">{e.value}</p>
          </div>
        </div>
      ))}
      {atoms.length === 0 && <p className="text-xs text-slate-400 text-center py-8">暂无证据数据</p>}
    </div>
  );
}

function MetricsTab({ report }) {
  const metrics = report.meta?.evaluation_metrics || {};
  const entries = Object.entries(metrics);
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {entries.map(([key, value]) => (
        <div key={key} className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/10">
          <p className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">{key}</p>
          <p className="text-xl font-extrabold text-primary">
            {typeof value === 'number' ? (Number.isInteger(value) ? value : value.toFixed(2)) : String(value)}
          </p>
        </div>
      ))}
      {entries.length === 0 && <p className="text-xs text-slate-400 col-span-full text-center py-8">暂无指标数据</p>}
    </div>
  );
}
