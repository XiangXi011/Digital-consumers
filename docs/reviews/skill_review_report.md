# Market Research DingTalk Agent — Skill v2.5.1 合规评审报告

> **评审日期**: 2026-03-13  
> **基准文档**: SKILL.md (v2.5.1 Final Lock) + references/master-spec.md, data-contracts.md, runtime-and-state.md, testing-and-operations.md, scaffold-guide.md  
> **项目路径**: `c:\Users\05537\Desktop\agent\市场部agent teams`

---

## 总体评估

| 维度 | 状态 | 评分 |
|:---|:---|:---|
| BusinessBrief 隔离 | ⚠️ 部分合规 | 6/10 |
| ReadinessGate 单一判定 | ✅ 合规 | 8/10 |
| 反数学规则 (Anti-Math) | ⚠️ 部分合规 | 7/10 |
| Follow-up 仲裁 | ✅ 合规 | 8/10 |
| Prompt Injection 防护 | ✅ 合规 | 8/10 |
| Persona YAML 合约 | ⚠️ 部分合规 | 6/10 |
| RA 证据优先合成 | ⚠️ 部分合规 | 6/10 |
| 授权绑定 (Auth Binding) | ❌ 缺失 | 2/10 |
| 内存层级隔离 | ❌ 缺失 | 2/10 |
| 快照与回放 | ⚠️ 部分实现 | 4/10 |
| 数据治理 & 隐私 | ⚠️ 部分合规 | 6/10 |
| CI 阻断测试覆盖 | ⚠️ 部分覆盖 | 5/10 |
| 目录结构 | ❌ 不合规 | 3/10 |
| HTML 报告合约 | ⚠️ 部分合规 | 5/10 |

**综合评分: 5.4/10 — 尚未达到生产就绪标准**

---

## 一、合规项目 ✅

