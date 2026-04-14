import { useState, useEffect } from 'react';
import { api } from '../lib/api';

const STATUS_STYLES = {
  collecting: { label: '收集中', cls: 'bg-blue-100 text-blue-800' },
  running: { label: '进行中', cls: 'bg-primary-fixed text-on-primary-fixed' },
  completed: { label: '已完成', cls: 'bg-emerald-100 text-emerald-800' },
  error: { label: '异常', cls: 'bg-red-100 text-red-800' },
  awaiting_run_confirmation: { label: '待确认', cls: 'bg-amber-100 text-amber-800' },
  awaiting_clarification: { label: '待补充', cls: 'bg-amber-100 text-amber-800' },
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboardStats()
      .then(setStats)
      .catch(err => console.error('Dashboard stats error:', err))
      .finally(() => setLoading(false));
  }, []);

  const s = stats || {};
  const totalReports = s.total_reports ?? 0;
  const weeklyReviews = s.weekly_reviews ?? 0;
  const totalProjects = s.total_projects ?? 0;
  const avgHours = s.avg_completion_hours ?? 0;
  const recentTasks = s.recent_tasks ?? [];

  return (
    <div className="pt-8 pb-12 px-8 h-full">
      {/* Top Metrics */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-transparent hover:border-outline-variant/20 transition-all duration-300">
          <p className="text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-2">已生成报告数</p>
          <div className="flex items-end justify-between">
            <h3 className="text-3xl font-extrabold text-primary tracking-tight latex-stat">{loading ? '—' : totalReports}</h3>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-transparent hover:border-outline-variant/20 transition-all duration-300">
          <p className="text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-2">本周评审次数</p>
          <div className="flex items-end justify-between">
            <h3 className="text-3xl font-extrabold text-primary tracking-tight latex-stat">{loading ? '—' : weeklyReviews}</h3>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-transparent hover:border-outline-variant/20 transition-all duration-300">
          <p className="text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-2">总项目数</p>
          <div className="flex items-end justify-between">
            <h3 className="text-3xl font-extrabold text-primary tracking-tight latex-stat">{loading ? '—' : totalProjects}</h3>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-transparent hover:border-outline-variant/20 transition-all duration-300">
          <p className="text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-2">平均完成时长</p>
          <div className="flex items-end justify-between">
            <h3 className="text-3xl font-extrabold text-primary tracking-tight latex-stat">{loading ? '—' : `${avgHours}小时`}</h3>
          </div>
        </div>
      </section>

      {/* Quick Actions */}
      <section className="mb-10">
        <h4 className="text-sm font-bold text-on-surface-variant mb-4 flex items-center">
          <span className="material-symbols-outlined mr-2 text-primary" style={{fontVariationSettings: "'FILL' 1"}}>bolt</span>
          快速发起评审
        </h4>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <a href="/new?type=concept" className="group relative overflow-hidden bg-gradient-to-br from-primary to-primary-container p-4 rounded-xl text-white shadow-md hover:shadow-lg transition-all duration-300 active:scale-[0.98]">
            <div className="flex items-center justify-between relative z-10">
              <span className="text-sm font-bold">新建概念评审</span>
              <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">lightbulb</span>
            </div>
          </a>
          <a href="/new?type=packaging" className="bg-surface-container-highest p-4 rounded-xl text-on-surface font-bold text-sm flex items-center justify-between hover:bg-surface-container-high transition-colors duration-200">
            <span>新建包装评审</span>
            <span className="material-symbols-outlined text-slate-500">package_2</span>
          </a>
          <a href="/new?type=copywriting" className="bg-surface-container-highest p-4 rounded-xl text-on-surface font-bold text-sm flex items-center justify-between hover:bg-surface-container-high transition-colors duration-200">
            <span>新建文案评审</span>
            <span className="material-symbols-outlined text-slate-500">edit_note</span>
          </a>
          <a href="/new?type=ab_test" className="bg-surface-container-highest p-4 rounded-xl text-on-surface font-bold text-sm flex items-center justify-between hover:bg-surface-container-high transition-colors duration-200">
            <span>新建对比测试</span>
            <span className="material-symbols-outlined text-slate-500">splitscreen</span>
          </a>
        </div>
      </section>

      {/* Recent Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between px-2">
            <h4 className="text-lg font-bold text-on-surface">最近任务</h4>
            <a href="/docs" className="text-xs font-bold text-primary hover:underline">查看全部</a>
          </div>
          <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden border border-outline-variant/10">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-low/50 border-b border-outline-variant/10">
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">任务名称</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">测试对象</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">状态</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">创建时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {loading ? (
                  <tr><td colSpan={4} className="px-6 py-8 text-center text-sm text-slate-400">加载中……</td></tr>
                ) : recentTasks.length === 0 ? (
                  <tr><td colSpan={4} className="px-6 py-8 text-center text-sm text-slate-400">暂无任务，点击上方按钮创建第一个评审项目</td></tr>
                ) : recentTasks.map((task, i) => {
                  const st = STATUS_STYLES[task.status] || { label: task.status, cls: 'bg-slate-100 text-slate-600' };
                  return (
                    <tr key={i} className="hover:bg-surface-container-low transition-colors">
                      <td className="px-6 py-4">
                        <a href={`/projects/${task.session_id}`} className="text-sm font-semibold text-on-surface hover:text-primary hover:underline">
                          {task.name}
                        </a>
                      </td>
                      <td className="px-6 py-4"><span className="text-xs text-on-surface-variant">{task.product || '—'}</span></td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${st.cls}`}>{st.label}</span>
                      </td>
                      <td className="px-6 py-4"><span className="text-xs text-on-surface-variant latex-stat">{task.created_at}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Status Distribution */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <h4 className="text-lg font-bold text-on-surface">项目状态分布</h4>
          </div>
          <div className="bg-surface-container-lowest p-5 rounded-xl shadow-sm border border-outline-variant/10">
            {loading ? (
              <p className="text-sm text-slate-400">加载中……</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(s.status_distribution || {}).map(([status, count]) => {
                  const st = STATUS_STYLES[status] || { label: status };
                  return (
                    <div key={status} className="flex items-center justify-between">
                      <span className="text-xs font-medium text-on-surface-variant">{st.label}</span>
                      <span className="text-sm font-bold text-primary latex-stat">{count}</span>
                    </div>
                  );
                })}
                {Object.keys(s.status_distribution || {}).length === 0 && (
                  <p className="text-xs text-slate-400">暂无数据</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* FAB */}
      <div className="fixed bottom-8 right-8 z-50">
        <a href="/new" className="flex items-center bg-primary text-white px-6 py-4 rounded-full shadow-2xl hover:scale-105 active:scale-95 transition-all duration-300">
          <span className="material-symbols-outlined mr-2">add</span>
          <span className="text-sm font-bold">新建项目</span>
        </a>
      </div>
    </div>
  );
}
