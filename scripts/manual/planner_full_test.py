#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究助手有效性测试 - 完整版

测试目标：
1. 信息不足时：返回澄清问题
2. 信息足够时：生成研究计划并执行
3. 收紧Agent答复，返回优质回答
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


# ============ 测试场景 ============
TEST_CASES = [
    {
        "name": "场景1：信息不足 - 应返回澄清问题",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这个牙膏怎么样？",
            "persona_id": "M04",
            "background_material": "一个普通妈妈",
            "product_info": "舒客宝贝的变色牙膏",
        },
        "expect_clarification": True,
    },
    {
        "name": "场景2：信息足够 - 应执行研究",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这款变色牙膏你会给孩子买吗？",
            "persona_id": "M04",
            "background_material": "M04高线忙碌派：一线城市30-40岁职场妈妈，月收入15000-25000元，追求省心高效，孩子5岁刷牙需要监督",
            "product_info": "舒客宝贝魔法变色儿童牙膏，53.5元活动价35元，2-12岁适用，含氟+羟基磷灰石防蛀，刷牙2分钟变色",
        },
        "expect_clarification": False,
    },
    {
        "name": "场景3：口语化但信息足够 - 应执行研究",
        "input": {
            "mode": "single",
            "question_type": "copy_feedback",
            "user_question": "帮我看看这几句话哪句最吸引人",
            "persona_id": "M05",
            "background_material": "我比较较真，喜欢看成分，孩子6岁",
            "product_info": "舒客宝贝变色牙膏，含氟防蛀，35元",
            "copy_material": "A: 魔法变色让娃主动刷牙 | B: 含氟+羟基磷灰石双重防蛀 | C: 抗糖护齿温和健白",
        },
        "expect_clarification": False,
    },
]


def run_test(test_case):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"{test_case['name']}")
    print(f"{'='*60}")

    inp = test_case['input']
    print(f"\n用户输入：{inp['user_question']}")
    print(f"产品信息：{inp['product_info'][:60]}...")

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    research_input = QualitativeResearchInput(**inp)

    try:
        # 调用Planner
        print("\n[Step 1] Planner分析输入...")
        research_plan = runner.plan(research_input)

        if research_plan.get('ready_to_dispatch'):
            print(f"  ✅ Planner判定：信息足够，可以执行研究")
            print(f"  dispatch_scope: {research_plan.get('dispatch_scope')}")
            print(f"  target_personas: {research_plan.get('target_personas')}")

            # 执行完整研究
            print("\n[Step 2] 执行研究...")
            report = runner.run(research_input, research_plan)

            consumer_voice = report.get("consumer_voice", [])
            if consumer_voice:
                p = consumer_voice[0]
                print(f"\n[Step 3] Agent输出（已收紧）：")
                print(f"  persona: {p.get('persona_name')}")
                print(f"  stance: {p.get('stance')}")
                print(f"  purchase_intent: {p.get('backend_evaluation', {}).get('purchase_intent')}")
                print(f"\n  原话：{p.get('voice_line', '')[:200]}...")

                # 验证输出质量
                quality_check = {
                    "has_stance": bool(p.get('stance')),
                    "has_voice_line": len(p.get('voice_line', '')) > 20,
                    "has_scores": bool(p.get('rubric_scores')),
                    "has_evaluation": bool(p.get('backend_evaluation')),
                }
                quality_score = sum(quality_check.values()) / len(quality_check)

                print(f"\n  输出质量：{quality_score*100:.0f}%")
                for k, v in quality_check.items():
                    print(f"    {k}: {'✅' if v else '❌'}")

                return {"status": "success", "clarification": False, "quality": quality_score}
            else:
                print("  ❌ 未获取到Agent输出")
                return {"status": "no_output", "clarification": False}
        else:
            clarifying = research_plan.get('clarifying_questions', [])
            print(f"  ✅ Planner判定：信息不足，需要澄清")
            print(f"\n  澄清问题：")
            for i, q in enumerate(clarifying[:3], 1):
                print(f"    {i}. {q}")

            if test_case['expect_clarification']:
                return {"status": "success", "clarification": True}
            else:
                return {"status": "unexpected_clarification", "clarification": True}

    except Exception as e:
        print(f"\n  ❌ 失败: {type(e).__name__}: {e}")
        return {"status": "failed", "error": str(e)}


def main():
    print("=" * 60)
    print("研究助手有效性测试 - 完整版")
    print("=" * 60)
    print("\n测试目标：")
    print("1. 信息不足时：返回澄清问题")
    print("2. 信息足够时：生成研究计划并执行")
    print("3. 收紧Agent答复，返回优质回答")

    results = []
    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append({"name": test_case["name"], "expect": test_case["expect_clarification"], **result})

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    success = 0
    for r in results:
        is_success = r["status"] == "success"
        if is_success:
            success += 1
        icon = "✅" if is_success else "❌"
        expect = "应返回澄清" if r["expect"] else "应执行研究"
        print(f"\n{icon} {r['name']}")
        print(f"    期望: {expect}")
        print(f"    结果: {r['status']}")

    print(f"\n通过率: {success}/{len(results)} ({success/len(results)*100:.0f}%)")

    return 0 if success == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
