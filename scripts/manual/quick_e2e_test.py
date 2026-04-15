#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速端到端测试"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner

def main():
    print("=" * 50)
    print("快速端到端测试")
    print("=" * 50)

    # 初始化
    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    # 测试输入 - 提供完整信息
    research_input = QualitativeResearchInput(
        mode="single",
        question_type="purchase_decision",
        user_question="这款儿童牙膏你会不会买？为什么？",
        persona_id="M04",
        background_material="""M04高线忙碌派画像：
- 一线城市30-40岁职场妈妈，本科学历，月收入15000-25000元
- 时间紧张，追求省心高效，相信专业背书
- 月度儿童用品预算500-1000元，更看重便利性和品质
- 目前使用云南白药儿童牙膏，对现有产品基本满意但愿意尝试新品
- 对儿童牙膏核心关注：防蛀效果、安全性、品牌可信度、使用便利性
- 不喜欢花哨包装和过度营销，偏好专业简洁的产品""",
        product_info="""儿童益生菌防蛀牙膏产品信息：
- 价格：29.9元/支（100g），属于中端价位
- 核心卖点：低氟防蛀+益生菌护龈，双重保护
- 主要成分：氟化钠（0.05%）、益生菌、木糖醇
- 安全认证：国家口腔护理产品质量认证，符合GB/T 8372标准
- 适用年龄：3-12岁儿童
- 销售渠道：天猫、京东、线下母婴店
- 竞品对比：价格低于舒适达儿童牙膏（45元），高于云南白药儿童牙膏（19.9元）
- 用户评价：新品牌，目前评价较少，整体好评率92%""",
        copy_material="专业防蛀，益生菌护龈，孩子喜欢，妈妈省心。",
    )

    print("\n研究输入:")
    print(f"  模式: {research_input.mode}")
    print(f"  画像: {research_input.persona_id}")
    print(f"  产品: {research_input.product_info}")

    print("\n开始执行...")
    try:
        report = runner.run(research_input)

        print("\n[SUCCESS] 链路测试通过!")

        consumer_voice = report.get("consumer_voice", [])
        if consumer_voice:
            persona = consumer_voice[0]
            print(f"\nPersona输出:")
            print(f"  persona_id: {persona.get('persona_id')}")
            print(f"  persona_name: {persona.get('persona_name')}")
            print(f"  stance: {persona.get('stance')}")
            print(f"  voice_line: {persona.get('voice_line', '')[:150]}")

            backend_eval = persona.get("backend_evaluation", {})
            print(f"\n后端评分:")
            print(f"  purchase_intent: {backend_eval.get('purchase_intent')}")
            print(f"  purchase_score: {backend_eval.get('purchase_score')}")

            rubric_scores = persona.get("rubric_scores", {})
            print(f"\n评分维度:")
            for dim, score in rubric_scores.items():
                print(f"  {dim}: {score}")

        return True
    except Exception as e:
        print(f"\n[FAILED] 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
