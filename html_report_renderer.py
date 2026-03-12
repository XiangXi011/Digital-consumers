from html import escape
from typing import Any, Dict, Iterable, List


class HTMLReportRenderer:
    def render(self, report: Dict[str, Any]) -> str:
        meta = report.get("meta", {})
        brief = report.get("research_brief", {})
        research_plan = report.get("research_plan", {})
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
      --bg: #f7f1e8;
      --panel: #fffdf9;
      --ink: #221d1a;
      --muted: #6f655d;
      --line: #e7ddd1;
      --accent: #b85a2a;
      --accent-soft: #f8e7db;
      --sage: #6b7a4b;
      --sage-soft: #edf2e4;
      --sky: #dfe9f4;
      --shadow: 0 14px 36px rgba(71, 49, 31, 0.08);
      --radius: 22px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(184, 90, 42, 0.10), transparent 24%),
        radial-gradient(circle at 10% 10%, rgba(107, 122, 75, 0.10), transparent 20%),
        var(--bg);
      color: var(--ink);
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.65;
    }}
    .page {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 28px 22px 60px;
    }}
    .hero,
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 32px;
      background: linear-gradient(135deg, #fff8f1 0%, #fffdf9 100%);
    }}
    h1, h2, h3, p {{
      margin-top: 0;
    }}
    h1 {{
      font-size: 34px;
      margin-bottom: 8px;
    }}
    h2 {{
      font-size: 24px;
      margin: 28px 0 14px;
    }}
    h3 {{
      font-size: 18px;
      margin-bottom: 10px;
    }}
    .subtitle {{
      color: var(--muted);
      max-width: 900px;
    }}
    .chip-row,
    .tag-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .chip-row {{
      margin-top: 18px;
    }}
    .chip,
    .tag {{
      display: inline-flex;
      align-items: center;
      padding: 7px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }}
    .chip-accent {{
      background: var(--accent-soft);
      color: var(--accent);
    }}
    .chip-sage {{
      background: var(--sage-soft);
      color: var(--sage);
    }}
    .chip-sky {{
      background: var(--sky);
      color: #3d607a;
    }}
    .grid {{
      display: grid;
      gap: 18px;
    }}
    .grid-2 {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .grid-3 {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .card {{
      padding: 22px;
    }}
    .brief-item,
    .list-block {{
      margin-bottom: 14px;
    }}
    .label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 5px;
    }}
    .value {{
      font-size: 15px;
    }}
    .quote {{
      padding: 14px 16px;
      border-radius: 18px;
      background: #fbf4eb;
      border: 1px solid #efe1ce;
      font-size: 15px;
      margin-bottom: 12px;
    }}
    .persona-meta {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
    }}
    .tag {{
      background: #f6efe5;
      color: var(--ink);
    }}
    .tag-list {{
      margin-bottom: 10px;
      gap: 8px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .footer {{
      margin-top: 26px;
      text-align: center;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 960px) {{
      .grid-2, .grid-3 {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>妈妈定性研究报告</h1>
      <p class="subtitle">{escape(self._brief_value(brief.get("user_question")) or "围绕当前研究任务，输出研究助理拆解、消费者原声与结构化建议。")}</p>
      <div class="chip-row">
        <span class="chip chip-accent">模式：{escape(self._mode_label(str(meta.get("mode", ""))))}</span>
        <span class="chip chip-sage">研究问题：{escape(self._question_label(str(meta.get("question_type", ""))))}</span>
        <span class="chip chip-sky">生成时间：{escape(str(meta.get("generated_at", "未提供")))}</span>
        <span class="chip chip-accent">覆盖画像：{escape(str(meta.get("total_agents", 0)))}</span>
      </div>
    </section>

    <h2>任务拆解</h2>
    <section class="grid grid-2">
      {self._research_plan_cards(research_plan, meta)}
    </section>

    <h2>任务概览</h2>
    <section class="grid grid-2">
      <div class="card">
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
      <div class="card">
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
      <div class="card">
        <h3>输出边界</h3>
        <ul>
          <li>本报告基于既有妈妈画像生成，不等同于真实消费者访谈。</li>
          <li>如需更深分析，建议在当前会话继续追问具体画像、场景或表达。</li>
        </ul>
      </div>
    </section>

    <div class="footer">数字消费者洞察与妈妈定性研究助手</div>
  </div>
</body>
</html>
"""

    def _research_plan_cards(self, research_plan: Dict[str, Any], meta: Dict[str, Any]) -> str:
        if not research_plan:
            return (
                self._info_card("研究目标", "未提供")
                + self._list_card("评估维度", [])
            )

        planning_status = "带假设首轮" if meta.get("assumption_run") else "标准调研"
        left = f"""
        <div class="card">
          <h3>研究目标</h3>
          <div class="tag-list">
            <span class="tag">执行方式：{escape(planning_status)}</span>
            <span class="tag">建议模式：{escape(self._mode_label(str(research_plan.get("recommended_mode", ""))))}</span>
            <span class="tag">问题类型：{escape(self._question_label(str(research_plan.get("question_type", ""))))}</span>
          </div>
          <div class="brief-item">
            <div class="label">任务理解</div>
            <div class="value">{escape(self._brief_value(research_plan.get("normalized_intent")))}</div>
          </div>
          <div class="list-block">
            <div class="label">关键问题</div>
            <ul>{self._list_items(research_plan.get("research_objectives", []))}</ul>
          </div>
          <div class="list-block">
            <div class="label">评估维度</div>
            <ul>{self._list_items(research_plan.get("evaluation_dimensions", []))}</ul>
          </div>
        </div>
        """
        right = f"""
        <div class="card">
          <h3>执行前提</h3>
          <div class="list-block">
            <div class="label">资料需求</div>
            <ul>{self._list_items(research_plan.get("required_materials", []))}</ul>
          </div>
          <div class="list-block">
            <div class="label">待补信息</div>
            <ul>{self._list_items(research_plan.get("missing_information", []), empty_text="当前无缺口")}</ul>
          </div>
          <div class="list-block">
            <div class="label">澄清问题</div>
            <ul>{self._list_items(research_plan.get("clarification_questions", []), empty_text="当前无需追问")}</ul>
          </div>
          <div class="list-block">
            <div class="label">假设前提</div>
            <ul>{self._list_items(research_plan.get("assumptions_if_run_now", []), empty_text="当前未使用假设")}</ul>
          </div>
        </div>
        """
        return left + right

    def _persona_cards(self, items: List[Dict[str, Any]]) -> str:
        if not items:
            return self._empty_card("当前没有可展示的妈妈原声。")
        cards = []
        for item in items:
            cards.append(
                f"""
                <div class="card">
                  <h3>{escape(str(item.get('persona_name', '匿名妈妈')))}</h3>
                  <div class="persona-meta">{escape(str(item.get('persona_id', '未知画像')))} · {escape(self._question_label(str(item.get('question_type', ''))))}</div>
                  <div class="quote">{escape(str(item.get('verbatim_answer', '')))}</div>
                  <div class="tag-list">
                    <span class="tag">态度：{escape(str(item.get('stance', '未标注')))}</span>
                    <span class="tag">核心需求：{escape(self._join_inline(item.get('core_needs', []), fallback='无'))}</span>
                  </div>
                  <div class="brief-item">
                    <div class="label">动机</div>
                    <div class="value">{escape(self._join_inline(item.get('motivations', []), fallback='无'))}</div>
                  </div>
                  <div class="brief-item">
                    <div class="label">顾虑</div>
                    <div class="value">{escape(self._join_inline(item.get('concerns', []), fallback='无'))}</div>
                  </div>
                  <div class="brief-item">
                    <div class="label">决策逻辑</div>
                    <div class="value">{escape(str(item.get('decision_logic', '')))}</div>
                  </div>
                </div>
                """
            )
        return "".join(cards)

    def _summary_block(self, title: str, items: Iterable[str]) -> str:
        return f"""
        <div class="card">
          <h3>{escape(title)}</h3>
          <ul>{self._list_items(items)}</ul>
        </div>
        """

    def _info_card(self, title: str, value: str) -> str:
        return f"""
        <div class="card">
          <h3>{escape(title)}</h3>
          <div class="value">{escape(value)}</div>
        </div>
        """

    def _list_card(self, title: str, items: Iterable[str]) -> str:
        return f"""
        <div class="card">
          <h3>{escape(title)}</h3>
          <ul>{self._list_items(items)}</ul>
        </div>
        """

    def _list_items(self, items: Iterable[str], empty_text: str = "暂无内容") -> str:
        values = [str(item) for item in items or [] if str(item).strip()]
        if not values:
            return f"<li>{escape(empty_text)}</li>"
        return "".join(f"<li>{escape(value)}</li>" for value in values)

    def _join_inline(self, items: Iterable[str], fallback: str = "未提供") -> str:
        values = [str(item) for item in items or [] if str(item).strip()]
        return "、".join(values) if values else fallback

    def _mode_label(self, mode: str) -> str:
        return {"multi": "多人模式", "single": "单人模式"}.get(mode, mode or "未提供")

    def _question_label(self, question_type: str) -> str:
        return {
            "product_concept": "产品概念",
            "purchase_decision": "购买决策",
            "needs_pain_points": "需求痛点",
            "copy_feedback": "文案和卖点反馈",
        }.get(question_type, question_type or "未提供")

    def _brief_value(self, value: Any) -> str:
        if value is None:
            return "未提供"
        text = str(value).strip()
        return text or "未提供"

    def _empty_card(self, text: str) -> str:
        return f'<div class="card"><div class="value">{escape(text)}</div></div>'
