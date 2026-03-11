from html import escape
from typing import Any, Dict, List


class HTMLReportRenderer:
    def render(self, report: Dict[str, Any]) -> str:
        meta = report.get("meta", {})
        brief = report.get("research_brief", {})
        consumer_voice = report.get("consumer_voice", [])
        research_summary = report.get("research_summary", {})
        appendix = report.get("appendix", {})

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>妈妈定性研究报告</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --ink: #1f1a17;
      --muted: #6d6258;
      --line: #e6ddd0;
      --accent: #bf5b2c;
      --accent-soft: #f7e6db;
      --olive: #707d49;
      --olive-soft: #edf1e2;
      --shadow: 0 14px 36px rgba(62, 42, 26, 0.08);
      --radius: 24px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(191, 91, 44, 0.10), transparent 28%),
        radial-gradient(circle at left 15%, rgba(112, 125, 73, 0.12), transparent 24%),
        var(--bg);
      color: var(--ink);
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.6;
    }}
    .page {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 28px 22px 56px;
    }}
    .hero, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 30px 32px;
      background: linear-gradient(135deg, #fff8f2 0%, #fffdf8 100%);
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ font-size: 34px; margin-bottom: 10px; }}
    h2 {{ font-size: 24px; margin: 26px 0 14px; }}
    h3 {{ font-size: 18px; margin-bottom: 10px; }}
    .subtitle {{ color: var(--muted); max-width: 860px; }}
    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 8px 14px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
    }}
    .chip-accent {{ background: var(--accent-soft); color: var(--accent); }}
    .chip-olive {{ background: var(--olive-soft); color: var(--olive); }}
    .grid {{
      display: grid;
      gap: 18px;
    }}
    .grid-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .brief-card, .persona-card, .summary-card {{
      padding: 20px 22px;
    }}
    .brief-item {{
      margin-bottom: 14px;
    }}
    .label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 15px;
    }}
    .persona-card {{
      background: #fffdf8;
    }}
    .persona-meta {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
    }}
    .quote {{
      padding: 14px 16px;
      border-radius: 18px;
      background: #faf5ee;
      border: 1px solid #eee0cf;
      font-size: 15px;
      margin-bottom: 12px;
    }}
    .tag-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .tag {{
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      background: #f6efe5;
      color: var(--ink);
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .footer {{
      margin-top: 22px;
      text-align: center;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 960px) {{
      .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>妈妈定性研究报告</h1>
      <p class="subtitle">{escape(self._brief_value(brief.get("user_question")) or "围绕指定研究问题，输出妈妈原声和研究助理总结。")}</p>
      <div class="chip-row">
        <span class="chip chip-accent">模式：{escape(self._mode_label(meta.get("mode", "")))}</span>
        <span class="chip chip-olive">研究问题：{escape(self._question_label(meta.get("question_type", "")))}</span>
        <span class="chip chip-accent">生成时间：{escape(str(meta.get("generated_at", "未提供")))}</span>
        <span class="chip chip-olive">覆盖画像：{escape(str(meta.get("total_agents", 0)))}</span>
      </div>
    </section>

    <h2>任务概览</h2>
    <section class="grid grid-2">
      <div class="card brief-card">
        <div class="brief-item">
          <div class="label">用户问题</div>
          <div class="value">{escape(self._brief_value(brief.get("user_question")))}</div>
        </div>
        <div class="brief-item">
          <div class="label">产品信息</div>
          <div class="value">{escape(self._brief_value(brief.get("product_info")))}</div>
        </div>
        <div class="brief-item">
          <div class="label">文案或卖点</div>
          <div class="value">{escape(self._brief_value(brief.get("copy_material")))}</div>
        </div>
      </div>
      <div class="card brief-card">
        <div class="brief-item">
          <div class="label">背景资料</div>
          <div class="value">{escape(self._brief_value(brief.get("background_material")))}</div>
        </div>
        <div class="brief-item">
          <div class="label">追问上下文</div>
          <div class="value">{escape(self._brief_value(appendix.get("follow_up_context")))}</div>
        </div>
        <div class="brief-item">
          <div class="label">附件</div>
          <div class="value">{escape(", ".join(appendix.get("attachments", [])) or "无")}</div>
        </div>
      </div>
    </section>

    <h2>消费者原声</h2>
    <section class="grid grid-2">
      {self._persona_cards(consumer_voice)}
    </section>

    <h2>研究总结</h2>
    <section class="grid grid-3">
      {self._summary_block("共识", research_summary.get("consensus", []))}
      {self._summary_block("分歧", research_summary.get("differences", []))}
      {self._summary_block("痛点", research_summary.get("pain_points", []))}
      {self._summary_block("驱动", research_summary.get("drivers", []))}
      {self._summary_block("障碍", research_summary.get("barriers", []))}
      {self._summary_block("启发", research_summary.get("copy_insights", []))}
    </section>

    <h2>建议</h2>
    <section class="grid grid-2">
      {self._summary_block("建议", research_summary.get("recommendations", []))}
      <div class="card summary-card">
        <h3>输出边界</h3>
        <ul>
          <li>本报告基于既有妈妈画像生成，不等同于真实消费者访谈。</li>
          <li>如需更深分析，建议在当前会话继续追问具体画像或具体表达。</li>
        </ul>
      </div>
    </section>

    <div class="footer">数字消费者洞察与妈妈定性研究助手</div>
  </div>
</body>
</html>
"""

    def _mode_label(self, mode: str) -> str:
        return {"multi": "多人模式", "single": "单人模式"}.get(mode, mode or "未提供")

    def _question_label(self, question_type: str) -> str:
        return {
            "product_concept": "产品概念",
            "purchase_decision": "购买决策",
            "needs_pain_points": "需求痛点",
            "copy_feedback": "文案和卖点反馈",
        }.get(question_type, question_type or "未提供")

    def _persona_cards(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return self._empty_card("当前没有可展示的妈妈原声。")
        cards = []
        for item in items:
            cards.append(
                f"""
                <div class="card persona-card">
                  <h3>{escape(str(item.get('persona_name', '匿名妈妈')))}</h3>
                  <div class="persona-meta">{escape(str(item.get('persona_id', '未知画像')))} · {escape(self._question_label(str(item.get('question_type', ''))))}</div>
                  <div class="quote">{escape(str(item.get('verbatim_answer', '')))}</div>
                  <div class="tag-list">
                    <span class="tag">态度：{escape(str(item.get('stance', '未标注')))}</span>
                    <span class="tag">核心需求：{escape('、'.join(item.get('core_needs', [])) or '无')}</span>
                  </div>
                  <div class="brief-item">
                    <div class="label">动机</div>
                    <div class="value">{escape('；'.join(item.get('motivations', [])) or '无')}</div>
                  </div>
                  <div class="brief-item">
                    <div class="label">顾虑</div>
                    <div class="value">{escape('；'.join(item.get('concerns', [])) or '无')}</div>
                  </div>
                  <div class="brief-item">
                    <div class="label">决策逻辑</div>
                    <div class="value">{escape(str(item.get('decision_logic', '')))}</div>
                  </div>
                </div>
                """
            )
        return "".join(cards)

    def _summary_block(self, title: str, items: List[str]) -> str:
        return f"""
        <div class="card summary-card">
          <h3>{escape(title)}</h3>
          <ul>{self._list_items(items)}</ul>
        </div>
        """

    def _list_items(self, items: List[str]) -> str:
        if not items:
            return "<li>暂无内容</li>"
        return "".join(f"<li>{escape(str(item))}</li>" for item in items)

    def _brief_value(self, value: Any) -> str:
        if value is None:
            return "未提供"
        text = str(value).strip()
        return text or "未提供"

    def _empty_card(self, text: str) -> str:
        return f'<div class="card persona-card"><div class="value">{escape(text)}</div></div>'
