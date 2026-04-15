# 数字消费者角色单元系统

## 系统概述

**200个可控数字人物库** - 8类主画像 × 每类25个数字人物

这是一个混合架构的消费者模拟系统，结合了代码层的结构化逻辑和LLM层的自然语言生成能力。

---

## 核心能力

每个数字人物具备：

1. **稳定的人设边界** - 始终符合所属母群与子型特征
2. **决策能力** - 基于自身偏好对产品、价格、卖点、包装、内容做判断
3. **对话能力** - 参与短轮次讨论，与主持人或其他角色交流
4. **有限记忆** - 记住当前测试任务中的关键上下文
5. **行为模拟** - 模拟浏览、比较、收藏、加购、购买、评价、分享等动作
6. **可批量调度** - 支持单人评测、小组讨论、整群投票、跨人群对比

---

## 三层运行模式

### 第一层：批量静默评估 (Tier 1)

**用途**：快速获取200个角色的产品接受度

```python
# 加载200个Agent
agents = load_agents_from_json("persona_samples_complete.json")
orchestrator = AgentOrchestrator()
orchestrator.load_agents([a.to_dict() for a in agents])

# 创建测试产品
product = Product(
    name="舒客儿童益生菌牙膏",
    brand="舒客",
    price=39.9,
    features=["益生菌配方", "低氟防蛀"],
    selling_points=["医生推荐", "99%天然成分"],
    rating=4.6
)

# 批量评估 (200个角色，秒级完成)
results = orchestrator.batch_evaluate(product)
report = orchestrator.generate_report(results)

# 输出
print(f"平均购买意愿: {report['summary']['avg_intention']:.0%}")
print(f"预估转化率: {report['summary']['estimated_conversion_rate']}%")
```

**输出**：
- 200个角色的量化评分
- 决策分布统计
- 人群段对比分析
- 关键发现和建议

---

### 第二层：小组讨论 (Tier 2)

**用途**：观察角色间的观点碰撞，理解购买/拒绝的深层原因

```python
# 分层抽样选择代表 (8-12人)
representatives = orchestrator.select_representatives(
    method="stratified",  # 按子型分层
    count=8
)

# 执行小组讨论
discussion = orchestrator.group_discussion(
    topic="你会给孩子买这款牙膏吗？",
    product=product,
    participant_ids=representatives
)

# 输出讨论结果
print(f"共识度: {discussion['consensus_level']:.0%}")
print(f"支持者: {len([o for o in discussion['opinions'] if o['opinion']['purchase_intention'] > 0.5])}")
```

**输出**：
- 各方观点表达
- 群体共识度分析
- 关键洞察提取
- 情感倾向分析

---

### 第三层：深度追问 (Tier 3)

**用途**：深入理解典型用户的决策逻辑，挖掘潜在需求

```python
# 选择关键角色 (高意愿/犹豫/拒绝各1人)
key_agents = [
    sorted_results[0]['agent_id'],      # 高意愿
    sorted_results[100]['agent_id'],    # 中间派
    sorted_results[-1]['agent_id']      # 明确拒绝
]

# 深度访谈
questions = [
    "描述一下你平时给孩子选购牙膏的完整过程",
    "这款产品的哪些特点最吸引你？",
    "如果让你提一个改进建议，你会说什么？"
]

for agent_id in key_agents:
    interview = orchestrator.deep_dive(agent_id, questions)
    # 分析动机和情感触发点
```

**输出**：
- 结构化问答
- 潜在动机分析
- 情感触发点识别
- 产品改进建议

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    编排层 (Orchestrator)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 批量调度     │  │ 小组讨论     │  │ 深度访谈            │  │
│  │ batch_eval  │  │ group_disc  │  │ deep_dive           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    角色层 (200 Agents)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DigitalConsumerAgent                               │   │
│  │  ├── evaluate_product()    # 产品评估               │   │
│  │  ├── simulate_behavior()   # 行为模拟               │   │
│  │  ├── generate_response()   # 对话生成 (LLM)         │   │
│  │  ├── participate_discussion() # 参与讨论            │   │
│  │  └── deep_interview()      # 深度访谈               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    数据层 (Persona Data)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ basic_profile│  │mindset_profile│  │consumption_profile │  │
│  │ (基础画像)   │  │ (心智特征)    │  │ (消费偏好)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 使用场景

### 场景1：新产品概念测试
```python
# 测试多个产品概念
concepts = [concept_a, concept_b, concept_c]
for concept in concepts:
    results = orchestrator.batch_evaluate(concept)
    # 对比不同概念的接受度
```

### 场景2：定价策略优化
```python
# 测试不同价格点
prices = [29.9, 39.9, 49.9, 59.9]
for price in prices:
    product.price = price
    results = orchestrator.batch_evaluate(product)
    # 分析价格敏感度曲线
```

### 场景3：卖点优化
```python
# 测试不同卖点组合
selling_points_variants = [
    ["医生推荐", "天然成分"],
    ["网红爆款", "颜值在线"],
    ["性价比之王", "大容量"]
]
# 对比不同卖点的吸引力
```

### 场景4：人群精准定位
```python
# 分析哪个人群最匹配
for segment_id in orchestrator.segments.keys():
    results = orchestrator.batch_evaluate(product, segment_filter=segment_id)
    # 找出接受度最高的人群段
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `digital_consumer_agents.py` | 核心系统代码，包含Agent类和编排器 |
| `demo_three_tier_system.py` | 三层运行模式完整演示 |
| `persona_samples_complete.json` | 200个角色原始数据 |
| `simulation_report_*.json` | 生成的模拟报告 |

---

## 扩展建议

### 1. 接入LLM增强对话能力

当前系统的 `generate_response()` 使用简化逻辑，建议接入真实LLM：

```python
def generate_response(self, message: str, context: Dict = None) -> str:
    """调用LLM生成自然语言回复"""
    prompt = self.get_persona_prompt()
    
    # 调用OpenAI/Claude等LLM
    response = llm_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message}
        ]
    )
    
    return response.choices[0].message.content
```

### 2. 添加可视化报告

```python
import matplotlib.pyplot as plt

# 决策分布饼图
plt.pie(report['decision_distribution'].values(), 
        labels=report['decision_distribution'].keys())

# 人群接受度对比柱状图
segments = report['segment_analysis']
plt.bar(segments.keys(), [s['avg_intention'] for s in segments.values()])
```

### 3. 添加A/B测试框架

```python
class ABTest:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    def test(self, variant_a, variant_b, sample_size=100):
        """对比两个产品变体"""
        results_a = self.orchestrator.batch_evaluate(variant_a)
        results_b = self.orchestrator.batch_evaluate(variant_b)
        
        return {
            'variant_a': self._analyze(results_a),
            'variant_b': self._analyze(results_b),
            'winner': 'A' if results_a > results_b else 'B'
        }
```

---

## 注意事项

1. **角色一致性**：系统通过结构化数据确保角色行为一致，但LLM生成内容时需要验证人设一致性

2. **计算效率**：第一层批量评估完全基于代码计算，200个角色可在秒级完成；第二层和第三层涉及LLM调用，需要更长时间

3. **结果解释**：模拟结果是基于画像数据的推断，应结合实际市场调研验证

4. **隐私保护**：角色数据为虚构，但设计时参考了真实人群特征，使用时注意数据安全

---

## 快速开始

```bash
# 运行完整演示
cd /Users/xiangdong/.openclaw/workspace/reports
python3 demo_three_tier_system.py

# 查看生成的报告
cat simulation_report_*.json
```

---

*系统版本: 1.0*  
*创建时间: 2026-03-07*
