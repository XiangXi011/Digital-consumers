#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舒客变色牙膏购买决策测试（简化版）
"""

import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


PRODUCT_INFO = """舒客宝贝变色儿童牙膏产品信息：
- 品牌：舒客宝贝（国产专业儿童口腔护理品牌）
- 产品名：羟基磷灰石抗糖色修健白含氟防蛀儿童牙膏
- 价格：39.9元/支（100g），属于中高端价位
- 核心卖点：
  1、魔法变色，引导孩子主动刷牙（刷牙过程中牙膏颜色会从蓝色变成粉色）
  2、含氟 + 羟基磷灰石，双重防蛀修护牙釉质
  3、抗糖护齿，温和健白不刺激
- 安全认证：符合国家GB/T 8372标准
- 适用年龄：3-12岁儿童
- 竞品对比：价格高于云南白药儿童牙膏（19.9元），低于舒适达儿童牙膏（59元）"""

QUESTION = """这款会变色的儿童牙膏你会不会想给孩子试试？
1、你最被打动的点是什么？
2、你最大的顾虑是什么？
3、比起普通儿童牙膏，你愿意为变色功能多花点钱吗？
"""

TEST_PERSONAS = [
    {
        "id": "M01",
        "name": "宠爱富养家",
        "background": """M01宠爱富养家：一线城市35-45岁高收入妈妈，月收入30000+元，只买贵的进口大牌，孩子4岁刷牙不太乖。""",
    },
    {
        "id": "M04",
        "name": "高线忙碌派",
        "background": """M04高线忙碌派：一线城市30-40岁职场妈妈，月收入15000-25000元，追求省心高效，孩子5岁刷牙需要监督。""",
    },
    {
        "id": "M05",
        "name": "品质精算师",
        "background": """M05品质精算师：一二线城市30-40岁高学历妈妈，注重成分和数据，孩子6岁刷牙会偷懒。""",
    },
]


def main():
    print("=" * 60)
    print("舒客变色牙膏购买决策测试")
    print("=" * 60)

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    results = []

    for persona in TEST_PERSONAS:
        print(f"\n测试画像：{persona['id']} - {persona['name']}")

        research_input = QualitativeResearchInput(
            mode="single",
            question_type="purchase_decision",
            user_question=QUESTION,
            persona_id=persona["id"],
            background_material=persona["background"],
            product_info=PRODUCT_INFO,
            copy_material="魔法变色，让娃主动刷够2分钟 | 含氟+羟基磷灰石，双重防蛀修护牙釉质 | 抗糖护齿，温和健白不伤牙",
        )

        try:
            report = runner.run(research_input)
            consumer_voice = report.get("consumer_voice", [])

            if consumer_voice:
                p = consumer_voice[0]
                result = {
                    "id": persona["id"],
                    "name": persona["name"],
                    "stance": p.get("stance", ""),
                    "voice_line": p.get("voice_line", ""),
                    "purchase_intent": p.get("backend_evaluation", {}).get("purchase_intent", ""),
                    "purchase_score": p.get("backend_evaluation", {}).get("purchase_score", 0),
                    "rubric_scores": p.get("rubric_scores", {}),
                }
                results.append(result)
                print(f"  立场: {result['stance']}")
                print(f"  购买意图: {result['purchase_intent']} ({result['purchase_score']:.2f})")
            else:
                print("  [ERROR] 未获取到输出")
        except Exception as e:
            print(f"  [ERROR] {e}")

    # 输出汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for r in results:
        print(f"\n【{r['name']}】")
        print(f"  购买意图: {r['purchase_intent']} (分数: {r['purchase_score']:.2f})")
        print(f"  立场: {r['stance']}")
        print(f"  原话: {r['voice_line'][:200]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
