from html import escape
from typing import Any, Dict, List


class HTMLReportRenderer:
    def render(self, report: Dict[str, Any]) -> str:
        summary = report.get("executive_summary", {})
        input_summary = report.get("input_summary", {})
        segment_opportunity = report.get("segment_opportunity", {})
        top_segments = segment_opportunity.get("top_segments", [])
        weak_segments = segment_opportunity.get("weak_segments", [])
        full_segments = segment_opportunity.get("full_table", []) or top_segments + weak_segments
        reasons = report.get("reasons_to_buy", [])
        barriers = report.get("barriers", {}).get("top_barriers", [])
        diagnosis = report.get("diagnosis", {})
        voice = report.get("voice_of_consumer", {})
        action_plan = report.get("action_plan", {})
        report_boundary = report.get("report_boundary", {})
        completeness = report_boundary.get("input_completeness", self._fallback_completeness(report))

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(report['meta']['concept_name'])} 报告</title>
  <style>
    :root {{
      --bg: #eef3fb;
      --card: #ffffff;
      --text: #18212f;
      --muted: #5d6b82;
      --line: #dbe5f4;
      --brand: #2364d2;
      --brand-soft: #dfeafe;
      --accent: #ff8552;
      --accent-soft: #fff1ea;
      --success: #168d62;
      --success-soft: #def7ec;
      --warning: #cc7a00;
      --warning-soft: #fff2d8;
      --danger: #cf3a3a;
      --danger-soft: #fde7e7;
      --ink-soft: #f8fbff;
      --shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
      --radius-xl: 24px;
      --radius-lg: 18px;
      --radius-md: 14px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top right, rgba(35, 100, 210, 0.10), transparent 28%),
        radial-gradient(circle at left 20%, rgba(255, 133, 82, 0.10), transparent 24%),
        var(--bg);
      line-height: 1.65;
    }}
    .page {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 28px 22px 54px;
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      border-radius: 30px;
      padding: 38px 40px 34px;
      color: #fff;
      background: linear-gradient(140deg, #0f4cbd 0%, #2364d2 45%, #3d87ff 100%);
      box-shadow: var(--shadow);
    }}
    .hero::before {{
      content: "";
      position: absolute;
      right: -100px;
      top: -80px;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.12);
    }}
    .hero::after {{
      content: "";
      position: absolute;
      left: -70px;
      bottom: -120px;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.08);
    }}
    .hero h1 {{
      margin: 0;
      font-size: 34px;
      line-height: 1.15;
      position: relative;
      z-index: 1;
    }}
    .hero-subtitle {{
      position: relative;
      z-index: 1;
      margin-top: 12px;
      max-width: 900px;
      font-size: 16px;
      opacity: 0.94;
    }}
    .meta-row, .tag-row {{
      position: relative;
      z-index: 1;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .meta-chip, .tag {{
      display: inline-flex;
      align-items: center;
      padding: 9px 14px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
    }}
    .meta-chip {{
      background: rgba(255, 255, 255, 0.14);
      border: 1px solid rgba(255, 255, 255, 0.16);
    }}
    .tag-brand {{ background: var(--brand-soft); color: var(--brand); }}
    .tag-success {{ background: var(--success-soft); color: var(--success); }}
    .tag-warning {{ background: var(--warning-soft); color: var(--warning); }}
    .tag-danger {{ background: var(--danger-soft); color: var(--danger); }}
    .tag-accent {{ background: var(--accent-soft); color: var(--accent); }}
    .section {{
      margin-top: 24px;
    }}
    .section-title {{
      margin: 0 0 14px;
      font-size: 21px;
      font-weight: 800;
      letter-spacing: 0.01em;
    }}
    .card {{
      background: var(--card);
      border: 1px solid rgba(219, 229, 244, 0.95);
      border-radius: var(--radius-xl);
      padding: 24px;
      box-shadow: var(--shadow);
    }}
    .summary-card {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 18px;
      align-items: stretch;
    }}
    .summary-main {{
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      border: 1px solid #e6eefb;
      border-radius: var(--radius-lg);
      padding: 20px 22px;
    }}
    .summary-side {{
      display: grid;
      gap: 14px;
    }}
    .mini-panel {{
      background: var(--ink-soft);
      border: 1px solid #e7eef9;
      border-radius: var(--radius-lg);
      padding: 16px 18px;
    }}
    .mini-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .mini-value {{
      font-size: 18px;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      gap: 18px;
    }}
    .grid-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .grid-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .kpi {{
      background: var(--card);
      border: 1px solid #e8eef8;
      border-radius: var(--radius-lg);
      padding: 20px;
      box-shadow: var(--shadow);
    }}
    .kpi-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .kpi-value {{
      font-size: 32px;
      font-weight: 800;
      line-height: 1.05;
    }}
    .kpi-note {{
      margin-top: 8px;
      font-size: 13px;
      color: var(--muted);
    }}
    .diag-card, .action-card, .quote-column {{
      background: var(--ink-soft);
      border: 1px solid #e6eef8;
      border-radius: var(--radius-lg);
      padding: 18px;
    }}
    .diag-card h3, .action-card h3, .quote-column h3, .info-card h3 {{
      margin: 0 0 12px;
      font-size: 17px;
    }}
    .info-card {{
      background: var(--ink-soft);
      border: 1px solid #e6eef8;
      border-radius: var(--radius-lg);
      padding: 18px;
    }}
    .list {{
      margin: 0;
      padding-left: 18px;
    }}
    .list li {{
      margin-bottom: 10px;
    }}
    .segment-table {{
      display: grid;
      gap: 14px;
    }}
    .segment-row {{
      display: grid;
      grid-template-columns: 220px 110px 1fr;
      gap: 14px;
      align-items: center;
      padding: 16px 18px;
      border-radius: var(--radius-md);
      border: 1px solid #e6edf8;
      background: #fbfdff;
    }}
    .segment-name {{
      font-weight: 700;
    }}
    .segment-score {{
      font-size: 24px;
      font-weight: 800;
      color: var(--brand);
      text-align: center;
    }}
    .segment-reason {{
      color: #314156;
      font-size: 14px;
    }}
    .progress {{
      height: 8px;
      width: 100%;
      margin-top: 8px;
      border-radius: 999px;
      overflow: hidden;
      background: #dfe7f5;
    }}
    .progress-bar {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #2364d2 0%, #57a5ff 100%);
    }}
    .quote-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .quote-item {{
      background: #ffffff;
      border: 1px solid #e7edf8;
      border-radius: var(--radius-md);
      padding: 14px;
      margin-bottom: 12px;
    }}
    .quote-text {{
      font-size: 14px;
      color: #1e293b;
      margin-bottom: 10px;
    }}
    .quote-meta {{
      font-size: 12px;
      color: var(--muted);
    }}
    .boundary-card {{
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      border: 1px solid #e3ebf8;
      border-radius: var(--radius-lg);
      padding: 18px;
    }}
    .footer {{
      margin-top: 28px;
      text-align: center;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 980px) {{
      .summary-card, .grid-4, .grid-3, .grid-2, .quote-grid, .segment-row {{
        grid-template-columns: 1fr;
      }}
      .segment-score {{
        text-align: left;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{escape(report['meta']['concept_name'])}</h1>
      <div class="hero-subtitle">{escape(summary.get('headline', '报告已生成。'))}</div>
      <div class="meta-row">
        <span class="meta-chip">品牌：{escape(report['meta'].get('brand', '未提供'))}</span>
        <span class="meta-chip">生成时间：{escape(report['meta'].get('generated_at', '未提供'))}</span>
        <span class="meta-chip">样本数：{report['meta'].get('total_personas', 0)}</span>
        <span class="meta-chip">报告类型：单方案概念验证</span>
      </div>
      <div class="tag-row">
        <span class="tag tag-success">业务建议：{escape(summary.get('business_recommendation', summary.get('recommendation', '未提供')))}</span>
        <span class="tag tag-brand">结论可信度：{escape(summary.get('confidence_level', '中'))}</span>
        <span class="tag tag-warning">关键风险：{escape(summary.get('key_risk', '待补充'))}</span>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">一句话结论</h2>
      <div class="card summary-card">
        <div class="summary-main">
          <div class="mini-label">当前结论</div>
          <div class="mini-value">{escape(summary.get('headline', '待补充'))}</div>
          <p>{escape(summary.get('confidence_reason', '当前已基于可用资料生成业务结论。'))}</p>
        </div>
        <div class="summary-side">
          <div class="mini-panel">
            <div class="mini-label">业务建议</div>
            <div class="mini-value">{escape(summary.get('business_recommendation', summary.get('recommendation', '未提供')))}</div>
          </div>
          <div class="mini-panel">
            <div class="mini-label">高潜人群</div>
            <div class="mini-value">{escape(self._segment_name(top_segments, 0))}</div>
          </div>
          <div class="mini-panel">
            <div class="mini-label">可信度等级</div>
            <div class="mini-value">{escape(summary.get('confidence_level', '中'))}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">结论依据拆解</h2>
      <div class="grid grid-3">
        {self._diagnosis_cards(diagnosis.get('decision_drivers', []))}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">核心指标概览</h2>
      <div class="grid grid-4">
        <div class="kpi">
          <div class="kpi-label">模拟购买意向</div>
          <div class="kpi-value">{report['purchase_intent'].get('average_intention', 0):.0%}</div>
          <div class="kpi-note">基于数字消费者样本的整体意向</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">预计转化倾向</div>
          <div class="kpi-value">{report['purchase_intent'].get('estimated_conversion_rate', 0)}%</div>
          <div class="kpi-note">规则引擎综合估算</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">价格阻力占比</div>
          <div class="kpi-value">{report.get('barriers', {}).get('price_concern_share', 0):.0%}</div>
          <div class="kpi-note">价格相关顾虑占比</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">资料完整度</div>
          <div class="kpi-value">{completeness:.0%}</div>
          <div class="kpi-note">输入信息越完整，结论越稳健</div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">输入信息回顾</h2>
      <div class="grid grid-2">
        <div class="info-card">
          <h3>任务与基础信息</h3>
          <ul class="list">
            <li><strong>品类：</strong>{escape(str(input_summary.get('category', '未提供')))}</li>
            <li><strong>价格：</strong>{escape(str(input_summary.get('price', '未提供')))}</li>
            <li><strong>目标渠道：</strong>{escape(' / '.join(input_summary.get('target_channels', [])) or '未提供')}</li>
            <li><strong>竞品参考：</strong>{escape(' / '.join(input_summary.get('competitive_anchors', [])) or '未提供')}</li>
          </ul>
        </div>
        <div class="info-card">
          <h3>核心卖点与包装</h3>
          <ul class="list">
            {self._list_items(input_summary.get('core_claims', []))}
          </ul>
          <p><strong>包装摘要：</strong>{escape(str(input_summary.get('packaging_summary', '未提供')))}</p>
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">人群接受度与原因解释</h2>
      <div class="card">
        <div class="segment-table">
          {self._segment_rows(full_segments[:8])}
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">价值主张诊断</h2>
      <div class="grid grid-3">
        <div class="diag-card">
          <h3>最强买点</h3>
          <ul class="list">{self._list_items(reasons)}</ul>
        </div>
        <div class="diag-card">
          <h3>主要障碍</h3>
          <ul class="list">{self._list_items(barriers)}</ul>
        </div>
        <div class="diag-card">
          <h3>价值主张冲突</h3>
          <ul class="list">{self._list_items(diagnosis.get('value_proposition_conflicts', []))}</ul>
        </div>
      </div>
      <div class="card" style="margin-top: 16px;">
        <h3 style="margin-top:0;">竞品与判断边界</h3>
        <ul class="list">{self._list_items(diagnosis.get('competitive_limitations', []))}</ul>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">原声摘录</h2>
      <div class="quote-grid">
        {self._quote_column('支持者原声', voice.get('supporters', []), 'tag-success')}
        {self._quote_column('犹豫者原声', voice.get('hesitant', []), 'tag-warning')}
        {self._quote_column('拒绝者原声', voice.get('rejecting', []), 'tag-danger')}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">下一步动作建议</h2>
      <div class="grid grid-3">
        {self._action_column('立即可做', action_plan.get('immediate_actions', []))}
        {self._action_column('下一轮测试前要补', action_plan.get('next_round_prerequisites', []))}
        {self._action_column('建议下一轮测试什么', action_plan.get('recommended_next_tests', []))}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">说明与可信度边界</h2>
      <div class="grid grid-2">
        <div class="boundary-card">
          <h3>可信度与完整度</h3>
          <div class="tag-row">
            <span class="tag tag-brand">结论可信度：{escape(summary.get('confidence_level', '中'))}</span>
            <span class="tag tag-accent">资料完整度：{completeness:.0%}</span>
            <span class="tag tag-warning">缺失项数：{len(report_boundary.get('missing_fields', []))}</span>
          </div>
          <p>{escape(summary.get('confidence_reason', '待补充'))}</p>
        </div>
        <div class="boundary-card">
          <h3>适用范围与说明</h3>
          <ul class="list">
            {self._list_items(report_boundary.get('credibility_notes', []))}
          </ul>
          <p><strong>缺失项：</strong>{escape(' / '.join(report_boundary.get('missing_fields', [])) or '无')}</p>
        </div>
      </div>
    </section>

    <div class="footer">数字消费者洞察与概念测试平台 · 业务版 HTML 报告</div>
  </div>
</body>
</html>
"""

    def _segment_name(self, segments: List[Dict[str, Any]], index: int) -> str:
        if index >= len(segments):
            return "待补充"
        return str(segments[index].get("segment", "待补充"))

    def _list_items(self, items: List[Any]) -> str:
        if not items:
            return "<li>当前暂无可展示内容</li>"
        return "".join(f"<li>{escape(str(item))}</li>" for item in items)

    def _diagnosis_cards(self, items: List[str]) -> str:
        cards = []
        for index, item in enumerate(items[:3], start=1):
            cards.append(
                f"""
                <div class="diag-card">
                  <h3>核心原因 {index}</h3>
                  <p>{escape(str(item))}</p>
                </div>
                """
            )
        if not cards:
            cards.append(
                """
                <div class="diag-card">
                  <h3>核心原因</h3>
                  <p>当前暂无足够信号拆解结论原因。</p>
                </div>
                """
            )
        return "".join(cards)

    def _segment_rows(self, items: List[Dict[str, Any]]) -> str:
        rows = []
        for item in items:
            score = int(round(item.get("avg_intention", 0) * 100))
            rows.append(
                f"""
                <div class="segment-row">
                  <div>
                    <div class="segment-name">{escape(str(item.get('segment', '未提供')))}</div>
                    <div class="progress"><div class="progress-bar" style="width: {score}%;"></div></div>
                  </div>
                  <div class="segment-score">{score}%</div>
                  <div class="segment-reason">{escape(str(item.get('why_high_or_low', '待补充')))}</div>
                </div>
                """
            )
        return "".join(rows)

    def _quote_column(self, title: str, items: List[Dict[str, Any]], tag_class: str) -> str:
        if not items:
            items = [{"agent_name": "系统", "segment": "无", "stance_label": title, "reason_tag": "无", "quote": "当前没有可展示的原声。"}]

        cards = []
        for item in items[:2]:
            cards.append(
                f"""
                <div class="quote-item">
                  <div class="quote-text">{escape(str(item.get('quote', '')))}</div>
                  <div class="quote-meta">{escape(str(item.get('agent_name', '匿名')))} · {escape(str(item.get('segment', '未知人群')))}</div>
                  <div class="tag-row" style="margin-top:10px;">
                    <span class="tag {tag_class}">{escape(str(item.get('stance_label', '未标注')))}</span>
                    <span class="tag tag-brand">原因：{escape(str(item.get('reason_tag', '未标注')))}</span>
                  </div>
                </div>
                """
            )

        return f"""
        <div class="quote-column">
          <h3>{escape(title)}</h3>
          {''.join(cards)}
        </div>
        """

    def _action_column(self, title: str, items: List[str]) -> str:
        return f"""
        <div class="action-card">
          <h3>{escape(title)}</h3>
          <ul class="list">{self._list_items(items)}</ul>
        </div>
        """

    def _fallback_completeness(self, report: Dict[str, Any]) -> float:
        missing_fields = report.get("input_summary", {}).get("missing_fields", [])
        total = 14
        return max(0.0, (total - len(missing_fields)) / total)
