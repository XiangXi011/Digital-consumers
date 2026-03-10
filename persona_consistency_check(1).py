#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persona 一致性检查器 - 确保角色"守住母群边界"

检查原则:
1. 佛系粗养家 → 不能变成成分党
2. 小镇贵妇妈 → 不能大面积跑成高线极理性派
3. 高线忙碌派 → 不能个个都像全能优等家

计算每个角色的"母群一致性分数"
"""

import json
from typing import Dict, List, Any
from collections import Counter, defaultdict
from dataclasses import dataclass
import sys
sys.path.insert(0, '/Users/xiangdong/.openclaw/workspace/reports')

from digital_consumer_agents import load_agents_from_json


@dataclass
class SegmentDefinition:
    """母群定义 - 定义每个母群应有的特征"""
    name: str
    expected_decision_modes: List[str]
    expected_core_needs: List[str]
    forbidden_traits: List[str]
    price_sensitivity_range: tuple  # (min, max)
    openness_range: tuple


# 8大母群的定义
SEGMENT_DEFINITIONS = {
    '宠爱富养家': SegmentDefinition(
        name='宠爱富养家',
        expected_decision_modes=['权威依赖', '体验驱动'],
        expected_core_needs=['成分安全', '颜值包装', '孩子喜欢'],
        forbidden_traits=['价格敏感', '极简主义'],
        price_sensitivity_range=(0, 0.4),
        openness_range=(0.5, 1.0)
    ),
    '全能优等家': SegmentDefinition(
        name='全能优等家',
        expected_decision_modes=['自我主导', '权威依赖'],
        expected_core_needs=['成分安全', '功能全面', '长期健康'],
        forbidden_traits=['随意决策', '跟风购买'],
        price_sensitivity_range=(0.2, 0.6),
        openness_range=(0.4, 0.8)
    ),
    '高线忙碌派': SegmentDefinition(
        name='高线忙碌派',
        expected_decision_modes=['权威依赖', '社交跟随'],
        expected_core_needs=['省时省力', '口碑推荐', '一站式解决'],
        forbidden_traits=['深度研究', '比价行为'],
        price_sensitivity_range=(0.3, 0.7),
        openness_range=(0.3, 0.7)
    ),
    '小镇贵妇妈': SegmentDefinition(
        name='小镇贵妇妈',
        expected_decision_modes=['社交跟随', '权威依赖'],
        expected_core_needs=['面子消费', '品质感', '社交货币'],
        forbidden_traits=['极理性分析', '成分党'],
        price_sensitivity_range=(0.2, 0.5),
        openness_range=(0.4, 0.8)
    ),
    '传统关爱妈': SegmentDefinition(
        name='传统关爱妈',
        expected_decision_modes=['权威依赖', '传统保守'],
        expected_core_needs=['老牌子', '医生推荐', '安全可靠'],
        forbidden_traits=['追新潮', '网红推荐'],
        price_sensitivity_range=(0.4, 0.8),
        openness_range=(0, 0.4)
    ),
    '性价比精算师': SegmentDefinition(
        name='性价比精算师',
        expected_decision_modes=['价格敏感', '自我主导'],
        expected_core_needs=['性价比', '大容量', '促销优惠'],
        forbidden_traits=['冲动消费', '品牌溢价'],
        price_sensitivity_range=(0.7, 1.0),
        openness_range=(0.2, 0.6)
    ),
    '佛系粗养家': SegmentDefinition(
        name='佛系粗养家',
        expected_decision_modes=['随意决策', '极简主义'],
        expected_core_needs=['简单方便', '便宜够用', '不讲究'],
        forbidden_traits=['成分党', '过度保护'],
        price_sensitivity_range=(0.5, 0.9),
        openness_range=(0, 0.5)
    ),
    '自在成长家': SegmentDefinition(
        name='自在成长家',
        expected_decision_modes=['自我主导', '体验驱动'],
        expected_core_needs=['自然成长', '快乐童年', '亲子体验'],
        forbidden_traits=['焦虑驱动', '过度干预'],
        price_sensitivity_range=(0.3, 0.7),
        openness_range=(0.5, 1.0)
    )
}


class PersonaConsistencyChecker:
    """角色一致性检查器"""
    
    def __init__(self):
        self.segment_defs = SEGMENT_DEFINITIONS
    
    def check_agent(self, agent) -> Dict:
        """
        检查单个角色的一致性
        
        返回:
            {
                'consistency_score': 0-1,
                'violations': [...],
                'matches': [...],
                'details': {...}
            }
        """
        segment_name = agent.segment_name
        segment_def = self.segment_defs.get(segment_name)
        
        if not segment_def:
            return {
                'consistency_score': 0.5,
                'violations': ['未找到母群定义'],
                'matches': [],
                'details': {}
            }
        
        violations = []
        matches = []
        scores = {}
        
        # 1. 检查决策模式
        decision_mode = agent.mindset_profile.get('decision_mode', '')
        if decision_mode in segment_def.expected_decision_modes:
            matches.append(f"决策模式'{decision_mode}'符合母群特征")
            scores['decision_mode'] = 1.0
        else:
            violations.append(f"决策模式'{decision_mode}'偏离母群预期{segment_def.expected_decision_modes}")
            scores['decision_mode'] = 0.3
        
        # 2. 检查核心需求
        core_needs = agent.consumption_profile.get('core_needs', [])
        need_matches = sum(1 for need in core_needs if any(exp in need for exp in segment_def.expected_core_needs))
        need_score = need_matches / max(len(core_needs), 1)
        
        if need_score >= 0.5:
            matches.append(f"核心需求匹配度{need_score:.0%}")
        else:
            violations.append(f"核心需求匹配度仅{need_score:.0%}，预期关注{segment_def.expected_core_needs}")
        scores['core_needs'] = need_score
        
        # 3. 检查禁止特征
        trust_trigger = agent.consumption_profile.get('trust_trigger', '')
        rejection_trigger = agent.consumption_profile.get('rejection_trigger', '')
        
        for forbidden in segment_def.forbidden_traits:
            if forbidden in trust_trigger or forbidden in rejection_trigger:
                violations.append(f"出现禁止特征'{forbidden}'")
                scores['forbidden_traits'] = 0.5
            else:
                scores['forbidden_traits'] = 1.0
        
        # 4. 检查价格敏感度
        price_sens = agent.mindset_profile.get('price_sensitivity', 'medium')
        price_sens_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8}
        price_sens_value = price_sens_map.get(price_sens, 0.5)
        
        min_sens, max_sens = segment_def.price_sensitivity_range
        if min_sens <= price_sens_value <= max_sens:
            matches.append(f"价格敏感度'{price_sens}'在预期范围内")
            scores['price_sensitivity'] = 1.0
        else:
            violations.append(f"价格敏感度'{price_sens}'({price_sens_value})超出预期范围{segment_def.price_sensitivity_range}")
            scores['price_sensitivity'] = 0.5
        
        # 5. 检查开放程度
        openness = agent.mindset_profile.get('openness_level', 'medium')
        openness_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8}
        openness_value = openness_map.get(openness, 0.5)
        
        min_open, max_open = segment_def.openness_range
        if min_open <= openness_value <= max_open:
            matches.append(f"开放程度'{openness}'符合母群特征")
            scores['openness'] = 1.0
        else:
            violations.append(f"开放程度'{openness}'({openness_value})偏离预期范围{segment_def.openness_range}")
            scores['openness'] = 0.5
        
        # 计算综合一致性分数
        weights = {
            'decision_mode': 0.25,
            'core_needs': 0.25,
            'forbidden_traits': 0.2,
            'price_sensitivity': 0.15,
            'openness': 0.15
        }
        
        consistency_score = sum(scores.get(k, 0) * w for k, w in weights.items())
        
        return {
            'consistency_score': round(consistency_score, 2),
            'violations': violations,
            'matches': matches,
            'details': {
                'segment': segment_name,
                'decision_mode': decision_mode,
                'core_needs': core_needs,
                'price_sensitivity': price_sens,
                'openness': openness,
                'dimension_scores': scores
            }
        }
    
    def check_all_agents(self, agents: List) -> Dict:
        """检查所有角色的一致性"""
        results = []
        segment_scores = defaultdict(list)
        
        for agent in agents:
            check_result = self.check_agent(agent)
            check_result['agent_id'] = agent.sample_id
            check_result['agent_name'] = agent.basic_profile.get('nickname')
            results.append(check_result)
            
            segment_scores[agent.segment_name].append(check_result['consistency_score'])
        
        # 计算母群级别的统计
        segment_stats = {}
        for segment, scores in segment_scores.items():
            segment_stats[segment] = {
                'agent_count': len(scores),
                'avg_consistency': round(sum(scores) / len(scores), 2),
                'min_consistency': min(scores),
                'max_consistency': max(scores),
                'std': round((sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores))**0.5, 2)
            }
        
        # 识别异常角色
        anomalies = [r for r in results if r['consistency_score'] < 0.6]
        
        return {
            'overall_stats': {
                'total_checked': len(agents),
                'avg_consistency': round(sum(r['consistency_score'] for r in results) / len(results), 2),
                'consistency_above_80': sum(1 for r in results if r['consistency_score'] >= 0.8),
                'consistency_below_60': len(anomalies),
                'anomaly_rate': f"{len(anomalies)/len(results):.1%}"
            },
            'segment_stats': segment_stats,
            'anomalies': anomalies[:10],  # 只显示前10个
            'all_results': results
        }
    
    def generate_report(self, check_results: Dict) -> str:
        """生成可读报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("🎭 Persona 一致性检查报告")
        lines.append("=" * 70)
        
        stats = check_results['overall_stats']
        lines.append(f"\n检查样本: {stats['total_checked']} 个角色")
        lines.append(f"平均一致性: {stats['avg_consistency']:.0%}")
        lines.append(f"高一致性(≥80%): {stats['consistency_above_80']} 个")
        lines.append(f"异常角色(<60%): {stats['consistency_below_60']} 个")
        lines.append(f"异常率: {stats['anomaly_rate']}")
        
        lines.append("\n" + "-" * 70)
        lines.append("各母群一致性统计:")
        lines.append("-" * 70)
        
        for segment, seg_stats in sorted(check_results['segment_stats'].items(), 
                                          key=lambda x: x[1]['avg_consistency'], reverse=True):
            status = "✅" if seg_stats['avg_consistency'] >= 0.8 else "⚠️" if seg_stats['avg_consistency'] >= 0.6 else "❌"
            lines.append(f"\n{status} {segment}")
            lines.append(f"   样本数: {seg_stats['agent_count']}")
            lines.append(f"   平均一致性: {seg_stats['avg_consistency']:.0%}")
            lines.append(f"   一致性范围: {seg_stats['min_consistency']:.0%} - {seg_stats['max_consistency']:.0%}")
            lines.append(f"   标准差: {seg_stats['std']}")
        
        if check_results['anomalies']:
            lines.append("\n" + "-" * 70)
            lines.append("⚠️ 异常角色示例 (一致性<60%):")
            lines.append("-" * 70)
            
            for anomaly in check_results['anomalies'][:5]:
                lines.append(f"\n{anomaly['agent_name']} ({anomaly['details']['segment']})")
                lines.append(f"   一致性: {anomaly['consistency_score']:.0%}")
                lines.append(f"   问题:")
                for v in anomaly['violations'][:3]:
                    lines.append(f"      • {v}")
        
        return "\n".join(lines)


# 演示
if __name__ == "__main__":
    print("=" * 70)
    print("Persona 一致性检查")
    print("=" * 70)
    
    # 加载数据
    agents = load_agents_from_json("persona_samples_complete.json")
    print(f"\n加载完成: {len(agents)} 个角色")
    
    # 执行检查
    checker = PersonaConsistencyChecker()
    results = checker.check_all_agents(agents)
    
    # 打印报告
    report = checker.generate_report(results)
    print(report)
    
    # 保存详细结果
    output_file = "consistency_check_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n📁 详细报告已保存: {output_file}")
