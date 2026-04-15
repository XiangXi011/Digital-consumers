#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进效果验证测试

测试目标：
1. Planner门槛降低：简单输入也能启动
2. 结果透明度：评分有解释、决策有逻辑
3. 人设准确性：输出符合真实人设特征
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


# 简化的产品信息（测试Planner门槛）
SIMPLE_PRODUCT = "舒客宝贝变色牙膏，53.5元活动价35元，能变色防蛀"

# 完整的产品信息
FULL_PRODUCT = """舒客宝贝魔法变色儿童牙膏：
- 价格：53.5元/支，活动价约35元
- 核心卖点：魔法变色引导刷牙2分钟、含氟+羟基磷灰石双重防蛀
- 适用年龄：2-12岁儿童
- 安全认证：经过超20项安全测试"""


def test_planner_threshold():
    """测试1：Planner门槛降低"""
    print("\n" + "=" * 60)
    print("测试1：Planner门槛降低")
    print("=" * 60)

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    # 测试简化输入
    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这个牙膏怎么样？",  # 模糊问题
        persona_id="M04",
        background_material="",  # 空背景
        product_info=SIMPLE_PRODUCT,  # 简化产品信息
    )

    try:
        plan = runner.plan(research_input)
        if plan.get('ready_to_dispatch'):
            print("  ✅ 简化输入也能启动研究")
            print(f"  dispatch_scope: {plan.get('dispatch_scope')}")
            return True
        else:
            clarifying = plan.get('clarifying_questions', [])
            print(f"  ⚠️ 仍需澄清: {clarifying[:2]}")
            return False
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_transparency():
    """测试2：结果透明度"""
    print("\n" + "=" * 60)
    print("测试2：结果透明度（评分解释+决策逻辑）")
    print("=" * 60)

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这款变色牙膏你会买吗？为什么？",
        persona_id="M05",
        background_material="品质精算师，注重成分和数据",
        product_info=FULL_PRODUCT,
    )

    try:
        report = runner.run(research_input)
        consumer_voice = report.get("consumer_voice", [])

        if consumer_voice:
            p = consumer_voice[0]
            voice_line = p.get('voice_line', '')
            decision_logic = p.get('decision_logic', '')

            # 检查透明度
            has_reasoning = len(voice_line) > 30  # 原话有解释（降低阈值）
            has_logic = len(decision_logic) > 30  # 决策逻辑有内容
            has_scores = bool(p.get('rubric_scores'))  # 有评分

            print(f"\n  原话长度: {len(voice_line)} 字")
            print(f"  决策逻辑长度: {len(decision_logic)} 字")
            print(f"  评分: {p.get('rubric_scores')}")

            print(f"\n  原话摘录：\n  {voice_line[:200]}...")
            print(f"\n  决策逻辑：\n  {decision_logic[:200]}...")

            if has_reasoning and has_logic and has_scores:
                print("\n  ✅ 结果透明度良好")
                return True
            else:
                print("\n  ⚠️ 透明度不足")
                return False
        else:
            print("  ❌ 未获取到输出")
            return False
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_persona_accuracy():
    """测试3：人设准确性"""
    print("\n" + "=" * 60)
    print("测试3：人设准确性")
    print("=" * 60)

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    # 测试M01（宠爱富养家）
    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这款变色牙膏你会买吗？",
        persona_id="M01",
        background_material="宠爱富养家，只买进口大牌",
        product_info=FULL_PRODUCT,
    )

    try:
        report = runner.run(research_input)
        consumer_voice = report.get("consumer_voice", [])

        if consumer_voice:
            p = consumer_voice[0]
            voice_line = p.get('voice_line', '')
            stance = p.get('stance', '')

            # 检查是否符合M01人设（应该reject，因为是国产）
            mentions_import = '进口' in voice_line or '国产' in voice_line
            mentions_brand = '品牌' in voice_line or '大牌' in voice_line
            correct_stance = stance in ['hesitant', 'rejecting']

            print(f"\n  立场: {stance}")
            print(f"  提到进口/国产: {'是' if mentions_import else '否'}")
            print(f"  提到品牌: {'是' if mentions_brand else '否'}")
            print(f"\n  原话：\n  {voice_line[:200]}...")

            if correct_stance and (mentions_import or mentions_brand):
                print("\n  ✅ 人设准确性良好（M01正确反映进口偏好）")
                return True
            else:
                print("\n  ⚠️ 人设准确性不足")
                return False
        else:
            print("  ❌ 未获取到输出")
            return False
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def main():
    print("=" * 60)
    print("改进效果验证测试")
    print("=" * 60)

    results = []

    # 测试1：Planner门槛
    results.append(("Planner门槛降低", test_planner_threshold()))

    # 测试2：结果透明度
    results.append(("结果透明度", test_transparency()))

    # 测试3：人设准确性
    results.append(("人设准确性", test_persona_accuracy()))

    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")

    success_count = sum(1 for _, p in results if p)
    print(f"\n通过率: {success_count}/{len(results)}")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
