#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""舒客变色牙膏产品测试 - 使用真实数据"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner

# ============ 真实产品数据（来源：淘宝/天猫/慢慢买/新闻报道） ============
PRODUCT_INFO = """舒客宝贝魔法变色儿童牙膏产品信息：
【基本信息】
- 品牌：舒客宝贝（薇美姿集团旗下，成立于2014年，国产专业儿童口腔护理品牌）
- 产品名：羟基磷灰石抗糖色修健白含氟防蛀儿童牙膏（魔法变色款）
- 规格：60g/支
- 适用年龄：2-12岁儿童
- 香型：莓莓酸奶香型（清甜温和不刺激）
- 膏体颜色：粉色膏体，刷牙2分钟后变成浅蓝色泡泡

【价格信息】（来源：天猫旗舰店+慢慢买）
- 天猫标价：53.5元/支
- 活动价：约30.72-34.72元（立减12元+立减4.95元+9.5折）
- 历史最低：30.72元（慢慢买2026-03-19记录）

【核心卖点】（来源：商品详情页+新闻报道）
1、魔法变色：刷牙2分钟，粉色膏体变浅蓝泡泡，可视化清洁体验
2、四效防蛀体系：乳酸钙+酪蛋白磷酸肽(CPPs)+氟化钠+羟基磷灰石
3、12小时长效抗糖酸防蛀
4、温和清洁：软性磨料水合硅石，减少牙釉质磨损

【详细成分】（来源：新闻报道）
- 氟化钠：强化牙釉质，提高耐酸力
- 羟基磷灰石(HAP)：修复牙釉质微裂纹
- 酪蛋白磷酸肽(CPPs)：促进钙磷吸收
- 乳酸钙：强健牙齿
- 水合硅石：软性磨料，轻柔清洁
- 变色粒子：食用级色素，安全无害

【安全认证】（来源：新闻报道）
- 经过超20项安全测试，各项指标均符合标准
- 温和低刺激，适合儿童娇嫩口腔
- 0添加酒精、0添加色素、0添加SLS发泡剂

【用户评价】（来源：天猫）
- 店铺评分：物流4.9、服务4.9、商品描述4.9（满分5分）
- 用户反馈："包装挺好的，物品没有损坏，质量还行，宝宝说不变色"

【竞品参考】
- 舒客宝贝抗糖盾含氟儿童牙膏：9.9元
- 舒客宝贝小护盾（6-9岁）：试用装0.9元
- 舒客成人修护牙膏：标价39.9元，活动价18.9元"""

QUESTION = """这款会变色的儿童牙膏你会不会想给孩子试试？
1、你最被打动的点是什么？是魔法变色、含氟防蛀、羟基磷灰石修护还是抗糖护齿？
2、你最大的顾虑是什么？
3、你觉得53.5元（活动价约35元）的价格怎么样？
"""

# ============ 3个代表性画像 ============
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
- 一二线城市30-40岁高学历妈妈，注重成分和数据
- 会仔细研究配料表和用户评价
- 追求性价比而非单纯低价
- 看成分表、比数据、讲逻辑
- 孩子6岁，刷牙还算配合，但会偷懒""",
    },
]


def run_test(persona):
    """运行单个画像测试"""
    print(f"\n{'='*60}")
    print(f"测试画像：{persona['id']} - {persona['name']}")
    print(f"{'='*60}")

    ai_client = OpenAICompatibleClient(config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent))
    persona_path = Path(__file__).resolve().parent / "persona_samples_complete.json"
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

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
            print(f"\n[SUCCESS]")
            print(f"  persona_id: {p.get('persona_id')}")
            print(f"  persona_name: {p.get('persona_name')}")
            print(f"  stance: {p.get('stance')}")
            print(f"  purchase_intent: {p.get('backend_evaluation', {}).get('purchase_intent')}")
            print(f"  purchase_score: {p.get('backend_evaluation', {}).get('purchase_score')}")
            print(f"\n  原话：\n  {p.get('voice_line', '')}")
            return p
        else:
            print("\n[FAILED] 未获取到输出")
            return None
    except Exception as e:
        print(f"\n[FAILED] {type(e).__name__}: {e}")
        return None


def main():
    print("=" * 60)
    print("舒客变色牙膏产品测试（使用真实淘宝数据）")
    print("=" * 60)
    print("\n数据来源：")
    print("- 淘宝/天猫：舒客宝贝官方旗舰店")
    print("- 慢慢买比价网：历史价格记录")
    print("- 淘宝百科：成分和品牌介绍")

    results = []
    for persona in TEST_PERSONAS:
        result = run_test(persona)
        if result:
            results.append({"persona": persona, "output": result})

    # 汇总分析
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for r in results:
        persona = r["persona"]
        output = r["output"]
        print(f"\n【{persona['name']} ({persona['id']})】")
        print(f"  购买意图：{output.get('backend_evaluation', {}).get('purchase_intent')}")
        print(f"  购买分数：{output.get('backend_evaluation', {}).get('purchase_score')}")
        print(f"  立场：{output.get('stance')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