### 1. ReadinessGate 单一判定点
- [make_readiness_gate_node](file:///c:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py#L118-L132) 是唯一决定信息是否充分的节点
- 其他节点不做就绪判断
- **合规**: 符合 master-spec.md "ReadinessGate Is the Only Readiness Judge"

### 2. Follow-up 仲裁 (Rule-First)
- [followup_adjudicator.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/followup_adjudicator.py) 完整实现了规则优先仲裁
- 阈值正确：embedding_similarity > 0.85, keyword_overlap > 60%
- [unrelated](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/tests/test_followup_rule_override.py#42-58) 判定不会唤醒 LLM
- [llm_refine_followup](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/followup_adjudicator.py#127-140) 只在 `candidate_same_topic` 时调用
- [test_followup_rule_override.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/tests/test_followup_rule_override.py) 提供了完整测试

### 3. Prompt Injection 防护
- [prompt_shield.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/prompt_shield.py) 在路由前执行
- 覆盖中英文注入模式：角色重设、系统提示覆盖、忽略规则、DAN/越狱
- [langgraph_flows.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/langgraph_flows.py#L52-L61) 中 [prompt_shield](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/langgraph_nodes.py#28-50) 节点在 [detect_command](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/langgraph_nodes.py#20-26) 之前运行

### 4. 幂等性与排序基础设施
- [redis_infra.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/redis_infra.py) 实现了完整的基础设施：
  - [EventDeduplicator](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/redis_infra.py#104-122) — SETNX + 24h TTL ✅
  - [AggregationWindow](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/redis_infra.py#131-157) — 3 秒滑动窗口 ✅
  - [SuspendQueue](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/redis_infra.py#163-191) — dispatch 阶段消息暂存 ✅
  - [OrderingGuard](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/redis_infra.py#197-216) — 时间戳排序检查 ✅
  - [InMemoryStore](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/redis_infra.py#47-95) 抽象层方便测试 ✅

---

## 二、部分合规项目 ⚠️

### 5. BusinessBrief 隔离

> [!WARNING]
> 多处仍然直接访问 session fields 而非 BusinessBrief

**问题**:
- [business_brief.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/business_brief.py) 定义了 [BusinessBrief](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/business_brief.py#15-102) 模型 ✅
- 但 `product_context` 和 `research_goal` 缺少 `Field(min_length=1)` 校验 — 使用默认空字符串替代
- `validate_price_constraints` model_validator **完全缺失** — spec 要求 `price_test` 时强制校验 `price_test_mode`、`price_range`、`benchmark_reference`
- `price_anchor_type` 字段**完全缺失**
- 下游节点 [make_start_analysis_node](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/langgraph_nodes.py#172-216) 仍然通过 `session.fields` → [build_research_input_payload](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/task_session_manager.py#292-304) 传递原始字段而非 [BusinessBrief](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/business_brief.py#15-102)

**修复建议**:
```python
# business_brief.py — 添加缺失字段和校验器
product_context: str = Field(min_length=1)
research_goal: str = Field(min_length=1)
price_anchor_type: Optional[Literal["competitor", "category_norm", "historical_price", "promo_anchor"]] = None

@model_validator(mode="after")
def validate_price_constraints(self):
    if self.task_type == "price_test":
        if not self.price_test_mode:
            raise ValueError("price_test requires price_test_mode")
        if not self.price_range:
            raise ValueError("price_test requires price_range")
        if self.price_test_mode == "relative_price" and not self.benchmark_reference:
            raise ValueError("relative_price requires benchmark_reference")
        if self.price_test_mode == "promo_vs_daily":
            if self.price_anchor_type not in {"historical_price", "promo_anchor"}:
                raise ValueError("promo_vs_daily requires valid price_anchor_type")
    return self
```

### 6. 反数学规则 (Anti-Math)

**问题**:
- [evidence_models.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/evidence_models.py#L77) 使用 `"consider"` 而非 spec 要求的 `"maybe"` 作为 purchase_intent 值
- Spec 定义的阈值：`≥4.0 → buy`, `2.8..4.0 → maybe`, `<2.8 → reject`
- 实际实现：`≥4.0 → buy`, `<4.0 → consider` — **缺少 reject 阈值 (<2.8)** 且标签不匹配

```diff
- purchase_intent: Optional[Literal["buy", "consider", "reject"]] = None
+ purchase_intent: Optional[Literal["buy", "maybe", "reject"]] = None

  if self.veto_triggered:
      self.purchase_intent = "reject"
+ elif score < 2.8:
+     self.purchase_intent = "reject"
+ elif score >= 4.0:
+     self.purchase_intent = "buy"
  else:
-     self.purchase_intent = "buy" if score >= 4.0 else "consider"
+     self.purchase_intent = "maybe"
```

### 7. Persona YAML 合约

**问题**:
- 所有 8 个 YAML 文件存在且包含 [id](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/evidence_models.py#21-30), [name](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/privacy_utils.py#36-39), `budget_band`, [decision_weights](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/persona_scoring.py#38-41), `feature_scoring_rubric` ✅
- 但 spec 要求的 `veto_rules` 字段**缺失**，项目使用 [veto_trigger](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/persona_scoring.py#43-46)（字符串格式）而非结构化 veto 规则
- 消费者语气保持良好，未出现专家/投资人/R&D 语言 ✅

### 8. RA 证据优先合成

**问题**:
- [test_ra_evidence_assembly.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/tests/test_ra_evidence_assembly.py) 测试了证据提取和分组 ✅
- [EvidenceAtom](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/evidence_models.py#21-30) 和 [RASynthesisInternal](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/evidence_models.py#32-38) 模型定义正确 ✅
- 但 spec 要求的 `RAInput` 模型**完全缺失** — 需要 `effective_task_type`, `research_goal`, `assumptions`, `mom_results: List[AgentOutput]`（精确 8 个）
- `SuccessAgentOutput` 和 `FailedAgentOutput` 判别联合类型**完全缺失**

### 9. HTML 报告合约

**问题** — 与 testing-and-operations.md 对比:

| 必需报告段落 | 当前状态 |
|:---|:---|
| 1. 封面信息 | ✅ hero 区域 |
| 2. **降级与假设** | ❌ 缺失 |
| 3. 一句话结论 | ❌ 缺失 |
| 4. 共识与分歧 | ✅ 研究总结区域 |
| 5. 痛点与驱动 | ✅ |
| 6. 八张人物卡片 | ⚠️ 格式不完整 |
| 7. **缺席说明** | ❌ 缺失 |
| 8. 优化建议 | ✅ 结构化建议区域 |
| 9. 输入快照摘要 | ❌ 缺失 |

人物卡片必需字段对比:

| 必需字段 | 当前状态 |
|:---|:---|
| persona_name | ✅ |
| purchase_intent | ❌ 缺失 |
| purchase_score | ❌ 缺失 |
| chart_data | ❌ 缺失 |
| voice_line | ❌ (使用 verbatim_answer) |
| what_would_change_my_mind | ❌ 缺失 |

---

## 三、严重缺失项目 ❌

### 10. 授权绑定 (Authorization Binding)

> [!CAUTION]
> 这是一个安全关键缺失。当前没有任何基于 user_id、时间窗口或 bot-mention 的授权绑定逻辑。

Spec 要求:
- 强肯定语句（如"开始调研"）仅在 bot mention / 私聊 / 回复 bot 授权请求时有效
- 弱肯定语句（如"好"、"可以"）需要 `awaiting_authorization` 状态 + 同一 [user_id](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/privacy_utils.py#28-34) + 5分钟内 + bot 提及
- 否定语句（如"等等"、"先别"）保持挂起

**当前实现**: [has_run_confirmation()](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/task_session_manager.py#217-221) 仅做简单关键词匹配，无 user_id 绑定、无时间窗口、无 bot-mention 检查。

### 11. 内存层级隔离 (Memory Architecture)

> [!CAUTION]
> 完全缺失分层内存架构。

Spec 要求 5 层内存:
1. **Control memory**: state, locks, TTLs, dedup, timestamps
2. **Working memory**: intake buffer, routing, draft brief, readiness output
3. **Episodic memory**: prior snapshots, completed task records
4. **Semantic memory**: tuning, calibration, analytics
5. **Evaluation memory**: divergence, minority survival, route overrides

**当前实现**: 仅使用平坦的 JSON sessions 和 Redis 基础设施，没有层级隔离。Persona 节点可能读到 peer 输出（没有隔离边界）。

### 12. 快照策略 (Snapshot Strategy)

**Spec 要求**:
- 在 aggregation, routing, readiness, authorization 后创建 live snapshots
- 在 dispatch, RA synthesis, report rendering 前冻结快照
- 每个冻结快照需包含: `prompt_bundle_version`, `persona_pack_version`, `schema_version`, `router_version`, `synthesis_version`, `scoring_engine_version`

**当前实现**: [system_fingerprint.py](file:///c:/Users/05537/Desktop/agent/市场部agent teams/system_fingerprint.py) 提供了版本标记（包含 `prompt_bundle_version`, `persona_pack_version`, `schema_version`），但:
- 缺少 `router_version` 和 `synthesis_version` 和 `scoring_engine_version`
- 没有实际的 live snapshot 或 frozen snapshot 机制
- 没有 replay 一致性保证

### 13. 目录结构

Spec 要求的 Deliverables Tree:
```text
models/          ❌ 不存在
state_machine/   ❌ 不存在
nodes/           ❌ 不存在
memory/          ❌ 不存在
reporting/       ❌ 不存在
personas/        ✅ 存在
tests/mock/      ❌ 不存在
```

当前项目使用平坦的文件结构，所有模块在根目录。这不是一个严格的功能性问题，但不符合 scaffold 标准。

### 14. 缺失的 CI 阻断测试

Spec 要求的 9 个 CI 阻断测试:

| 测试文件 | 状态 |
|:---|:---|
| [test_followup_rule_override.py](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/tests/test_followup_rule_override.py) | ✅ 存在，7 tests pass |
| [test_persona_math_decoupling.py](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/tests/test_persona_math_decoupling.py) | ✅ 存在，8 tests pass |
| `test_ra_evidence_assembly_minority.py` | ⚠️ 有 [test_ra_evidence_assembly.py](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/tests/test_ra_evidence_assembly.py)，5 tests pass |
| `test_webhook_idempotency_and_order.py` | ❌ 缺失 |
| `test_dispatching_suspend_queue.py` | ❌ 缺失 |
| `test_veto_override_structured.py` | ❌ 缺失 |
| `test_history_cannot_override_current_fact.py` | ❌ 缺失 |
| `test_mom_agent_cannot_read_peer_outputs.py` | ❌ 缺失 |
| `test_frozen_snapshot_replay_consistency.py` | ❌ 缺失 |

---

## 四、Front Controller 输出模型缺失

Spec (data-contracts.md) 要求的 `RoutingDecision` 和 `NextActionDecision` 模型**完全不存在**。这些是前端控制器的结构化输出，决定路由和下一步动作。

```python
class RoutingDecision(BaseModel):
    route_task_type: TaskType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_spans: List[str]
    competing_routes: List[str]
    ambiguity_flags: List[str]
    requires_clarification: bool

class NextActionDecision(BaseModel):
    recommended_state: SessionState
    blocking_reasons: List[str]
    assumptions_to_confirm: List[str]
    authorization_needed: bool
    user_facing_prompt: str
```

---

## 五、Dedup Key 格式

Spec 要求: `dedup_key = source_platform + ":" + msg_id + ":" + event_type`

当前实现: `dedup_key = "dedup:" + msg_id` — 缺少 `source_platform` 和 `event_type` 组件。

---

## 六、状态机缺陷

Spec 定义了 10 个状态:
```
intake → normalizing → awaiting_clarification → awaiting_authorization → 
ready_to_dispatch → dispatching → summarizing → completed → recovery → expired
```

当前实现使用非标准状态名称:
- `collecting` (不在 spec 中)
- `planning` (不在 spec 中)
- [running](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/tests/test_followup_rule_override.py#42-58) (不在 spec 中)
- `awaiting_run_confirmation` (不在 spec 中)
- 缺失: `intake`, `normalizing`, `dispatching`, `summarizing`, `recovery`, [expired](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/redis_infra.py#55-61)

---

## 七、Final Acceptance Checklist

| 验收标准 | 状态 |
|:---|:---|
| 下游节点不直接读取 raw chat | ⚠️ 部分违规 |
| 所有执行通过 ReadinessGate | ✅ |
| LLM 不执行加权数学 | ⚠️ 阈值/标签不对 |
| Veto override 使用结构化代码 | ⚠️ 使用字符串而非结构化代码 |
| Follow-up 规则优先，unrelated 不可被 LLM 升级 | ✅ |
| 幂等性测试通过 | ❌ 测试不存在 |
| 排序测试通过 | ❌ 测试不存在 |
| suspend queue 测试通过 | ❌ 测试不存在 |
| 少数派意见存活 | ✅ 有测试 |
| Peer 隔离测试通过 | ❌ 测试不存在 |
| Replay 一致性测试通过 | ❌ 测试不存在 |
| 脱敏、保留期限、版本锁定 | ⚠️ 部分实现 |

---

## 八、修复优先级建议

### P0 — 立即修复 (安全 & 核心合约)
1. **授权绑定** — 添加 user_id + 时间窗口 + bot-mention 验证
2. **purchase_intent 阈值修正** — [consider](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/tests/test_persona_math_decoupling.py#53-64) → `maybe`, 添加 `<2.8 → reject`
3. **BusinessBrief 校验器** — 添加 `validate_price_constraints` 和 `price_anchor_type`
4. **状态机名称对齐** — 使用 spec 定义的 10 个状态

### P1 — 短期修复 (合约完整性)
5. **添加 RoutingDecision / NextActionDecision 模型**
6. **添加 SuccessAgentOutput / FailedAgentOutput / RAInput 模型**
7. **添加缺失的 6 个 CI 阻断测试**
8. **补全 HTML 报告必需段落** — 降级假设、一句话结论、缺席说明、输入快照摘要
9. **Persona 卡片格式** — 添加 purchase_intent, purchase_score, chart_data, voice_line, what_would_change_my_mind

### P2 — 中期修复 (架构治理)
10. **内存层级隔离** — 实现 5 层内存架构 + persona 节点 peer 隔离
11. **快照策略** — 实现 live/frozen snapshot + 版本束
12. **目录结构重组** — 按 scaffold 标准组织 models/, state_machine/, nodes/, memory/, reporting/
13. **Dedup key 格式** — 添加 source_platform + event_type 组件
14. **Persona YAML** — [veto_trigger](file:///c:/Users/05537/Desktop/agent/%E5%B8%82%E5%9C%BA%E9%83%A8agent%20teams/persona_scoring.py#43-46) → `veto_rules` 结构化格式
