#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究助手完整流程测试

验证：
1. Planner能否组织策略
2. Persona Agent能否根据设定产生差异化反馈
3. 输出是否优质
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


# 完整产品信息（之前测试成功）
PRODUCT_INFO = """舒客宝贝魔法变色儿童牙膏产品信息：
【基本信息】
- 品牌：舒客宝贝（薇美姿集团旗下，成立于2014年，国产专业儿童口腔护理品牌）
- 产品名：羟基磷灰石抗糖色修健白含氟防蛀儿童牙膏（魔法变色款）
- 规格：60g/支
- 适用年龄：2-12岁儿童
- 香型：莓莓酸奶香型（清甜温和不刺激）
- 膏体颜色：粉色膏体，刷牙2分钟后变成浅蓝色泡泡

【价格信息】
- 天猫标价：53.5元/支
- 活动价：约30.72-34.72元（立减12元+立减4.95元+9.5折）
- 历史最低：30.72元（慢慢买2026-03-19记录）

【核心卖点】
1、魔法变色：刷牙2分钟，粉色膏体变浅蓝泡泡，可视化清洁体验
2、四效防蛀体系：乳酸钙+酪蛋白磷酸肽(CPPs)+氟化钠+羟基磷灰石
3、12小时长效抗糖酸防蛀
4、温和清洁：软性磨料水合硅石，减少牙釉质磨损

【详细成分】
- 氟化钠：强化牙釉质，提高耐酸力
- 羟基磷灰石(HAP)：修复牙釉质微裂纹
- 酪蛋白磷酸肽(CPPs)：促进钙磷吸收
- 乳酸钙：强健牙齿
- 水合硅石：软性磨料，轻柔清洁
- 变色粒子：食用级色素，安全无害

【安全认证】
- 经过超20项安全测试，各项指标均符合标准
- 温和低刺激，适合儿童娇嫩口腔

【用户评价】
- 店铺评分：物流4.9、服务4.9、商品描述4.9（满分5分）
- 用户反馈："包装挺好的，物品没有损坏，质量还行，宝宝说不变色"

【竞品参考】
- 舒客宝贝抗糖盾含氟儿童牙膏：9.9元
- 云南白药儿童牙膏：19.9元
- 舒适达儿童牙膏：59元"""


TEST_CASES = [
    {
        "name": "测试1：M01 宠爱富养家",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这款会变色的儿童牙膏你会给孩子买吗？为什么？",
            "persona_id": "M01",
            "background_material": "M01宠爱富养家：一线城市35-45岁高收入妈妈，月收入30000+元，只买贵的不买对的，进口优先大牌优先，月度儿童用品预算2000-5000元，孩子4岁刷牙不太乖",
            "product_info": PRODUCT_INFO,
        },
    },
    {
        "name": "测试2：M04 高线忙碌派",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这款会变色的儿童牙膏你会给孩子买吗？为什么？",
            "persona_id": "M04",
            "background_material": "M04高线忙碌派：一线城市30-40岁职场妈妈，月收入15000-25000元，追求省心高效，相信专业背书，月度儿童用品预算500-1000元，孩子5岁刷牙需要监督",
            "product_info": PRODUCT_INFO,
        },
    },
    {
        "name": "测试3：M05 品质精算师",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这款会变色的儿童牙膏你会给孩子买吗？为什么？",
            "persona_id": "M05",
            "background_material": "M05品质精算师：一二线城市30-40岁高学历妈妈，注重成分和数据，会仔细研究配料表和用户评价，追求性价比而非单纯低价，孩子6岁刷牙还算配合",
            "product_info": PRODUCT_INFO,
        },
    },
    {
        "name": "测试4：M08 佛系粗养家",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这款会变色的儿童牙膏你会给孩子买吗？为什么？",
            "persona_id": "M08",
            "background_material": "M08佛系粗养家：三四线城市25-35岁妈妈，月收入5000-10000元，认为孩子用品够用就行，安全便宜最重要，不追求高端品牌，孩子3岁",
            "product_info": PRODUCT_INFO,
        },
    },
]


def run_test(test_case):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"{test_case['name']}")
    print(f"{'='*60}")

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    research_input = QualitativeResearchInput(**test_case['input'])

    try:
        report = runner.run(research_input)
        consumer_voice = report.get("consumer_voice", [])

        if consumer_voice:
            p = consumer_voice[0]
            eval_data = p.get("backend_evaluation", {})

            print(f"\n【输出结果】")
            print(f"  persona: {p.get('persona_name')}")
            print(f"  stance: {p.get('stance')}")
            print(f"  purchase_intent: {eval_data.get('purchase_intent')}")
            print(f"  purchase_score: {eval_data.get('purchase_score')}")
            print(f"\n  原话：\n  {p.get('voice_line', '')}")

            # 质量检查
            quality = {
                "有立场": bool(p.get('stance')),
                "有原话": len(p.get('voice_line', '')) > 30,
                "有评分": bool(p.get('rubric_scores')),
                "有意图": bool(eval_data.get('purchase_intent')),
                "有顾虑": bool(p.get('concerns')),
                "有动机": bool(p.get('motivations')),
            }

            print(f"\n  输出质量检查：")
            for k, v in quality.items():
                print(f"    {k}: {'✅' if v else '❌'}")

            return {"status": "success", "stance": p.get('stance'), "intent": eval_data.get('purchase_intent'), "quality": quality}
        else:
            print("\n  ❌ 未获取到输出")
            return {"status": "no_output"}

    except Exception as e:
        print(f"\n  ❌ 失败: {type(e).__name__}: {e}")
        return {"status": "failed"}


def main():
    print("=" * 60)
    print("研究助手完整流程测试")
    print("=" * 60)

    results = []
    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append({"name": test_case["name"], **result})

    # 汇总分析
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    success_count = sum(1 for r in results if r.get("status") == "success")
    total = len(results)

    print(f"\n通过率: {success_count}/{total} ({success_count/total*100:.0f}%)")

    print("\n【各画像反馈对比】")
    for r in results:
        if r.get("status") == "success":
            print(f"  {r['name']}: stance={r.get('stance')}, intent={r.get('intent')}")

    # 检查差异化
    stances = [r.get('stance') for r in results if r.get('status') == 'success']
    intents = [r.get('intent') for r in results if r.get('status') == 'success']

    print(f"\n【差异化分析】")
    print(f"  立场种类数: {len(set(stances))} ({', '.join(set(stances))})")
    print(f"  购买意图种类数: {len(set(intents))} ({', '.join(set(intents))})")

    if len(set(stances)) >= 2 or len(set(intents)) >= 2:
        print("\n  ✅ 人物设定差异化验证通过！")
    else:
        print("\n  ⚠️ 人物设定差异化不足")

    return 0


if __name__ == "__main__":
    sys.exit(main())
