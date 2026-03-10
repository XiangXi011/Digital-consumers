# Business Report Upgrade Design

**Date:** 2026-03-10

## Goal

将当前“可演示版”概念测试报告升级为“业务可用版”报告，补足结论证据链、原声标签一致性、可执行建议、竞品边界和可信度提示。

## Current Gaps

当前报告已具备基础结构，但仍存在以下关键缺口：

- 结论只有 headline，没有“为什么”的证据拆解
- 业务层直接暴露内部 recommendation 枚举值
- 消费者原声来源于讨论模板句，和 stance 标签容易错位
- 人群接受度只有分数，没有高低原因解释
- 缺少价值主张冲突识别
- 优化建议不够可执行，缺少分层动作建议
- 缺少竞品缺失影响说明
- 缺少可信度等级与边界说明

## Scope

本次只升级两层：

- `concept_testing.py`：报告 schema 与生成逻辑
- `html_report_renderer.py`：业务版 HTML 模板

不调整：

- persona 角色库
- LangGraph 主流程
- 钉钉机器人接入
- Vercel 报告发布

## Recommended Approach

采用“规则生成核心判断 + 模板化业务表达”的方案。

### Why This Approach

- 当前底层讨论和访谈文本仍包含模板化表达，直接依赖 LLM 原话会降低稳定性
- 先用规则从评估结果中提取结构化信号，再生成业务表达，结果更可控
- 后续如果要接真实 LLM 润色，也可以在此结构之上追加，不会破坏报告 schema

## New Report Schema

### 1. Executive Summary

新增字段：

- `business_recommendation`
- `confidence_level`
- `confidence_reason`

保留：

- `headline`
- `recommendation`
- `avg_intention`
- `key_risk`

### 2. Diagnosis

新增模块：

- `decision_drivers`
- `value_proposition_conflicts`
- `competitive_limitations`

### 3. Segment Opportunity

为每个 segment 条目新增：

- `why_high_or_low`
- `top_reason_tag`

### 4. Voice Of Consumer

每条原声升级为：

- `agent_name`
- `segment`
- `stance_label`
- `reason_tag`
- `quote`

原声不再直接复用 discussion 模板句，而是基于评估结果生成与 stance 一致的“典型原声”。

### 5. Action Plan

新增：

- `immediate_actions`
- `next_round_prerequisites`
- `recommended_next_tests`

### 6. Report Boundary

新增：

- `input_completeness`
- `missing_fields`
- `credibility_notes`

## Generation Logic

### Business Recommendation

由内部 recommendation 枚举映射为业务语言：

- `advance_to_real_research` -> `可进入真实外部调研`
- `revise_then_retest` -> `建议优化后再进行下一轮测试`
- `do_not_advance_yet` -> `建议先内部优化，不建议直接进入外部测试`

### Confidence Level

依据输入完整度和关键证据项规则计算：

- 资料完整度
- 是否有价格
- 是否有包装图或包装摘要
- 是否有目标渠道
- 是否有竞品
- 是否有 discussion / deep dive 支撑

输出 `高 / 中高 / 中 / 低`。

### Decision Drivers

从以下信号中提取 3 条核心结论依据：

- 高频障碍项
- 卖点数量与分散度
- 安全/信任相关顾虑
- 弱势人群共性拒绝点

### Value Proposition Conflicts

把卖点归类为：

- 防蛀功效
- 安全温和
- 趣味互动
- 美白净色
- 科学背书

基于规则判断：

- 主张过多
- 美白与儿童安全冲突
- 趣味点与核心功效闭环不足

### Segment Reasons

每个人群的原因说明由两部分组成：

- 该 segment 的高频偏好信号
- 该 segment 的高频顾虑信号

### Voice Alignment

原声分三类选样：

- 支持者：高意向且明确支持
- 犹豫者：中间意向且有阻力
- 拒绝者：低意向且有明确拒绝点

每条原声由 stance、reason_tag 和 evaluation signals 共同生成，不直接使用 discussion 模板句。

### Action Plan

动作建议分三层：

- 立即可做
- 下一轮测试前补齐
- 建议下一轮测试什么

### Competitive Limitations

无竞品时显式说明：

- 本次更偏单概念自洽性判断
- 不包含相对竞争优势评估

## HTML Structure

正式业务版 HTML 重组为 10 个模块：

1. 封面与任务信息
2. 一句话结论
3. 结论依据拆解
4. 核心指标概览
5. 输入信息回顾
6. 人群接受度 + 原因解释
7. 买点 / 障碍 / 价值主张诊断
8. 原声摘录
9. 下一步动作建议
10. 说明与可信度边界

## Testing Strategy

### Concept Report Tests

- 新 report schema 字段存在
- `business_recommendation` 不再暴露内部枚举
- `segment_opportunity` 中含原因解释
- `voice_of_consumer` 中每条原声含 `stance_label` 和 `reason_tag`
- 价值主张冲突在多卖点样本中可被识别

### HTML Tests

- HTML 渲染出新增模块标题
- HTML 展示业务 recommendation，而不是内部枚举
- HTML 渲染可信度等级、竞品边界、动作建议三层结构

## Risks

- 当前底层 legacy engine 的 discussion/deep_dive 文本仍偏模板化，因此原声只能先保证“标签一致”，不能保证已经达到高拟真对话质量
- 若后续需要更自然的原声，需要再引入真实 LLM 生成与二次校验

## Non-Goals

- 不重写 legacy engine
- 不增加新的 LangGraph 节点
- 不接新的外部模型依赖
