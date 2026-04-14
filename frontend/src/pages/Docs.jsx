import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function Docs() {
  const [reports, setReports] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const pageSize = 10;

  const loadReports = (p = 1, q = '') => {
    setLoading(true);
    api.getReports({ page: p, page_size: pageSize, search: q })
      .then(res => {
        setReports(res.reports || []);
        setTotal(res.total || 0);
        setPage(res.page || p);
      })
      .catch(err => console.error('Failed to load reports:', err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadReports(); }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    loadReports(1, search);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="pt-8 pb-12 px-8 h-full max-w-6xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-2xl font-extrabold text-on-surface tracking-tight mb-2">报告中心</h2>
          <p className="text-sm text-on-surface-variant">查看、下载或分享已生成的评审分析报告</p>
        </div>
        <form onSubmit={handleSearch} className="flex space-x-3">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-[18px]">search</span>
            <input type="text" placeholder="搜索报告..." aria-label="搜索报告"
              className="pl-10 pr-4 py-2 bg-white rounded-lg border border-outline-variant/30 focus:border-primary focus:ring-1 focus:ring-primary text-sm w-64 outline-none"
              value={search} onChange={e => setSearch(e.target.value)}
            />
          </div>
          <button type="submit" className="flex items-center space-x-2 px-4 py-2 bg-white border border-outline-variant/30 rounded-lg text-sm font-bold text-on-surface hover:bg-slate-50 transition-colors">
            <span className="material-symbols-outlined text-[18px]">search</span>
            <span>搜索</span>
          </button>
        </form>
      </div>

      <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/10 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-low/50 border-b border-outline-variant/10">
              <th className="px-6 py-4 text-xs font-bold text-on-surface-variant uppercase tracking-widest w-16">ID</th>
              <th className="px-6 py-4 text-xs font-bold text-on-surface-variant uppercase tracking-widest">报告名称</th>
              <th className="px-6 py-4 text-xs font-bold text-on-surface-variant uppercase tracking-widest">评审类型</th>
              <th className="px-6 py-4 text-xs font-bold text-on-surface-variant uppercase tracking-widest">生成时间</th>
              <th className="px-6 py-4 text-xs font-bold text-on-surface-variant uppercase tracking-widest text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-sm text-slate-400">加载中...</td></tr>
            ) : reports.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-8 text-center text-sm text-slate-400">暂无报告</td></tr>
            ) : reports.map((report) => (
              <tr key={report.id} className="hover:bg-surface-container-low transition-colors group">
                <td className="px-6 py-4 text-xs font-bold text-slate-400 latex-stat">{report.id.slice(0, 8)}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <span className="material-symbols-outlined text-tertiary-container mr-3" style={{fontVariationSettings: "'FILL' 1"}}>description</span>
                    <span className="text-sm font-bold text-on-surface">{report.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-secondary-fixed text-on-secondary-fixed">
                    {report.report_type || '未分类'}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs text-on-surface-variant latex-stat">{report.date}</td>
                <td className="px-6 py-4 text-right space-x-2">
                  <a href={`/reports?id=${report.id}`} aria-label="查看详情" className="p-3 text-primary hover:bg-primary/10 rounded-lg transition-colors inline-block" title="查看详情">
                    <span className="material-symbols-outlined" aria-hidden="true">visibility</span>
                  </a>
                  {report.has_html && (
                    <a href={api.getReportHtmlUrl(report.id)} target="_blank" rel="noopener noreferrer"
                      aria-label="打开HTML报告" className="p-3 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors inline-block" title="HTML 报告">
                      <span className="material-symbols-outlined" aria-hidden="true">open_in_new</span>
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="px-6 py-4 border-t border-outline-variant/10 flex items-center justify-between bg-surface-container-lowest">
          <span className="text-xs text-slate-500">
            显示 {Math.min((page - 1) * pageSize + 1, total)} 到 {Math.min(page * pageSize, total)} 条，共 {total} 条
          </span>
          <div className="flex space-x-1">
            <button onClick={() => loadReports(page - 1, search)} disabled={page <= 1}
              className="px-3 py-1 text-xs font-bold text-slate-400 bg-slate-50 rounded hover:bg-slate-100 disabled:opacity-50">上一页</button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(p => (
              <button key={p} onClick={() => loadReports(p, search)}
                className={`px-3 py-1 text-xs font-bold rounded ${p === page ? 'text-white bg-primary shadow-sm' : 'text-slate-600 bg-white hover:bg-slate-50'}`}>
                {p}
              </button>
            ))}
            <button onClick={() => loadReports(page + 1, search)} disabled={page >= totalPages}
              className="px-3 py-1 text-xs font-bold text-slate-600 bg-white hover:bg-slate-50 rounded disabled:opacity-50">下一页</button>
          </div>
        </div>
      </div>
    </div>
  );
}
