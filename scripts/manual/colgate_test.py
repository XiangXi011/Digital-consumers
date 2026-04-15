#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舒客变色牙膏产品测试

测试产品：
- 舒客宝贝羟基磷灰石抗糖色修健白含氟防蛀儿童牙膏
- 核心卖点：魔法变色、含氟防蛀、抗糖护齿、温和健白

测试维度：
1. 产品概念测试
2. 购买决策测试
3. 文案和卖点反馈测试
"""

import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


# 产品信息
PRODUCT_INFO = """舒客宝贝变色儿童牙膏产品信息：
- 品牌：舒客宝贝（国产专业儿童口腔护理品牌，隶属于薇美姿集团）
- 产品名：羟基磷灰石抗糖色修健白含氟防蛀儿童牙膏
- 价格：39.9元/支（100g），大促期间35元，属于中高端价位
- 核心卖点：
  1、魔法变色，引导孩子主动刷牙（刷牙过程中牙膏颜色会从蓝色变成粉色）
  2、含氟（氟化钠0.05%）+ 羟基磷灰石，双重防蛀修护牙釉质
  3、抗糖护齿，温和健白不刺激
- 主要成分：氟化钠、羟基磷灰石（修复牙釉质）、抗糖成分、木糖醇
- 安全认证：符合国家GB/T 8372标准，通过口腔护理产品质量认证
- 适用年龄：3-12岁儿童
- 功能特点：变色趣味性 + 防蛀 + 修护 + 美白
- 销售渠道：天猫旗舰店、京东自营、线下母婴店
- 竞品对比：价格高于云南白药儿童牙膏（19.9元），低于进口品牌如舒适达儿童牙膏（59元）"""

COPY_MATERIAL = """
文案选项：
A："魔法变色，让娃主动刷够 2 分钟"
B："含氟 + 羟基磷灰石，双重防蛀修护牙釉质"
C："抗糖护齿，温和健白不伤牙"
"""

# 测试问题
QUESTIONS = {
    "product_concept": """一、产品概念方面
1、这款会变色的儿童牙膏，你听着觉得有吸引力吗？
2、哪个点最打动你？是魔法变色、含氟防蛀、抗糖护齿还是温和健白？
3、对于这款产品，你最大的顾虑是什么？""",

    "purchase_decision": """二、购买决策方面
1、看了这款会变色的儿童牙膏，你会不会想给孩子试试呀？
2、你最担心的点是什么，比如安全、效果还是价格？
3、孩子平时刷牙乖不乖，你是不是就想找能让他主动刷牙的牙膏？
4、比起普通儿童牙膏，你愿意为这个变色功能多花点钱吗？
5、买之前你最想确认清楚哪一点，才会放心下单？""",

    "copy_feedback": """三、文案和卖点反馈方面
1、下面几句文案，你觉得哪句最吸引你？
A："魔法变色，让娃主动刷够 2 分钟"
B："含氟 + 羟基磷灰石，双重防蛀修护牙釉质"
C："抗糖护齿，温和健白不伤牙"
2、你觉得哪个卖点最重要？原因是什么？
3、有没有哪句描述让你觉得不清楚、或者不太可信？"""
}

# 测试画像（选择3个代表性的）
TEST_PERSONAS = [
    {
        "id": "M01",
        "name": "宠爱富养家",
        "background": """M01宠爱富养家画像：
- 一线城市35-45岁高收入妈妈，月收入30000+元
- 只买贵的不买对的，进口优先大牌优先
- 月度儿童用品预算2000-5000元
- 认为价格高=品质好，便宜没好货
- 偏好进口品牌如舒适达、高露洁等
- 孩子4岁，刷牙不太乖，经常要催""",
    },
    {
        "id": "M04",
        "name": "高线忙碌派",
        "background": """M04高线忙碌派画像：
- 一线城市30-40岁职场妈妈，月收入15000-25000元
- 时间紧张，追求省心高效，相信专业背书
- 月度儿童用品预算500-1000元
- 不喜欢花哨包装，偏好专业简洁
- 孩子5岁，刷牙需要监督，嫌麻烦""",
    },
    {
        "id": "M05",
        "name": "品质精算师",
        "background": """M05品质精算师画像：
