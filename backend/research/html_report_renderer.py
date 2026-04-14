"""定性研究报告 HTML 渲染器。"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional


STANCE_LABELS = {
    "interested": "感兴趣",
    "cautious": "谨慎",
    "rejecting": "拒绝",
    "neutral": "中立",
}

PURCHASE_INTENT_LABELS = {
    "buy": "愿意购买",
    "consider": "考虑购买",
    "reject": "不会购买",
}

QUESTION_TYPE_LABELS = {
    "concept_test": "概念测试",
    "packaging_review": "包装评审",
    "pricing_test": "价格测试",
    "ad_review": "广告评审",
    "positioning_test": "定位测试",
}


def _h(text: Any) -> str:
    return html.escape(str(text)) if text else ""


def _score_color(score: float) -> str:
    if score >= 4.0:
        return "#16a34a"
    if score >= 2.8:
        return "#ca8a04"
    return "#dc2626"


class HTMLReportRenderer:
    """将结构化的定性研究报告字典渲染为独立 HTML 页面。"""

    def render(self, report: Dict[str, Any]) -> str:
        meta = report.get("meta", {})
        brief = report.get("research_brief", {})
        plan = report.get("research_plan", {})
        voices = report.get("consumer_voice", [])
        summary = report.get("research_summary", {})
        structured = report.get("structured_recommendation", {})
        evidence_groups = report.get("evidence_groups", {})
        group_discussion = report.get("group_discussion", {})
        deep_dive = report.get("deep_dive_results", {})
        appendix = report.get("appendix", {})

        title = self._report_title(brief, meta)

        sections = [
            self._section_cover(title, meta, brief),
            self._section_one_line(structured),
            self._section_summary(summary),
            self._section_verdict_card(meta, structured, summary, brief, report),
            self._section_overall(summary, structured),
            self._section_evidence(evidence_groups),
            self._section_persona_cards(voices),
            self._section_group_discussion(group_discussion),
            self._section_deep_dive(deep_dive),
            self._section_actions(structured),
            self._section_appendix(plan, meta, appendix),
        ]

        body = "\n".join(sections)
        return self._wrap_page(title, body, meta)

    # ------------------------------------------------------------------
    # 标题
    # ------------------------------------------------------------------

    def _report_title(self, brief: Dict, meta: Dict) -> str:
        question = brief.get("user_question", "")
        if question:
            return f"定性研究报告：{question[:40]}"
        qtype = meta.get("question_type", "")
        label = QUESTION_TYPE_LABELS.get(qtype, "定性研究")
        return f"{label}报告"

    # ------------------------------------------------------------------
    # 各区块
    # ------------------------------------------------------------------

    def _section_cover(self, title: str, meta: Dict, brief: Dict) -> str:
        mode = meta.get("mode", "multi")
        mode_label = "多人模式" if mode == "multi" else "单人模式"
        agent_count = meta.get("total_agents", meta.get("agent_count_completed", 0))
        question_type = QUESTION_TYPE_LABELS.get(meta.get("question_type", ""), meta.get("question_type", ""))
        product_info = brief.get("product_info", "")
        user_question = brief.get("user_question", "")
        generated_at = meta.get("generated_at", "")

        lines = [
            '<section class="cover">',
            f"<h1>{_h(title)}</h1>",
            f'<p class="meta-line">模式：{_h(mode_label)}　画像数：{_h(agent_count)}　类型：{_h(question_type)}　生成时间：{_h(generated_at)}</p>',
        ]
        if user_question:
            lines.append(f'<p class="meta-line">核心问题：{_h(user_question)}</p>')
        if product_info:
            lines.append(f'<p class="meta-line">产品信息：{_h(product_info)}</p>')
        lines.append("</section>")
        return "\n".join(lines)

    def _section_one_line(self, structured: Dict) -> str:
        answers = structured.get("objective_answers", [])
        if not answers:
            return ""
        return (
            '<section class="card">'
            "<h2>一句话结论</h2>"
            f'<p class="verdict">{_h(answers[0])}</p>'
            "</section>"
        )

    def _section_summary(self, summary: Dict) -> str:
        consensus = summary.get("consensus", [])
        barriers = summary.get("barriers", [])
        drivers = summary.get("drivers", [])
        if not any([consensus, barriers, drivers]):
            return ""

        parts = ['<section class="card">', "<h2>核心结论摘要</h2>"]
        if consensus:
            parts.append("<h3>共识点</h3>")
            parts.append("<ul>")
            for item in consensus[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        if drivers:
            parts.append("<h3>购买驱动因素</h3>")
            parts.append("<ul>")
            for item in drivers[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        if barriers:
            parts.append("<h3>购买阻力</h3>")
            parts.append("<ul>")
            for item in barriers[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        parts.append("</section>")
        return "\n".join(parts)

    def _section_verdict_card(self, meta: Dict, structured: Dict, summary: Dict, brief: Dict, report: Dict) -> str:
        mode = meta.get("mode", "multi")
        mode_label = "多人模式" if mode == "multi" else "单人模式"
        covered = (
            f"{meta.get('total_agents', 0)} 位画像"
            if mode == "multi"
            else report.get("appendix", {}).get("selected_persona") or "指定画像"
        )

        key_risks = structured.get("key_risks") or summary.get("barriers") or []
        opportunity = structured.get("opportunity_areas") or summary.get("drivers") or []
        if key_risks and not opportunity:
            decision = "建议先优化后推进"
        else:
            decision = "建议推进"

        objective = (
            structured.get("objective_answers")
            or summary.get("consensus")
            or ["当前有一定消费者兴趣，但需要结合场景细化。"]
        )[0]
        evidence_list = (summary.get("drivers") or [])[:2]
        risk_line = (key_risks or ["主要风险是信息可信度与卖点清晰度不足。"])[0]
        next_action = (
            (structured.get("recommended_actions") or ["补充关键信息后复跑，验证关键阻力是否下降。"])[0]
            if isinstance(structured.get("recommended_actions"), list)
            else "补充关键信息后复跑，验证关键阻力是否下降。"
        )

        evidence_text = "；".join(str(item).strip() for item in evidence_list if str(item).strip())
        if not evidence_text:
            evidence_text = "已有共识点支持继续验证。"

        required_for_quality = [
            meta.get("question_type", ""),
            brief.get("user_question", ""),
            brief.get("product_info", ""),
        ]
        present_count = sum(1 for item in required_for_quality if str(item).strip())
        if present_count >= 3:
            completeness = "高"
        elif present_count == 2:
            completeness = "中"
        else:
            completeness = "低"

        lines = [
            '<section class="card verdict-card">',
            "<h2>决策卡</h2>",
            f"<p><b>结论：</b>{_h(decision)}</p>",
            f"<p><b>信息完整度：</b>{_h(completeness)}</p>",
            f"<p><b>覆盖范围：</b>{_h(mode_label)}，{_h(covered)}</p>",
            f"<p><b>核心判断：</b>{_h(objective)}</p>",
            f"<p><b>关键证据：</b>{_h(evidence_text)}</p>",
            f"<p><b>主要风险：</b>{_h(risk_line)}</p>",
            f"<p><b>下一步动作：</b>{_h(next_action)}</p>",
            "</section>",
        ]
        return "\n".join(lines)

    def _section_overall(self, summary: Dict, structured: Dict) -> str:
        pain_points = summary.get("pain_points", [])
        copy_insights = summary.get("copy_insights", [])
        recommendations = summary.get("recommendations", [])
        differences = summary.get("differences", [])
        copy_adjustments = structured.get("copy_or_product_adjustments", [])

        has_content = any([pain_points, copy_insights, recommendations, differences, copy_adjustments])
        if not has_content:
            return ""

        parts = ['<section class="card">', "<h2>总体洞察</h2>"]
        if pain_points:
            parts.append("<h3>痛点</h3><ul>")
            for item in pain_points[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        if copy_insights:
            parts.append("<h3>文案洞察</h3><ul>")
            for item in copy_insights[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        if copy_adjustments:
            parts.append("<h3>文案 / 产品调整建议</h3><ul>")
            for item in copy_adjustments[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        if recommendations:
            parts.append("<h3>综合建议</h3><ul>")
            for item in recommendations[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        if differences:
            parts.append("<h3>关键分歧</h3><ul>")
            for item in differences[:5]:
                parts.append(f"<li>{_h(item)}</li>")
            parts.append("</ul>")
        parts.append("</section>")
        return "\n".join(parts)

    def _section_evidence(self, evidence_groups: Dict) -> str:
        top_consensus = evidence_groups.get("top_consensus_evidence", [])
        top_divergence = evidence_groups.get("top_divergence_evidence", [])
        if not top_consensus and not top_divergence:
            return ""

        parts = ['<section class="card">', "<h2>关键证据</h2>"]
        if top_consensus:
            parts.append("<h3>共识证据</h3><ul>")
            for ev in top_consensus[:5]:
                text = ev.get("text", ev.get("content", ""))
                persona = ev.get("persona_name", ev.get("persona_id", ""))
                if text:
                    parts.append(f"<li>{_h(text)}{' — ' + _h(persona) if persona else ''}</li>")
            parts.append("</ul>")
        if top_divergence:
            parts.append("<h3>分歧证据</h3><ul>")
            for ev in top_divergence[:5]:
                text = ev.get("text", ev.get("content", ""))
                persona = ev.get("persona_name", ev.get("persona_id", ""))
                if text:
                    parts.append(f"<li>{_h(text)}{' — ' + _h(persona) if persona else ''}</li>")
            parts.append("</ul>")
        parts.append("</section>")
        return "\n".join(parts)

    def _section_persona_cards(self, voices: List[Dict]) -> str:
        if not voices:
            return ""

        parts = ['<section class="card">', "<h2>典型人群观点</h2>", '<div class="persona-grid">']
        for v in voices:
            pid = v.get("persona_id", "")
            pname = v.get("persona_name", "")
            stance = v.get("stance", "")
            stance_cn = STANCE_LABELS.get(stance, stance)
            voice = v.get("voice_line") or v.get("verbatim_answer", "")
            needs = v.get("core_needs", [])
            concerns = v.get("concerns", [])
            change_mind = v.get("what_would_change_my_mind", "")

            backend = v.get("backend_evaluation", {})
            purchase_intent = backend.get("purchase_intent", "")
            purchase_intent_cn = PURCHASE_INTENT_LABELS.get(purchase_intent, purchase_intent)
            purchase_score = backend.get("purchase_score")

            rubric = v.get("rubric_scores", {})

            # Stance color
            stance_color = {
                "interested": "#16a34a",
                "cautious": "#ca8a04",
                "rejecting": "#dc2626",
                "neutral": "#6b7280",
            }.get(stance, "#6b7280")

            parts.append('<div class="persona-card">')
            parts.append(
                f'<div class="persona-header">'
                f'<span class="persona-name">{_h(pname)}</span>'
                f'<span class="persona-id">{_h(pid)}</span>'
                f'<span class="stance" style="background:{stance_color}">{_h(stance_cn)}</span>'
                f"</div>"
            )

            # Rubric scores bar
            if rubric:
                parts.append('<div class="rubric-bar">')
                for dim, score in rubric.items():
                    dim_cn = {
                        "demand_fit": "需求匹配",
                        "differentiation": "差异化",
                        "purchase_drive": "购买驱动",
                        "price_acceptance": "价格接受",
                    }.get(dim, dim)
                    sc = _score_color(float(score) if score else 0)
                    parts.append(
                        f'<span class="rubric-item">'
                        f'<span class="rubric-label">{_h(dim_cn)}</span>'
                        f'<span class="rubric-score" style="color:{sc}">{_h(score)}</span>'
                        f"</span>"
                    )
                parts.append("</div>")

            # Purchase info
            if purchase_score is not None or purchase_intent_cn:
                score_color = _score_color(float(purchase_score) if purchase_score else 0)
                score_display = f"{float(purchase_score):.1f}" if purchase_score is not None else "暂无"
                parts.append(
                    f'<div class="purchase-line">'
                    f'购买意向：<b style="color:{score_color}">{_h(purchase_intent_cn)}</b>　'
                    f'购买评分：<b style="color:{score_color}">{_h(score_display)}</b>'
                    f"</div>"
                )

            # Voice line
            if voice:
                parts.append(f'<blockquote class="voice-line">{_h(voice)}</blockquote>')

            # Needs & concerns
            if needs:
                needs_text = "、".join(str(n) for n in needs)
                parts.append(f"<p><b>核心需求：</b>{_h(needs_text)}</p>")
            if concerns:
                concerns_text = "、".join(str(c) for c in concerns)
                parts.append(f"<p><b>主要顾虑：</b>{_h(concerns_text)}</p>")

            # Trigger / change mind
            if change_mind:
                parts.append(f"<p><b>触发条件：</b>{_h(change_mind)}</p>")

            parts.append("</div>")  # persona-card

        parts.append("</div>")  # persona-grid
        parts.append("</section>")
        return "\n".join(parts)

    def _section_group_discussion(self, group_discussion: Dict) -> str:
        if not group_discussion or group_discussion.get("status") != "completed":
            return ""

        participants = group_discussion.get("participants", [])
        rounds = group_discussion.get("discussion_rounds", [])
        conflicts = group_discussion.get("key_conflicts", [])
        consensus = group_discussion.get("emerging_consensus", [])
        unresolved = group_discussion.get("unresolved_issues", [])

        if not rounds and not conflicts and not consensus:
            return ""

        parts = ['<section class="card">', "<h2>小组讨论摘要</h2>"]

        if participants:
            parts.append(f"<p><b>参与者：</b>{_h('、'.join(str(p) for p in participants))}</p>")

        for rd in rounds:
            round_num = rd.get("round", "")
            topic = rd.get("topic", "")
            exchanges = rd.get("exchanges", [])
            parts.append(f"<h3>第{_h(round_num)}轮：{_h(topic)}</h3>")
            if exchanges:
                parts.append("<ul>")
                for ex in exchanges[:6]:
                    persona = ex.get("persona_id", ex.get("persona_name", ""))
                    content = ex.get("content", ex.get("text", ""))
                    if content:
                        prefix = f"[{_h(persona)}] " if persona else ""
                        parts.append(f"<li>{prefix}{_h(content)}</li>")
                parts.append("</ul>")

        if conflicts:
            parts.append("<h3>关键分歧</h3><ul>")
            for c in conflicts:
                parts.append(f"<li>{_h(c)}</li>")
            parts.append("</ul>")

        if consensus:
            parts.append("<h3>初步共识</h3><ul>")
            for c in consensus:
                parts.append(f"<li>{_h(c)}</li>")
            parts.append("</ul>")

        if unresolved:
            parts.append("<h3>未解决问题</h3><ul>")
            for c in unresolved:
                parts.append(f"<li>{_h(c)}</li>")
            parts.append("</ul>")

        parts.append("</section>")
        return "\n".join(parts)

    def _section_deep_dive(self, deep_dive: Dict) -> str:
        if not deep_dive or deep_dive.get("status") != "completed":
            return ""

        results = deep_dive.get("results", [])
        if isinstance(results, dict):
            results = list(results.values())
        if not results:
            return ""

        parts = ['<section class="card">', "<h2>深访摘要</h2>"]

        for res in results:
            name = res.get("persona_name", "")
            original_stance = res.get("original_stance", "")
            refined_stance = res.get("refined_stance", "")
            shifted = res.get("stance_shifted", False)
            reasoning = res.get("deeper_reasoning", "")
            change_mind = res.get("what_would_change_mind", "")
            barrier_driver = res.get("key_barrier_or_driver", "")

            parts.append(f"<h3>{_h(name)}</h3>")

            stance_line = f"立场：{_h(original_stance)}"
            if refined_stance and refined_stance != original_stance:
                stance_line += f" → {_h(refined_stance)}"
            if shifted:
                stance_line += ' <span class="badge changed">立场转变</span>'
            parts.append(f"<p>{stance_line}</p>")

            if reasoning:
                parts.append(f"<p><b>深层推理：</b>{_h(reasoning)}</p>")
            if barrier_driver:
                parts.append(f"<p><b>关键障碍/驱动：</b>{_h(barrier_driver)}</p>")
            if change_mind:
                parts.append(f"<p><b>可能改变立场的条件：</b>{_h(change_mind)}</p>")

        parts.append("</section>")
        return "\n".join(parts)

    def _section_actions(self, structured: Dict) -> str:
        actions = structured.get("recommended_actions", [])
        risks = structured.get("key_risks", [])
        opportunities = structured.get("opportunity_areas", [])
        evidence_gaps = structured.get("evidence_gaps", [])

        has_content = any([actions, risks, opportunities, evidence_gaps])
        if not has_content:
            return ""

        parts = ['<section class="card">', "<h2>建议动作</h2>"]

        if actions:
            parts.append('<table class="action-table">')
            parts.append("<thead><tr><th>#</th><th>建议</th><th>落地说明</th></tr></thead>")
            parts.append("<tbody>")
            for i, action in enumerate(actions, 1):
                landing = self._action_landing_note(str(action))
                parts.append(f"<tr><td>{i}</td><td>{_h(action)}</td><td>{_h(landing)}</td></tr>")
            parts.append("</tbody></table>")

        if risks:
            parts.append("<h3>关键风险</h3><ul>")
            for r in risks[:5]:
                parts.append(f"<li>{_h(r)}</li>")
            parts.append("</ul>")

        if opportunities:
            parts.append("<h3>机会点</h3><ul>")
            for o in opportunities[:5]:
                parts.append(f"<li>{_h(o)}</li>")
            parts.append("</ul>")

        if evidence_gaps:
            parts.append("<h3>证据缺口</h3><ul>")
            for g in evidence_gaps[:5]:
                parts.append(f"<li>{_h(g)}</li>")
            parts.append("</ul>")

        parts.append("</section>")
        return "\n".join(parts)

    def _section_appendix(self, plan: Dict, meta: Dict, appendix: Dict) -> str:
        task_breakdown = plan.get("task_breakdown", [])
        research_objectives = plan.get("research_objectives", [])
        eval_dimensions = plan.get("evaluation_dimensions", [])
        sub_questions = plan.get("sub_questions_for_personas", [])

        parts = ['<section class="card">', "<h2>附录</h2>"]

        if task_breakdown or research_objectives:
            parts.append("<details><summary>任务拆解与研究目标（点击展开）</summary>")
            if task_breakdown:
                parts.append("<h3>任务拆解</h3><ol>")
                for item in task_breakdown:
                    parts.append(f"<li>{_h(item)}</li>")
                parts.append("</ol>")
            if research_objectives:
                parts.append("<h3>研究目标</h3><ol>")
                for item in research_objectives:
                    parts.append(f"<li>{_h(item)}</li>")
                parts.append("</ol>")
            parts.append("</details>")

        if eval_dimensions:
            parts.append("<details><summary>评估维度（点击展开）</summary><ul>")
            for d in eval_dimensions:
                parts.append(f"<li>{_h(d)}</li>")
            parts.append("</ul></details>")

        if sub_questions:
            parts.append("<details><summary>子问题（点击展开）</summary><ol>")
            for q in sub_questions:
                parts.append(f"<li>{_h(q)}</li>")
            parts.append("</ol></details>")

        # Version info
        version_bundle = meta.get("version_bundle", {})
        if version_bundle:
            parts.append("<details><summary>版本信息（点击展开）</summary><ul>")
            for k, v in version_bundle.items():
                parts.append(f"<li>{_h(k)}: {_h(v)}</li>")
            parts.append("</ul></details>")

        parts.append("</section>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _action_landing_note(action: str) -> str:
        lower = action.lower()
        if any(kw in lower for kw in ("packaging", "包装", "设计", "外观")):
            return "优先启动包装 A/B 测试，收集目标人群视觉偏好反馈。"
        if any(kw in lower for kw in ("social", "media", "社媒", "社交", "口碑", "小红书", "抖音", "campaign")):
            return "优先在小红书/抖音布局种草内容，30 天内观测声量变化。"
        if any(kw in lower for kw in ("ingredient", "成分", "数据", "efficacy", "data", "clinical")):
            return "补充临床数据或第三方检测报告，增强产品信任度。"
        if any(kw in lower for kw in ("price", "价格", "定价", "pricing")):
            return "建议进行价格敏感度测试，确定最优价格带。"
        if any(kw in lower for kw in ("partner", "合作", "endorsement", "牙医", "dental", "professional")):
            return "筛选并接洽专业背书合作方，明确合作形式与成本。"
        return "建议小范围试点验证，确认对购买转化的实际影响。"

    # ------------------------------------------------------------------
    # 页面外壳
    # ------------------------------------------------------------------

    def _wrap_page(self, title: str, body: str, meta: Dict) -> str:
        latency = meta.get("pipeline_total_latency_ms", 0)
        latency_sec = f"{latency / 1000:.1f}" if latency else "未知"
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_h(title)}</title>
<style>
:root{{--bg:#f8fafc;--card:#fff;--border:#e2e8f0;--text:#1e293b;--muted:#64748b;--accent:#2563eb}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans SC",sans-serif;background:var(--bg);color:var(--text);line-height:1.7;padding:24px}}
section{{max-width:900px;margin:0 auto 20px}}
h1{{font-size:1.6rem;margin-bottom:8px}}
h2{{font-size:1.25rem;border-bottom:2px solid var(--accent);padding-bottom:4px;margin:16px 0 10px}}
h3{{font-size:1rem;margin:12px 0 6px;color:var(--muted)}}
p{{margin:4px 0}}
ul,ol{{margin:4px 0 4px 20px}}
li{{margin:2px 0}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:20px 24px}}
.cover{{text-align:center;padding:40px 24px}}
.cover h1{{font-size:1.8rem}}
.meta-line{{color:var(--muted);font-size:.9rem;margin:4px 0}}
.verdict{{font-size:1.05rem;font-weight:500;margin:8px 0}}
.verdict-card{{border-left:4px solid var(--accent)}}
.persona-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:16px;margin-top:12px}}
.persona-card{{border:1px solid var(--border);border-radius:8px;padding:14px 16px}}
.persona-header{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.persona-name{{font-weight:600;font-size:1rem}}
.persona-id{{color:var(--muted);font-size:.85rem}}
.stance{{color:#fff;font-size:.75rem;padding:2px 8px;border-radius:10px}}
.rubric-bar{{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0}}
.rubric-item{{display:flex;flex-direction:column;align-items:center;font-size:.8rem}}
.rubric-label{{color:var(--muted)}}
.rubric-score{{font-weight:700;font-size:1rem}}
.purchase-line{{margin:4px 0;font-size:.9rem}}
.voice-line{{border-left:3px solid var(--accent);padding:6px 12px;margin:8px 0;font-style:italic;color:var(--muted);background:#f1f5f9;border-radius:0 4px 4px 0}}
.action-table{{width:100%;border-collapse:collapse;margin:8px 0}}
.action-table th,.action-table td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--border)}}
.action-table th{{background:#f1f5f9;font-weight:600}}
.badge{{font-size:.75rem;padding:1px 6px;border-radius:8px}}
.badge.changed{{background:#fef3c7;color:#92400e}}
details{{margin:8px 0}}
summary{{cursor:pointer;color:var(--accent);font-weight:500}}
footer{{text-align:center;color:var(--muted);font-size:.8rem;padding:20px 0}}
</style>
</head>
<body>
{body}
<footer>由 MiMo 调研智能体生成 · 流水线耗时 {latency_sec} 秒</footer>
</body>
</html>"""
