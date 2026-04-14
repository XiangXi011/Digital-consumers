import { useParams } from 'react-router-dom';
import { useProject } from '../hooks/useProjects';
import ProjectStatus from '../components/ProjectStatus';
import ReportViewer from '../components/ReportViewer';

export default function ProjectDetail() {
  const { id } = useParams();
  const { data: project, isLoading, error } = useProject(id);

  if (isLoading) {
    return (
      <div className="pt-8 pb-12 px-8 h-full flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-slate-200 border-t-primary animate-spin" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="pt-8 pb-12 px-8 h-full text-center">
        <p className="text-sm text-red-600">加载项目失败: {error?.message || '项目不存在'}</p>
        <a href="/" className="text-xs text-primary font-bold hover:underline mt-2 inline-block">返回首页</a>
      </div>
    );
  }

  return (
    <div className="pt-8 pb-12 px-8 h-full max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <a href="/" className="text-xs text-on-surface-variant hover:text-primary mb-2 inline-flex items-center">
          <span className="material-symbols-outlined text-[14px] mr-1">arrow_back</span>
          返回项目列表
        </a>
        <h1 className="text-2xl font-extrabold text-on-surface tracking-tight mt-1">
          {project.name || project.session_id}
        </h1>
        <p className="text-xs text-on-surface-variant mt-1">
          {project.project_type} · {project.created_at}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Status & Info */}
        <div className="space-y-4">
          <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
            <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">运行状态</h3>
            <ProjectStatus sessionId={id} />
          </div>

          {project.business_brief && (
            <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
              <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">Business Brief</h3>
              <pre className="text-xs text-on-surface-variant whitespace-pre-wrap max-h-60 overflow-y-auto">
                {typeof project.business_brief === 'string'
                  ? project.business_brief
                  : JSON.stringify(project.business_brief, null, 2)}
              </pre>
            </div>
          )}

          {project.research_plan && (
            <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
              <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">研究计划</h3>
              <pre className="text-xs text-on-surface-variant whitespace-pre-wrap max-h-60 overflow-y-auto">
                {JSON.stringify(project.research_plan, null, 2)}
              </pre>
            </div>
          )}

          {project.attachment_urls?.length > 0 && (
            <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/10">
              <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">附件</h3>
              <div className="space-y-2">
                {project.attachment_urls.map((url, i) => (
                  <a key={i} href={url} target="_blank" rel="noreferrer"
                    className="flex items-center text-xs text-primary hover:underline">
                    <span className="material-symbols-outlined text-[14px] mr-1">attach_file</span>
                    {project.attachments?.[i] || url.split('/').pop()}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Report (once available) */}
        <div className="lg:col-span-2">
          {project.has_report && project.json_report_path ? (
            <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10">
              <h3 className="text-sm font-bold text-on-surface mb-4">评审报告</h3>
              <ReportViewerFromPath jsonPath={project.json_report_path} />
            </div>
          ) : (
            <div className="bg-surface-container-lowest p-12 rounded-xl border border-outline-variant/10 text-center">
              <span className="material-symbols-outlined text-4xl text-slate-300 block mb-3">description</span>
              <p className="text-sm text-on-surface-variant">报告尚未生成</p>
              <p className="text-xs text-slate-400 mt-1">项目运行完成后将自动显示报告</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportViewerFromPath({ jsonPath }) {
  // In production, json_report_path is served under /outputs/
  const url = jsonPath.startsWith('/') ? jsonPath : `/outputs/${jsonPath}`;
  return <ReportViewerLazy url={url} />;
}

import { useState, useEffect } from 'react';

function ReportViewerLazy({ url }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(url, { headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` } })
      .then(r => r.json())
      .then(data => { if (!cancelled) { setReport(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setReport(null); setLoading(false); } });
    return () => { cancelled = true; };
  }, [url]);

  if (loading) return <p className="text-sm text-on-surface-variant">加载报告中...</p>;
  if (!report) return <p className="text-sm text-red-600">报告加载失败</p>;

  return <ReportViewer report={report} />;
}
