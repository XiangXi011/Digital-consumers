#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人物设定差异化测试"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner

# 产品信息（统一）
PRODUCT_INFO = """儿童益生菌防蛀牙膏产品信息：
- 价格：29.9元/支（100g），属于中端价位
- 核心卖点：低氟防蛀+益生菌护龈，双重保护
- 主要成分：氟化钠（0.05%）、益生菌、木糖醇
- 安全认证：国家口腔护理产品质量认证，符合GB/T 8372标准
- 适用年龄：3-12岁儿童
- 销售渠道：天猫、京东、线下母婴店
- 竞品对比：价格低于舒适达儿童牙膏（45元），高于云南白药儿童牙膏（19.9元）
- 用户评价：新品牌，目前评价较少，整体好评率92%"""

# 测试画像
TEST_PERSONAS = [
    {
        "id": "M01",
        "name": "宠爱富养家",
        "background": """M01宠爱富养家画像：
- 一线城市35-45岁高收入妈妈，月收入30000+元
- 只买贵的，不买对的，进口优先，大牌优先
- 月度儿童用品预算2000-5000元
- 对价格不敏感，但对品质要求极高
- 偏好进口品牌如舒适达、高露洁等""",
        "expected_stance": "rejecting",  # 29.9元太便宜
    },
    {
        "id": "M04",
        "name": "高线忙碌派",
        "background": """M04高线忙碌派画像：
- 一线城市30-40岁职场妈妈，月收入15000-25000元
- 时间紧张，追求省心高效，相信专业背书
- 月度儿童用品预算500-1000元
- 更看重便利性和品质，不想花时间选择
- 对国产品牌持开放态度""",
        "expected_stance": "interested",  # 价格合适，品质不错
    },
    {
        "id": "M08",
        "name": "佛系粗养家",
        "background": """M08佛系粗养家画像：
- 三四线城市25-35岁妈妈，月收入5000-10000元
- 认为孩子用品够用就行，安全便宜最重要
- 月度儿童用品预算200-500元
- 不追求高端品牌，注重性价比
- 倾向于购买平价产品""",
        "expected_stance": "hesitant",  # 29.9元可能偏贵
    },
]

def test_persona(persona_info):
    """测试单个画像"""
    print(f"\n{'='*60}")
    print(f"测试画像: {persona_info['id']} - {persona_info['name']}")
    print(f"{'='*60}")

    # 初始化
    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这款儿童牙膏你会不会买？为什么？",
        persona_id=persona_info["id"],
        background_material=persona_info["background"],
        product_info=PRODUCT_INFO,
        copy_material="专业防蛀，益生菌护龈，孩子喜欢，妈妈省心。",
    )

    try:
        report = runner.run(research_input)
        consumer_voice = report.get("consumer_voice", [])

        if not consumer_voice:
            print("[FAILED] 未获取到输出")
            return None

        persona = consumer_voice[0]
        backend_eval = persona.get("backend_evaluation", {})
        rubric_scores = persona.get("rubric_scores", {})

        result = {
            "id": persona_info["id"],
            "name": persona_info["name"],
            "stance": persona.get("stance", ""),
            "voice_line": persona.get("voice_line", ""),
            "purchase_intent": backend_eval.get("purchase_intent", ""),
            "purchase_score": backend_eval.get("purchase_score", 0),
            "concerns": persona.get("concerns", []),
            "motivations": persona.get("motivations", []),
            "rubric_scores": rubric_scores,
        }

        print(f"\n[SUCCESS] 测试通过")
        print(f"  立场: {result['stance']}")
        print(f"  购买意图: {result['purchase_intent']} (分数: {result['purchase_score']})")
        print(f"  原话: {result['voice_line'][:120]}...")
        print(f"\n  评分维度:")
        for dim, score in rubric_scores.items():
            print(f"    {dim}: {score}")

        return result

    except Exception as e:
        print(f"[FAILED] {type(e).__name__}: {e}")
        return None

def main():
    print("=" * 60)
    print("人物设定差异化测试")
    print("=" * 60)

    results = []
    for persona in TEST_PERSONAS:
        result = test_persona(persona)
        if result:
            results.append(result)

    # 分析结果
    print("\n" + "=" * 60)
    print("差异化分析")
    print("=" * 60)

    if len(results) < 2:
        print("测试结果不足，无法进行差异化分析")
        return 1

    # 检查立场差异
    stances = [r["stance"] for r in results]
    stance_unique = len(set(stances))

    # 检查购买意图差异
    intents = [r["purchase_intent"] for r in results]
    intent_unique = len(set(intents))

    # 检查评分差异
    scores = [r["purchase_score"] for r in results]
    score_range = max(scores) - min(scores) if scores else 0

    print(f"\n测试画像数量: {len(results)}")
    print(f"立场种类数: {stance_unique} ({', '.join(stances)})")
    print(f"购买意图种类数: {intent_unique} ({', '.join(intents)})")
    print(f"购买分数范围: {min(scores):.2f} - {max(scores):.2f} (差值: {score_range:.2f})")

    print("\n详细对比:")
    for r in results:
        print(f"\n  {r['name']} ({r['id']}):")
        print(f"    立场: {r['stance']}")
        print(f"    购买意图: {r['purchase_intent']} ({r['purchase_score']:.2f})")
        print(f"    原话: {r['voice_line'][:80]}...")

    # 判断差异化是否足够
    print("\n" + "-" * 60)
    if stance_unique >= 2 or intent_unique >= 2 or score_range >= 1.0:
        print("[SUCCESS] 人物设定差异化验证通过!")
        print("不同画像产生了显著不同的反馈，说明人物设定有效影响了LLM输出。")
        return 0
    else:
        print("[WARNING] 人物设定差异化不足")
        print("不同画像的反馈相似，可能需要优化prompt或调整模型参数。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