- 一二线城市30-40岁妈妈，高学历，注重成分
- 会仔细研究配料表和用户评价
- 追求性价比而非单纯低价
- 看成分表、比数据、讲逻辑
- 孩子6岁，刷牙还算配合，但会偷懒""",
    },
]


def run_test(persona_info, question_type, question_text):
    """运行单个测试"""
    print(f"\n  测试维度: {question_type}")

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    research_input = QualitativeResearchInput(
        mode="single",
        question_type=question_type,
        user_question=question_text,
        persona_id=persona_info["id"],
        background_material=persona_info["background"],
        product_info=PRODUCT_INFO,
        copy_material=COPY_MATERIAL,
    )

    try:
        report = runner.run(research_input)
        consumer_voice = report.get("consumer_voice", [])

        if not consumer_voice:
            return None

        persona = consumer_voice[0]
        return {
            "question_type": question_type,
            "persona_id": persona_info["id"],
            "persona_name": persona_info["name"],
            "stance": persona.get("stance", ""),
            "voice_line": persona.get("voice_line", ""),
            "purchase_intent": persona.get("backend_evaluation", {}).get("purchase_intent", ""),
            "purchase_score": persona.get("backend_evaluation", {}).get("purchase_score", 0),
            "rubric_scores": persona.get("rubric_scores", {}),
            "concerns": persona.get("concerns", []),
            "motivations": persona.get("motivations", []),
        }
    except Exception as e:
        print(f"    [ERROR] {e}")
        return None


def main():
    print("=" * 70)
    print("舒客变色牙膏产品测试")
    print("=" * 70)
    print(f"\n产品：舒客宝贝羟基磷灰石抗糖色修健白含氟防蛀儿童牙膏")
    print(f"核心卖点：魔法变色 | 含氟防蛀 | 抗糖护齿 | 温和健白")
    print(f"测试画像：{len(TEST_PERSONAS)}个")

    all_results = []

    for persona in TEST_PERSONAS:
        print(f"\n{'='*70}")
        print(f"画像：{persona['id']} - {persona['name']}")
        print(f"{'='*70}")

        persona_results = {"persona": persona, "tests": {}}

        for q_type, q_text in QUESTIONS.items():
            result = run_test(persona, q_type, q_text)
            if result:
                persona_results["tests"][q_type] = result
                print(f"    [OK] stance={result['stance']}, intent={result['purchase_intent']}")

        all_results.append(persona_results)
        time.sleep(2)  # 避免API限流

    # 输出分析报告
    print("\n" + "=" * 70)
    print("测试分析报告")
    print("=" * 70)

    # 1. 产品概念反馈汇总
    print("\n【一、产品概念反馈】")
    for r in all_results:
        persona = r["persona"]
        test = r["tests"].get("product_concept")
        if test:
            print(f"\n  {persona['name']} ({persona['id']}):")
            print(f"    立场: {test['stance']}")
            print(f"    原话: {test['voice_line'][:150]}...")

    # 2. 购买决策汇总
    print("\n【二、购买决策汇总】")
    intent_summary = {}
    for r in all_results:
        persona = r["persona"]
        test = r["tests"].get("purchase_decision")
        if test:
            intent = test["purchase_intent"]
            intent_summary[intent] = intent_summary.get(intent, 0) + 1
            print(f"\n  {persona['name']}: {intent} (分数: {test['purchase_score']:.2f})")
            print(f"    原话: {test['voice_line'][:120]}...")

    print(f"\n  购买意图分布: {intent_summary}")

    # 3. 文案反馈汇总
    print("\n【三、文案和卖点反馈】")
    for r in all_results:
        persona = r["persona"]
        test = r["tests"].get("copy_feedback")
        if test:
            print(f"\n  {persona['name']}:")
            print(f"    原话: {test['voice_line'][:150]}...")

    # 4. 总结
    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)

    total_tests = sum(len(r["tests"]) for r in all_results)
    print(f"\n完成测试: {total_tests}/{len(TEST_PERSONAS) * len(QUESTIONS)}")

    # 购买意图统计
    intents = []
    for r in all_results:
        for test in r["tests"].values():
            if test.get("purchase_intent"):
                intents.append(test["purchase_intent"])

    if intents:
        buy_count = intents.count("buy")
        maybe_count = intents.count("maybe")
        reject_count = intents.count("reject")
        print(f"\n购买意图统计:")
        print(f"  会买 (buy): {buy_count}")
        print(f"  犹豫 (maybe): {maybe_count}")
        print(f"  不买 (reject): {reject_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
