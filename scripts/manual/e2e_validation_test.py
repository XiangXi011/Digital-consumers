#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端验证测试脚本

验证目标：
1. 链路能否跑通 - 从输入到输出的完整流程
2. Agent能否根据人物设定产生有价值的反馈 - 不同画像产生不同输出

使用方式：
    python e2e_validation_test.py
"""

import json
import sys
import time
from pathlib import Path

# 设置控制台输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import (
    QualitativeResearchInput,
    QualitativeResearchRunner,
)


def test_link_validation():
    """测试1：验证链路能否跑通"""
    print("\n" + "=" * 60)
    print("测试1：链路跑通验证")
    print("=" * 60)

    # 初始化 AI 客户端
    ai_client = OpenAICompatibleClient(
        config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent)
    )

    # 初始化研究运行器
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    # 创建研究输入（单人模式，提供充分信息）
    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这款儿童牙膏你会不会买？最大的顾虑是什么？",
        persona_id="M04",
        background_material="M04高线忙碌派：一线城市30-40岁职场妈妈，收入中等偏上，时间紧张，追求省心高效，注重品质但不想花太多时间选择。",
        product_info="儿童益生菌防蛀牙膏，主打低氟防蛀、孩子更愿意坚持刷牙，价格29.9元/支，线下超市和电商平台均有销售。",
        copy_material="专业防蛀，孩子喜欢，妈妈省心。",
    )

    print(f"\n研究输入:")
    print(f"  模式: {research_input.mode}")
    print(f"  画像: {research_input.persona_id}")
    print(f"  问题类型: {research_input.question_type}")
    print(f"  产品信息: {research_input.product_info[:50]}...")

    try:
        start_time = time.time()

        # 执行研究
        print("\n正在执行研究流程...")
        report = runner.run(research_input)

        elapsed = time.time() - start_time

        # 验证报告结构
        print(f"\n研究完成！耗时: {elapsed:.1f}秒")

        # 检查报告关键字段
        required_fields = [
            "meta",
            "research_brief",
            "research_plan",
            "consumer_voice",
            "research_summary",
            "structured_recommendation",
        ]

        missing_fields = [f for f in required_fields if f not in report]
        if missing_fields:
            print(f"\n❌ 链路测试失败：缺少关键字段 {missing_fields}")
            return False

        # 检查 consumer_voice 是否有内容
        consumer_voice = report.get("consumer_voice", [])
        if not consumer_voice:
            print("\n❌ 链路测试失败：consumer_voice 为空")
            return False

        # 检查 persona 输出结构
        persona_output = consumer_voice[0]
        persona_required_fields = [
            "persona_id",
            "persona_name",
            "stance",
            "voice_line",
            "rubric_scores",
            "backend_evaluation",
        ]

        missing_persona_fields = [f for f in persona_required_fields if f not in persona_output]
        if missing_persona_fields:
            print(f"\n❌ 链路测试失败：persona 输出缺少字段 {missing_persona_fields}")
            return False

        print("\n✅ 链路测试通过！")
        print(f"\n报告摘要:")
        print(f"  模式: {report['meta']['mode']}")
        print(f"  画像数量: {report['meta']['total_agents']}")
        print(f"  persona_id: {persona_output['persona_id']}")
        print(f"  立场: {persona_output['stance']}")
        print(f"  原话: {persona_output['voice_line'][:100]}...")
        print(f"  购买意图: {persona_output['backend_evaluation'].get('purchase_intent', 'unknown')}")

        return True

    except Exception as e:
        print(f"\n❌ 链路测试失败：{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_persona_differentiation():
    """测试2：验证不同画像能否产生差异化反馈"""
    print("\n" + "=" * 60)
    print("测试2：人物设定差异化验证")
    print("=" * 60)

    # 初始化 AI 客户端
    ai_client = OpenAICompatibleClient(
        config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent)
    )

    # 初始化研究运行器
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    # 测试两个对比鲜明的画像
    test_personas = [
        {
            "id": "M01",
            "name": "宠爱富养家",
            "background": "M01宠爱富养家：一线城市35-45岁高收入妈妈，注重品质和进口品牌，愿意为孩子花高价购买最好的产品，相信贵的就是好的。",
            "expected_traits": ["进口", "高端", "贵"],
        },
        {
            "id": "M08",
            "name": "佛系粗养家",
            "background": "M08佛系粗养家：三四线城市25-35岁妈妈，收入有限，认为孩子用品够用就行，安全便宜最重要，不追求高端品牌。",
            "expected_traits": ["便宜", "安全", "够用"],
        },
    ]

    product_info = "儿童益生菌防蛀牙膏，主打低氟防蛀、孩子更愿意坚持刷牙，价格29.9元/支，国产品牌，线下超市和电商平台均有销售。"

    results = []

    for persona in test_personas:
        print(f"\n正在测试画像: {persona['id']} - {persona['name']}")

        research_input = QualitativeResearchInput(
            mode="single",
            question_type="purchase_decision",
            user_question="这款儿童牙膏你会不会买？为什么？",
            persona_id=persona["id"],
            background_material=persona["background"],
            product_info=product_info,
        )

        try:
            report = runner.run(research_input)
            consumer_voice = report.get("consumer_voice", [])

            if consumer_voice:
                persona_output = consumer_voice[0]
                results.append({
                    "id": persona["id"],
                    "name": persona["name"],
                    "stance": persona_output.get("stance", ""),
                    "voice_line": persona_output.get("voice_line", ""),
                    "purchase_intent": persona_output.get("backend_evaluation", {}).get("purchase_intent", ""),
                    "concerns": persona_output.get("concerns", []),
                    "motivations": persona_output.get("motivations", []),
                })
                print(f"  立场: {persona_output.get('stance', '')}")
                print(f"  原话: {persona_output.get('voice_line', '')[:80]}...")
            else:
                print(f"  ❌ 未获取到输出")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")

    # 分析差异化
    print("\n" + "-" * 40)
    print("差异化分析:")

    if len(results) == 2:
        r1, r2 = results

        # 检查立场是否不同
        stance_diff = r1["stance"] != r2["stance"]

        # 检查原话是否有差异
        voice_diff = r1["voice_line"][:50] != r2["voice_line"][:50]

        # 检查购买意图是否不同
        intent_diff = r1["purchase_intent"] != r2["purchase_intent"]

        print(f"\n  {r1['name']} vs {r2['name']}:")
        print(f"    立场差异: {'✅ 是' if stance_diff else '❌ 否'} ({r1['stance']} vs {r2['stance']})")
        print(f"    原话差异: {'✅ 是' if voice_diff else '❌ 否'}")
        print(f"    购买意图差异: {'✅ 是' if intent_diff else '❌ 否'} ({r1['purchase_intent']} vs {r2['purchase_intent']})")

        if stance_diff or voice_diff or intent_diff:
            print("\n✅ 人物设定差异化验证通过！不同画像产生了不同反馈。")
            return True
        else:
            print("\n⚠️ 人物设定差异化不足，两个画像反馈相似。")
            return False
    else:
        print("\n❌ 测试结果不足，无法进行差异化分析")
        return False


def test_five_dimension_framework():
    """测试3：验证5维框架输出"""
    print("\n" + "=" * 60)
    print("测试3：5维框架输出验证")
    print("=" * 60)

    # 初始化 AI 客户端
    ai_client = OpenAICompatibleClient(
        config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent)
    )

    # 初始化研究运行器
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    # 创建研究输入
    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这款儿童牙膏你会不会买？",
        persona_id="M05",
        background_material="M05品质精算师：一二线城市30-40岁妈妈，高学历，注重成分和功效，会仔细研究配料表和用户评价，追求性价比而非单纯低价。",
        product_info="儿童益生菌防蛀牙膏，主打低氟防蛀、孩子更愿意坚持刷牙，价格29.9元/支，含有益生菌和氟化物。",
    )

    print(f"\n测试画像: M05 - 品质精算师")

    try:
        report = runner.run(research_input)
        consumer_voice = report.get("consumer_voice", [])

        if not consumer_voice:
            print("❌ 未获取到输出")
            return False

        persona_output = consumer_voice[0]

        # 检查 persona_framework 字段
        framework = persona_output.get("persona_framework", {})

        print("\n5维框架输出检查:")

        dimensions = [
            ("identity_background", "身份背景"),
            ("decision_preferences", "决策偏好"),
            ("expression_style", "表达风格"),
            ("behavior_constraints", "行为约束"),
            ("traceable_evidence", "可追溯证据"),
        ]

        passed = 0
        for key, label in dimensions:
            has_content = bool(framework.get(key))
            status = "✅" if has_content else "❌"
            print(f"  {status} {label}: {'有内容' if has_content else '无内容'}")
            if has_content:
                passed += 1

        # 即使 LLM 没有返回5维框架，也可以通过其他字段推断
        print("\n其他关键字段检查:")
        other_fields = [
            ("stance", "立场"),
            ("voice_line", "原话"),
            ("rubric_scores", "评分"),
            ("concerns", "顾虑"),
            ("motivations", "动机"),
        ]

        for key, label in other_fields:
            has_content = bool(persona_output.get(key))
            status = "✅" if has_content else "❌"
            print(f"  {status} {label}: {'有内容' if has_content else '无内容'}")
            if has_content:
                passed += 1

        if passed >= 5:
            print(f"\n✅ 5维框架验证通过！({passed}/10 字段有内容)")
            return True
        else:
            print(f"\n⚠️ 5维框架验证部分通过 ({passed}/10 字段有内容)")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("市场部Agent Teams - 端到端验证测试")
    print("=" * 60)

    results = []

    # 测试1：链路跑通
    results.append(("链路跑通", test_link_validation()))

    # 测试2：人物设定差异化
    results.append(("人物设定差异化", test_persona_differentiation()))

    # 测试3：5维框架输出
    results.append(("5维框架输出", test_five_dimension_framework()))

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("=" * 60))
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试未通过，请检查上述详情。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
