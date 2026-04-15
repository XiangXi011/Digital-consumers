# Market Research DingTalk Agent — 综合评审报告

> **评审日期**: 2026-03-13
> **评审来源**: (A) Claude Code 实时代码审计 + (B) skill_review_report.md v2.5.1 合规评审
> **基准文档**: SKILL.md + references/{master-spec, data-contracts, runtime-and-state, testing-and-operations}.md

---

## 一、两份评审的对比与校准

| 评审维度 | 评审 A (代码审计) | 评审 B (合规评审) | 校准结论 |
|:---|:---|:---|:---|
| 整体评分 | ~85% 合规 | 5.4/10 | **B 更准确**。A 仅对照 SKILL.md 核心规则，B 对照了完整 data-contracts.md 包括 RoutingDecision、RAInput、状态机枚举等 |
| BusinessBrief | 缺 price_anchor_type + validator | 同 + 下游仍读 session fields | **B 更全面**，发现了 session fields 绕过问题 |
| Anti-Math | 通过 | 阈值/标签不匹配 (consider vs maybe, 缺 <2.8 reject) | **B 正确**，A 漏检了 intent 标签和阈值差异 |
| Persona YAML | 通过 | veto_trigger vs veto_rules 格式不匹配 | **B 正确**，data-contracts.md 要求 `veto_rules` |
| 授权绑定 | 未检查 | 严重缺失 (2/10) | **B 发现关键盲区**，A 完全遗漏 |
| 内存层级 | 未检查 | 严重缺失 (2/10) | **B 发现关键盲区** |
| 状态机 | 通过 (只看了 langgraph 5 状态) | 代码用非标准状态名，缺 6 个 spec 状态 | **B 正确**，spec 定义 10 个状态 |
| CI 测试 | 3/3 通过 | 3/9 通过 | **B 更完整**，spec 实际要求 9 个阻断测试 |
| HTML 报告 | 未检查 | 缺 4 个必需段落 + 卡片字段不完整 | **B 发现新缺口** |
| Front Controller 模型 | 未检查 | RoutingDecision / NextActionDecision 完全缺失 | **B 发现新缺口** |

**结论**: 评审 A 过于乐观，主要因为只对照了 SKILL.md 顶层规则，未深入 data-contracts.md 的完整 schema 定义。评审 B 更贴近生产就绪标准。

---

## 二、综合发现 — 按严重度排序

### P0 — 安全与核心合约 (必须立即修复)

| # | 问题 | 代码位置 | Spec 来源 | 两份评审 |
|:--|:-----|:---------|:----------|:---------|
| 1 | **授权绑定完全缺失** — 无 user_id 绑定、无时间窗口、无 bot-mention 验证。任何人发"开始"即触发调研 | `task_session_manager.py:217-221` | master-spec.md §Authorization | 仅 B 发现 |
| 2 | **purchase_intent 阈值/标签错误** — 使用 `consider` 而非 `maybe`；缺少 `<2.8 → reject` 阈值 | `evidence_models.py:77` | data-contracts.md §SuccessAgentOutput | 仅 B 发现 |
| 3 | **BusinessBrief 缺 price_anchor_type 字段** | `business_brief.py` | data-contracts.md:44 | A+B 共同发现 |
| 4 | **BusinessBrief 缺 validate_price_constraints** model_validator | `business_brief.py` | data-contracts.md:60-72 | A+B 共同发现 |

### P1 — 合约完整性 (短期修复)

| # | 问题 | 代码位置 | Spec 来源 |
|:--|:-----|:---------|:----------|
| 5 | **RoutingDecision / NextActionDecision 模型缺失** — 前端控制器无结构化输出 | 不存在 | data-contracts.md §Front Controller |
| 6 | **SuccessAgentOutput / FailedAgentOutput / RAInput 模型缺失** — persona 输出无判别联合类型 | 不存在 | data-contracts.md §Persona and RA Outputs |
| 7 | **状态机名称不对齐** — 代码用 `collecting/planning/running`，spec 定义 10 个标准状态 | `task_session_manager.py` | data-contracts.md §SessionState |
| 8 | **6 个 CI 阻断测试缺失** — webhook 幂等性、suspend queue、veto 结构化、历史覆盖、peer 隔离、replay 一致性 | `tests/` | testing-and-operations.md |
| 9 | **HTML 报告缺 4 个必需段落** — 降级假设、一句话结论、缺席说明、输入快照摘要 | `html_report_renderer.py` | testing-and-operations.md §Report |
| 10 | **下游节点绕过 BusinessBrief** — `make_start_analysis_node` 通过 `session.fields` 传递原始字段 | `langgraph_nodes.py:172-216` | master-spec.md §BusinessBrief Isolation |
| 11 | **Persona 卡片字段不完整** — 缺 purchase_intent/score/chart_data/voice_line/what_would_change_my_mind | `html_report_renderer.py` | data-contracts.md §SuccessAgentOutput |

### P2 — 架构治理 (中期修复)

