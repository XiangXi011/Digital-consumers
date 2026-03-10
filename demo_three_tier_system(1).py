#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三层运行模式演示
完整展示数字消费者角色系统的三种运行模式
"""

import json
import sys
sys.path.insert(0, '/Users/xiangdong/.openclaw/workspace/reports')

from digital_consumer_agents import (
    AgentOrchestrator, Product, DigitalConsumerAgent,
    load_agents_from_json, create_sample_product
)
from datetime import datetime


def print_section(title):
    """打印章节标题"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def print_subsection(title):
    """打印子章节标题"""
    print(f"\n▶ {title}")
    print("-"*40)


def tier1_batch_evaluation(orchestrator, product):
    """
    第一层: 200个角色批量静默评估
    
    用途:
    - 快速获取200个角色的产品接受度
    - 识别人群差异和机会点
    - 为后续深入分析提供数据基础
    """
    print_section("第一层: 批量静默评估 (Tier 1: Batch Silent Evaluation)")
    print("模式: 200个角色同时评估产品，无交互，纯计算")
    print("耗时: 秒级")
    print("输出: 量化评分、决策分布、人群洞察")
    
    print_subsection("执行批量评估...")
    
    # 全量评估
    results = orchestrator.batch_evaluate(product)
    
    # 生成报告
    report = orchestrator.generate_report(results)
    
    # 展示结果
    print(f"\n📊 评估结果汇总:")
    print(f"   评估样本数: {report['summary']['total_evaluated']} 人")
    print(f"   平均产品评分: {report['summary']['avg_score']}/10")
    print(f"   平均购买意愿: {report['summary']['avg_intention']:.1%}")
    print(f"   预估转化率: {report['summary']['estimated_conversion_rate']}%")
    
    print(f"\n📈 决策分布:")
    for decision, count in sorted(report['decision_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True):
        bar = "█" * int(count / 2)
        print(f"   {decision:12s}: {count:3d}人 ({count/len(results)*100:5.1f}%) {bar}")
    
    print(f"\n🎯 人群段接受度排名:")
    sorted_segments = sorted(report['segment_analysis'].items(), 
                             key=lambda x: x[1]['avg_intention'], reverse=True)
    for i, (segment, stats) in enumerate(sorted_segments[:5], 1):
        print(f"   {i}. {segment}: 意愿 {stats['avg_intention']:.0%} | 评分 {stats['avg_score']}/10")
    
    print(f"\n💡 关键发现:")
    for finding in report['key_findings']:
        print(f"   • {finding}")
    
    # 返回结果供后续使用
    return results, report


def tier2_group_discussion(orchestrator, product, tier1_results):
    """
    第二层: 抽取代表角色进行小组讨论
    
    用途:
    - 观察角色间的观点碰撞
    - 理解购买/拒绝的深层原因
    - 识别影响决策的关键因素
    """
    print_section("第二层: 小组讨论 (Tier 2: Group Discussion)")
    print("模式: 抽取8-12个代表角色，模拟焦点小组讨论")
    print("耗时: 分钟级")
    print("输出: 观点碰撞、共识分析、情感洞察")
    
    print_subsection("选择代表角色...")
    
    # 分层抽样选择代表
    representatives = orchestrator.select_representatives(
        method="stratified", 
        count=8
    )
    
    print(f"   选中 {len(representatives)} 位讨论参与者:")
    for rid in representatives:
        agent = orchestrator.agents[rid]
        print(f"   • {agent.basic_profile.get('nickname')} ({agent.segment_name} / {agent.subtype})")
    
    print_subsection("执行小组讨论...")
    
    # 执行讨论
    discussion = orchestrator.group_discussion(
        topic="作为妈妈，你会给孩子买这款¥39.9的益生菌牙膏吗？请分享你的真实想法",
        product=product,
        participant_ids=representatives
    )
    
    print(f"\n🗣️ 讨论主题: {discussion['topic']}")
    print(f"   参与者数量: {len(discussion['participants'])} 人")
    print(f"   群体共识度: {discussion['consensus_level']:.0%}")
    
    print(f"\n💭 各方观点:")
    for opinion in discussion['opinions']:
        agent_name = opinion['agent_name']
        segment = opinion['segment']
        intention = opinion['opinion']['purchase_intention']
        decision = opinion['opinion']['decision']
        
        # 用表情符号表示态度
        emoji = "✅" if intention > 0.6 else "⚠️" if intention > 0.4 else "❌"
        
        print(f"\n   {emoji} {agent_name} ({segment})")
        print(f"      决策: {decision} | 意愿: {intention:.0%}")
        print(f"      发言: \"{opinion['response']}\"")
    
    print(f"\n📋 讨论洞察:")
    for insight in discussion['key_insights']:
        print(f"   • {insight}")
    
    return discussion


def tier3_deep_interview(orchestrator, product, tier1_results, tier2_discussion):
    """
    第三层: 对少量关键角色做深度追问
    
    用途:
    - 深入理解典型用户的决策逻辑
    - 挖掘潜在需求和痛点
    - 获取产品优化建议
    """
    print_section("第三层: 深度追问 (Tier 3: Deep Interview)")
    print("模式: 选择2-3个关键角色，进行结构化深度访谈")
    print("耗时: 角色数 × 5-10分钟")
    print("输出: 深度洞察、动机分析、改进建议")
    
    print_subsection("选择关键角色...")
    
    # 选择策略: 一个高意愿、一个低意愿、一个中间派
    sorted_by_intention = sorted(tier1_results, key=lambda x: x['purchase_intention'], reverse=True)
    
    key_agents = [
        (sorted_by_intention[0]['agent_id'], "高意愿代表"),
        (sorted_by_intention[len(sorted_by_intention)//2]['agent_id'], "犹豫观望代表"),
        (sorted_by_intention[-1]['agent_id'], "明确拒绝代表")
    ]
    
    print(f"   选择3位关键角色进行深度访谈:")
    for agent_id, role_type in key_agents:
        agent = orchestrator.agents[agent_id]
        print(f"   • {agent.basic_profile.get('nickname')} - {role_type}")
    
    # 深度访谈问题设计
    interview_questions = [
        "描述一下你平时给孩子选购牙膏的完整过程",
        "这款产品的哪些特点最吸引你？哪些让你犹豫？",
        "如果让你给这款产品提一个改进建议，你会说什么？",
        "什么情况下你会向朋友推荐这款产品？",
        "你觉得这款产品和市场上其他儿童牙膏相比，最大的不同是什么？"
    ]
    
    print_subsection("执行深度访谈...")
    
    all_interviews = []
    for agent_id, role_type in key_agents:
        agent = orchestrator.agents[agent_id]
        
        print(f"\n👤 访谈对象: {agent.basic_profile.get('nickname')} ({role_type})")
        print(f"   人群段: {agent.segment_name}")
        print(f"   决策模式: {agent.mindset_profile.get('decision_mode')}")
        print(f"   核心需求: {', '.join(agent.consumption_profile.get('core_needs', [])[:2])}")
        
        # 执行访谈
        interview = orchestrator.deep_dive(agent_id, interview_questions)
        all_interviews.append(interview)
        
        print(f"\n   访谈问答:")
        for i, resp in enumerate(interview['interview_responses'][:3], 1):
            print(f"\n   Q{i}: {resp['question']}")
            print(f"   A: {resp['answer']}")
            print(f"      └─ 动机: {resp['underlying_motivation']}")
            print(f"      └─ 情感: {resp['emotional_trigger']}")
    
    return all_interviews


def generate_final_report(tier1_results, tier1_report, tier2_discussion, tier3_interviews, product):
    """
    生成最终综合报告
    """
    print_section("最终综合报告")
    
    report = {
        "report_meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "product_tested": product.name,
            "total_agents": 200,
            "tiers_executed": ["batch_evaluation", "group_discussion", "deep_interview"]
        },
        "executive_summary": {
            "overall_acceptance": f"{tier1_report['summary']['avg_intention']:.0%}",
            "estimated_conversion": f"{tier1_report['summary']['estimated_conversion_rate']}%",
            "key_opportunity_segments": [
                seg for seg, stats in sorted(tier1_report['segment_analysis'].items(), 
                                            key=lambda x: x[1]['avg_intention'], reverse=True)[:2]
            ],
            "main_barriers": tier2_discussion['key_insights']
        },
        "tier1_batch_results": {
            "sample_size": len(tier1_results),
            "avg_score": tier1_report['summary']['avg_score'],
            "decision_distribution": tier1_report['decision_distribution'],
            "segment_analysis": tier1_report['segment_analysis']
        },
        "tier2_discussion_summary": {
            "participants": len(tier2_discussion['participants']),
            "consensus_level": f"{tier2_discussion['consensus_level']:.0%}",
            "key_insights": tier2_discussion['key_insights']
        },
        "tier3_deep_insights": {
            "interviews_conducted": len(tier3_interviews),
            "representative_quotes": [
                interview['interview_responses'][0]['answer'] 
                for interview in tier3_interviews
            ]
        },
        "recommendations": generate_recommendations(tier1_report, tier2_discussion)
    }
    
    print("\n📋 执行摘要:")
    print(f"   产品: {report['executive_summary']['key_opportunity_segments']}")
    print(f"   整体接受度: {report['executive_summary']['overall_acceptance']}")
    print(f"   预估转化率: {report['executive_summary']['estimated_conversion']}")
    
    print("\n🎯 核心机会人群:")
    for seg in report['executive_summary']['key_opportunity_segments']:
        print(f"   • {seg}")
    
    print("\n⚠️ 主要障碍:")
    for barrier in report['executive_summary']['main_barriers']:
        print(f"   • {barrier}")
    
    print("\n💡 策略建议:")
    for rec in report['recommendations']:
        print(f"   • {rec}")
    
    # 保存报告
    output_file = f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 完整报告已保存: {output_file}")
    
    return report


def generate_recommendations(report, discussion):
    """生成策略建议"""
    recommendations = []
    
    # 基于转化率给出建议
    conversion = float(report['summary']['estimated_conversion_rate'])
    if conversion < 10:
        recommendations.append("当前产品定位需要调整，建议重新评估目标人群")
    elif conversion < 20:
        recommendations.append("产品有一定潜力，建议优化卖点表达和价格策略")
    else:
        recommendations.append("产品接受度良好，可加大推广力度")
    
    # 基于人群差异给出建议
    segments = report['segment_analysis']
    high_segments = [s for s, st in segments.items() if st['avg_intention'] > 0.5]
    if high_segments:
        recommendations.append(f"优先 targeting 人群: {', '.join(high_segments[:2])}")
    
    # 基于讨论洞察给出建议
    if discussion['consensus_level'] < 0.5:
        recommendations.append("目标人群分歧较大，建议细分市场策略")
    
    return recommendations


def main():
    """主函数"""
    print("\n" + "🚀"*30)
    print("  数字消费者角色系统 - 三层运行演示")
    print("  200个可控数字人物库")
    print("🚀"*30)
    
    # 初始化
    print("\n📦 初始化系统...")
    agents = load_agents_from_json("persona_samples_complete.json")
    print(f"   ✓ 加载 {len(agents)} 个数字角色")
    
    orchestrator = AgentOrchestrator()
    orchestrator.load_agents([a.to_dict() for a in agents])
    print(f"   ✓ 初始化编排器")
    
    product = create_sample_product()
    print(f"   ✓ 加载测试产品: {product.name}")
    
    # 执行三层运行
    print("\n" + "▓"*60)
    print("  开始三层运行模式")
    print("▓"*60)
    
    # Tier 1
    tier1_results, tier1_report = tier1_batch_evaluation(orchestrator, product)
    
    # Tier 2
    tier2_discussion = tier2_group_discussion(orchestrator, product, tier1_results)
    
    # Tier 3
    tier3_interviews = tier3_deep_interview(orchestrator, product, tier1_results, tier2_discussion)
    
    # 生成最终报告
    final_report = generate_final_report(
        tier1_results, tier1_report, 
        tier2_discussion, tier3_interviews,
        product
    )
    
    print("\n" + "✅"*30)
    print("  演示完成!")
    print("✅"*30)


if __name__ == "__main__":
    main()
