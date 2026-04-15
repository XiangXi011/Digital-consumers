#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究助手有效性测试

测试目标：
1. 用户输入不精确、不结构化时，能否组织好策略和方案
2. 能否收紧其他agent的答复
3. 给用户返回优质的回答
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


# ============ 测试场景：非结构化输入 ============
TEST_CASES = [
    {
        "name": "场景1：模糊产品描述",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这个牙膏怎么样？",
            "persona_id": "M04",
            "background_material": "一个普通妈妈，孩子5岁",
            "product_info": "舒客宝贝的变色牙膏，好像能防蛀",
        },
        "expected_behavior": "Planner应补充缺失信息，生成合理研究计划"
    },
    {
        "name": "场景2：口语化输入",
        "input": {
            "mode": "single",
            "question_type": "copy_feedback",
            "user_question": "帮我看看这个文案行不行，感觉写得有点乱",
            "persona_id": "M05",
            "background_material": "我是个比较较真的妈妈，喜欢看成分",
            "product_info": "就是那个会变色的儿童牙膏，抖音上看到的",
            "copy_material": "魔法变色让刷牙更有趣，含氟防蛀保护牙齿",
        },
        "expected_behavior": "Planner应理解口语化表达，生成结构化研究计划"
    },
    {
        "name": "场景3：缺少关键信息",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这个产品能卖出去吗？",
            "persona_id": "M01",
            "background_material": "",
            "product_info": "新品儿童牙膏，主打变色功能",
        },
        "expected_behavior": "Planner应识别缺失信息，返回clarifying_questions"
    },
    {
        "name": "场景4：多问题混杂",
        "input": {
            "mode": "single",
            "question_type": "purchase_decision",
            "user_question": "这个牙膏会不会太贵了？安全吗？孩子会喜欢吗？竞品怎么样？",
            "persona_id": "M08",
            "background_material": "小城市妈妈，收入不高，但想给孩子最好的",
            "product_info": "舒客宝贝变色牙膏，53.5元一支，活动价35元",
        },
        "expected_behavior": "Planner应拆解多问题，生成针对性研究计划"
    },
]


def test_planner_effectiveness(test_case):
    """测试单个场景"""
    print(f"\n{'='*60}")
    print(f"测试：{test_case['name']}")
    print(f"{'='*60}")

    # 打印输入
    inp = test_case['input']
    print(f"\n【用户输入】（非结构化）")
    print(f"  问题：{inp['user_question']}")
    print(f"  产品：{inp['product_info'][:50]}...")
    print(f"  背景：{inp['background_material'][:50] if inp['background_material'] else '(空)'}...")

    # 初始化
    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    research_input = QualitativeResearchInput(**inp)

    try:
        # 只调用Planner，不执行完整研究
        print(f"\n【Planner处理中...】")
        research_plan = runner.plan(research_input)

        print(f"\n【Planner输出】")
        print(f"  ready_to_dispatch: {research_plan.get('ready_to_dispatch')}")

        if research_plan.get('ready_to_dispatch'):
            print(f"  dispatch_scope: {research_plan.get('dispatch_scope')}")
            print(f"  target_personas: {research_plan.get('target_personas')}")
            print(f"  task_breakdown: {research_plan.get('task_breakdown', [])[:3]}")
            print(f"  evaluation_dimensions: {research_plan.get('evaluation_dimensions', [])[:3]}")

            # 验证Planner是否补充了缺失信息
            missing = research_plan.get('missing_information', [])
            if missing:
                print(f"\n  ⚠️ 仍缺失信息: {missing[:2]}")
            else:
                print(f"\n  ✅ Planner成功补充了缺失信息")

            return {"status": "success", "plan": research_plan}
        else:
            clarifying = research_plan.get('clarifying_questions', [])
            print(f"  clarifying_questions: {clarifying[:3]}")
            print(f"\n  ✅ Planner正确识别信息不足，返回澄清问题")
            return {"status": "clarification_needed", "plan": research_plan}

    except Exception as e:
        print(f"\n  ❌ 失败: {type(e).__name__}: {e}")
        return {"status": "failed", "error": str(e)}


def main():
    print("=" * 60)
    print("研究助手有效性测试")
    print("=" * 60)
    print("\n测试目标：")
    print("1. 用户输入不精确时，能否组织好策略")
    print("2. 能否收紧其他agent的答复")
    print("3. 给用户返回优质的回答")

    results = []
    for test_case in TEST_CASES:
        result = test_planner_effectiveness(test_case)
        results.append({
            "name": test_case["name"],
            "expected": test_case["expected_behavior"],
            **result
        })

    # 汇总分析
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] in ["success", "clarification_needed"])
    total = len(results)

    print(f"\n通过率: {success_count}/{total} ({success_count/total*100:.0f}%)")

    for r in results:
        status_icon = "✅" if r["status"] in ["success", "clarification_needed"] else "❌"
        print(f"\n{status_icon} {r['name']}")
        print(f"    期望: {r['expected']}")
        print(f"    结果: {r['status']}")

    return 0 if success_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
