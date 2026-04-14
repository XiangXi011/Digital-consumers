import { useProjectStatus } from '../hooks/useProjects';

const STAGE_LABELS = {
  collecting: '信息收集',
  planning: '规划中',
  running: '执行中',
  synthesizing: '结果综合中',
  awaiting_clarification: '待补充信息',
  awaiting_run_confirmation: '待运行确认',
  completed: '已完成',
  error: '异常',
};

const STATUS_COLORS = {
  collecting: 'bg-blue-500',
  planning: 'bg-amber-500',
  running: 'bg-primary',
  synthesizing: 'bg-purple-500',
  completed: 'bg-emerald-500',
  error: 'bg-red-500',
};

export default function ProjectStatus({ sessionId }) {
  const { data: status, isLoading } = useProjectStatus(sessionId);

  if (isLoading || !status) {
    return (
      <div className="flex items-center gap-2 text-xs text-on-surface-variant">
        <div className="w-4 h-4 rounded-full border-2 border-slate-200 border-t-primary animate-spin" />
        加载状态...
      </div>
    );
  }

  const progress = Math.max(0, Math.min(100, status.progress ?? 0));
  const stage = STAGE_LABELS[status.current_stage] || status.current_stage;
  const colorCls = STATUS_COLORS[status.current_stage] || 'bg-slate-400';

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${colorCls} ${status.current_stage === 'running' ? 'animate-pulse' : ''}`} />
          <span className="text-sm font-semibold text-on-surface">{stage}</span>
        </div>
        <span className="text-xs font-bold text-on-surface-variant">{progress}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full transition-all duration-700 ${colorCls}`}
          style={{ width: `${progress}%` }}
        />
      </div>
      {status.last_error && (
        <p className="text-xs text-red-600">{status.last_error}</p>
      )}
    </div>
  );
}