| # | 问题 | 说明 |
|:--|:-----|:-----|
| 12 | **内存层级隔离缺失** — 使用平坦 JSON sessions，无 5 层分离，persona 节点间无隔离 | spec 要求 control/working/episodic/semantic/evaluation 5 层 |
| 13 | **快照策略不完整** — `system_fingerprint.py` 缺 router_version/synthesis_version/scoring_engine_version，无 live/frozen snapshot 机制 | spec 要求在关键节点创建快照 |
| 14 | **Dedup key 格式不完整** — 当前 `dedup:msg_id`，spec 要求 `source_platform:msg_id:event_type` | 影响多平台扩展性 |
| 15 | **目录结构不合规** — 平坦根目录 vs spec 要求的 models/state_machine/nodes/memory/reporting/ | 功能影响小但不符合 scaffold 标准 |
| 16 | **veto_trigger → veto_rules** — YAML 使用字符串格式，spec 要求结构化规则 | 影响 veto 可测试性 |
| 17 | **EvidenceAtom.weight_hint 缺上界** — 应为 `Field(ge=0.0, le=5.0)` | 数据验证缺口 |
| 18 | **llm_refine_followup() 未真正调用 LLM** — 简化为 precondition 检查 | 功能不完整 |

---

## 三、Skill 文件自身的问题

两份评审综合后，对 Skill 定义文件本身也发现以下问题：

### 3.1 SKILL.md 与 data-contracts.md 的覆盖度差距

SKILL.md 的 "Core Rules" 仅 7 条，但 data-contracts.md 包含了大量 SKILL.md 未提及的合约：

| data-contracts.md 定义 | SKILL.md 是否提及 |
|:---|:---|
| 10 个 SessionState 枚举 | 未提及 |
| RoutingDecision / NextActionDecision | 未提及 |
| SuccessAgentOutput / FailedAgentOutput 判别联合 | 未提及 |
| RAInput (精确 8 个 mom_results) | 未提及 |
| PersonaChartData | 未提及 |
| purchase_intent 阈值 (buy/maybe/reject) | 未提及 |
| veto_rules (结构化格式) | 未提及，仅说 "veto trigger" |
| price_anchor_type | 未提及 |

**影响**: 如果开发者只读 SKILL.md 不读 references，会遗漏大量合约要求。评审 A 正是因此给出了过于乐观的评分。

**建议**: 在 SKILL.md 的 Core Rules 中补充关键合约清单，或在 Workflow 中标注"以下场景必须读 data-contracts.md"。

### 3.2 Sub-skill 引用不可解析

SKILL.md 引用了两个不存在的 sub-skill：
- `superpowers:test-driven-development`
- `superpowers:systematic-debugging`

这会导致 skill 调用链断裂。应移除或替换为实际存在的 skill。

### 3.3 agents/openai.yaml 定位不清

项目使用 Claude Code skill 体系，但 `agents/openai.yaml` 似乎面向 OpenAI agent protocol。如果不打算支持多 agent runtime，应移除或注明用途。

### 3.4 缺少反向同步规则

Skill 文档与代码之间缺少"双向同步"的强制规则。当前漂移（如 BusinessBrief 缺字段、intent 标签不匹配）说明需要在 Skill 中加一条：

> 修改 Pydantic schema 时必须同步更新 data-contracts.md，修改 data-contracts.md 时必须同步更新实现代码。PR 审查需检查两端一致性。

---

## 四、综合评分

| 维度 | 评分 | 理由 |
|:---|:---|:---|
| 核心架构规则落地 | **7/10** | math-decoupling、evidence-first、rule-first adjudication、prompt shield 核心逻辑正确，但细节偏差 (阈值/标签/字段) |
| 合约完整性 | **4/10** | 缺少 RoutingDecision、RAInput、AgentOutput 判别类型、状态机枚举等关键 schema |
| 安全性 | **3/10** | 授权绑定完全缺失是最大风险 |
| 测试覆盖 | **4/10** | 3/9 阻断测试到位，6 个关键场景无覆盖 |
| 生产就绪度 | **4/10** | 内存隔离、快照回放、降级策略、报告完整性均有缺口 |
| Skill 文档质量 | **7/10** | 结构清晰、reference 分层合理，但 SKILL.md 覆盖度不足、sub-skill 引用断裂 |

**综合评分: 4.8/10 — 未达生产就绪标准**

与评审 B 的 5.4/10 基本一致，略低是因为综合考量后授权绑定缺失和合约完整性问题的权重更高。

---

## 五、推荐行动路线图

```
Week 1 (P0):  授权绑定 → intent 阈值修正 → BusinessBrief 补全
Week 2 (P1):  RoutingDecision/AgentOutput 模型 → 状态机对齐 → 6 个 CI 测试
Week 3 (P1):  HTML 报告补全 → session.fields 绕过修复
Week 4 (P2):  内存层级 → 快照策略 → 目录重组
持续:         Skill 文档同步规则 → sub-skill 清理 → veto 结构化
```
