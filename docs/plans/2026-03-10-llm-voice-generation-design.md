# LLM Voice Generation And Stance Validation Design

**Date:** 2026-03-10

## Goal

为概念测试报告增加“LLM 原声生成 + stance 校验器”，在保持 stance 判定由规则层控制的前提下，提升消费者原声的自然度，同时避免原声与标签错位。

## Current Problem

- 当前报告中的原声是规则模板合成，结构稳定，但语气仍偏模板化。
- 历史 discussion 文本来自 legacy engine 的固定表达，容易出现“标签与原声错位”的问题。
- 如果直接把 stance 判定交给 LLM，会引入漂移，降低报告稳定性。

## Recommended Approach

采用“规则选样 + LLM 生成 + LLM 校验 + fallback”四段式增强。

### Step 1: Rule-Based Selection

继续由 `concept_testing.py` 负责：

- 选出支持者 / 犹豫者 / 拒绝者
- 确定 `stance_label`
- 确定 `reason_tag`

LLM 不参与“这个角色属于哪一类”的判定。

### Step 2: LLM Quote Generation

为每个选中的角色构造结构化输入：

- `agent_name`
- `segment`
- `stance_label`
- `reason_tag`
- `purchase_intention`
- `decision`
- `reasoning`
- `key_concerns`
- `preferred_features`
- 可选的 discussion / deep dive 信号

让 LLM 只返回 JSON：

```json
{
  "quote": "..."
}
```

约束：

- 只生成 1 句中文原声
- 符合消费者口吻
- stance 必须与输入一致
- 不得输出分析师口吻

### Step 3: LLM Stance Validation

对生成出的原声再跑一次独立校验：

输入：

- `quote`
- `expected_stance`
- `expected_reason_tag`

输出固定 JSON：

```json
{
  "is_consistent": true,
  "detected_stance": "犹豫者",
  "detected_reason": "安全感不足",
  "why": "..."
}
```

放行条件：

- `is_consistent == true`
- `detected_stance == expected_stance`
- `detected_reason` 与 `expected_reason_tag` 语义一致

### Step 4: Fallback

任何以下情况都回退到规则原声：

- 没有 AI client
- LLM 生成失败
- LLM 校验失败
- 校验结果 stance 不一致
- reason tag 不匹配

## File Changes

### `ai_clients.py`

新增两个面向报告层的能力：

- `generate_consumer_quote(payload)`
- `validate_consumer_quote(expected_stance, expected_reason_tag, quote)`

实现方式：

- 复用现有 `generate_text()`
- 用 `_extract_json_object()` 解析 JSON
- 出错时返回 fallback 结果，不抛异常给上层

### `concept_testing.py`

调整：

- `ConceptTestRunner` 支持注入 `ai_client`
- `_build_voice_entry()` 改为：
  - 先生成规则 fallback 原声
  - 尝试 LLM 生成
  - 尝试 LLM 校验
  - 通过则用 LLM 原声
  - 否则用 fallback

新增内部字段：

- `quote_generation_mode`
- `quote_validation`

### `dingtalk_bot.py` / `advanced_testing.py`

把现有 `ai_client` 传入 `ConceptTestRunner`，让线上报告链路也能使用该增强。

## Prompt Strategy

### Quote Prompt

只返回 JSON，不允许解释。

强约束：

- 18-40 个中文字符优先
- 只写一句
- 支持者必须表达愿意尝试
- 犹豫者必须表达仍需确认
- 拒绝者必须表达暂不买或不会优先买

### Validation Prompt

只返回 JSON，不允许重写原声。

校验只关注：

- stance 是否一致
- reason 是否语义一致

## Testing Strategy

### `tests/test_concept_testing.py`

新增 4 类测试：

1. 无 AI client 时使用规则原声
2. LLM 原声生成成功且校验通过时采用 LLM 原声
3. LLM 原声生成成功但校验失败时回退规则原声
4. LLM 调用异常时回退规则原声

### Regression

确保以下能力不受影响：

- 单方案报告生成
- 包装评审链路
- 钉钉群任务链路

## Non-Goals

- 不让 LLM 决定 stance 分类
- 不重写 legacy discussion 生成逻辑
- 不把原声增强独立成新的 LangGraph 节点
