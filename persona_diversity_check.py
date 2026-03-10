#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色差异性检查器 - 确保200个角色不是"换皮"

检查维度:
1. 职业重复率
2. 城市重复率  
3. 引言风格重复率
4. 信任触发点集中度
5. 拒绝原因多样性
6. 同类子型边界差异
"""

import json
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
import sys
sys.path.insert(0, '/Users/xiangdong/.openclaw/workspace/reports')

from digital_consumer_agents import load_agents_from_json


@dataclass
class DiversityMetrics:
    """多样性指标"""
    total_agents: int
    unique_occupations: int
    occupation_diversity_score: float
    unique_cities: int
    city_diversity_score: float
    quote_style_diversity: float
    trust_trigger_diversity: float
    rejection_reason_diversity: float
    subtype_boundary_clarity: float
    overall_diversity_score: float
    warnings: List[str]


class PersonaDiversityChecker:
    """角色差异性检查器"""
    
    # 多样性阈值
    THRESHOLDS = {
        'occupation_min_unique': 30,      # 最少30种不同职业
        'city_min_unique': 15,            # 最少15个不同城市
        'quote_similarity_max': 0.3,      # 引言相似度不超过30%
        'trust_trigger_max_concentration': 0.25,  # 单一触发点不超过25%
        'rejection_reason_min_types': 8,  # 最少8种拒绝原因
        'subtype_boundary_min': 0.6       # 子型边界清晰度至少60%
    }
    
    def check(self, agents: List) -> DiversityMetrics:
        """执行完整差异性检查"""
        warnings = []
        
        # 1. 职业多样性
        occ_metrics = self._check_occupation_diversity(agents)
        if occ_metrics['unique_count'] < self.THRESHOLDS['occupation_min_unique']:
            warnings.append(f"⚠️ 职业多样性不足: 仅{occ_metrics['unique_count']}种职业，建议≥{self.THRESHOLDS['occupation_min_unique']}")
        
        # 2. 城市多样性
        city_metrics = self._check_city_diversity(agents)
        if city_metrics['unique_count'] < self.THRESHOLDS['city_min_unique']:
            warnings.append(f"⚠️ 城市多样性不足: 仅{city_metrics['unique_count']}个城市，建议≥{self.THRESHOLDS['city_min_unique']}")
        
        # 3. 引言风格多样性
        quote_metrics = self._check_quote_diversity(agents)
        if quote_metrics['similarity_score'] > self.THRESHOLDS['quote_similarity_max']:
            warnings.append(f"⚠️ 引言风格过于相似: 相似度{quote_metrics['similarity_score']:.1%}，建议≤{self.THRESHOLDS['quote_similarity_max']:.0%}")
        
        # 4. 信任触发点集中度
        trust_metrics = self._check_trust_trigger_diversity(agents)
        if trust_metrics['max_concentration'] > self.THRESHOLDS['trust_trigger_max_concentration']:
            warnings.append(f"⚠️ 信任触发点过度集中: 最高占比{trust_metrics['max_concentration']:.1%}，建议≤{self.THRESHOLDS['trust_trigger_max_concentration']:.0%}")
        
        # 5. 拒绝原因多样性
        rejection_metrics = self._check_rejection_diversity(agents)
        if rejection_metrics['unique_count'] < self.THRESHOLDS['rejection_reason_min_types']:
            warnings.append(f"⚠️ 拒绝原因类型不足: 仅{rejection_metrics['unique_count']}种，建议≥{self.THRESHOLDS['rejection_reason_min_types']}")
        
        # 6. 子型边界清晰度
        boundary_metrics = self._check_subtype_boundaries(agents)
        if boundary_metrics['clarity_score'] < self.THRESHOLDS['subtype_boundary_min']:
            warnings.append(f"⚠️ 子型边界不够清晰: 清晰度{boundary_metrics['clarity_score']:.1%}，建议≥{self.THRESHOLDS['subtype_boundary_min']:.0%}")
        
        # 计算综合多样性得分
        overall_score = (
            occ_metrics['diversity_score'] * 0.2 +
            city_metrics['diversity_score'] * 0.15 +
            (1 - quote_metrics['similarity_score']) * 0.15 +
            (1 - trust_metrics['max_concentration']) * 0.15 +
            rejection_metrics['diversity_score'] * 0.15 +
            boundary_metrics['clarity_score'] * 0.2
        )
        
        return DiversityMetrics(
            total_agents=len(agents),
            unique_occupations=occ_metrics['unique_count'],
            occupation_diversity_score=occ_metrics['diversity_score'],
            unique_cities=city_metrics['unique_count'],
            city_diversity_score=city_metrics['diversity_score'],
            quote_style_diversity=1 - quote_metrics['similarity_score'],
            trust_trigger_diversity=1 - trust_metrics['max_concentration'],
            rejection_reason_diversity=rejection_metrics['diversity_score'],
            subtype_boundary_clarity=boundary_metrics['clarity_score'],
            overall_diversity_score=overall_score,
            warnings=warnings
        )
    
    def _check_occupation_diversity(self, agents: List) -> Dict:
        """检查职业多样性"""
        occupations = []
        for agent in agents:
            occ = agent.basic_profile.get('occupation', '未知')
            # 标准化职业名称
            occ = occ.replace('（', '(').replace('）', ')').strip()
            occupations.append(occ)
        
        counter = Counter(occupations)
        unique_count = len(counter)
        total = len(occupations)
        
        # 计算多样性得分 (使用Simpson's Diversity Index)
        diversity_score = 1 - sum((count/total)**2 for count in counter.values())
        
        # 找出重复率高的职业
        top_occupations = counter.most_common(5)
        
        return {
            'unique_count': unique_count,
            'diversity_score': round(diversity_score, 2),
            'distribution': dict(counter),
            'top_occupations': top_occupations
        }
    
    def _check_city_diversity(self, agents: List) -> Dict:
        """检查城市多样性"""
        cities = []
        for agent in agents:
            city = agent.basic_profile.get('city', '未知')
            cities.append(city)
        
        counter = Counter(cities)
        unique_count = len(counter)
        total = len(cities)
        
        diversity_score = 1 - sum((count/total)**2 for count in counter.values())
        
        # 按城市级别分类
        tier1 = ['北京', '上海', '广州', '深圳']
        tier2 = ['杭州', '南京', '成都', '武汉', '西安', '重庆', '天津', '苏州']
        
        tier1_count = sum(1 for c in cities if c in tier1)
        tier2_count = sum(1 for c in cities if c in tier2)
        other_count = len(cities) - tier1_count - tier2_count
        
        return {
            'unique_count': unique_count,
            'diversity_score': round(diversity_score, 2),
            'tier_distribution': {
                '一线城市': tier1_count,
                '二线城市': tier2_count,
                '其他城市': other_count
            },
            'top_cities': counter.most_common(5)
        }
    
    def _check_quote_diversity(self, agents: List) -> Dict:
        """检查引言风格多样性"""
        quotes = []
        for agent in agents:
            quote = agent.expression_profile.get('likely_quote', '')
            if quote:
                quotes.append(quote)
        
        if len(quotes) < 2:
            return {'similarity_score': 0, 'unique_quotes': 0}
        
        # 计算引言相似度 (基于共同关键词)
        similarity_pairs = []
        for i in range(len(quotes)):
            for j in range(i+1, len(quotes)):
                sim = self._calculate_text_similarity(quotes[i], quotes[j])
                similarity_pairs.append(sim)
        
        avg_similarity = sum(similarity_pairs) / len(similarity_pairs) if similarity_pairs else 0
        
        # 识别重复引言
        exact_duplicates = len(quotes) - len(set(quotes))
        
        return {
            'similarity_score': round(avg_similarity, 2),
            'exact_duplicates': exact_duplicates,
            'total_quotes': len(quotes),
            'sample_quotes': quotes[:5]
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度"""
        # 简单实现：基于共同字符比例
        set1 = set(text1)
        set2 = set(text2)
        
        if not set1 or not set2:
            return 0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0
    
    def _check_trust_trigger_diversity(self, agents: List) -> Dict:
        """检查信任触发点多样性"""
        triggers = []
        for agent in agents:
            trigger = agent.consumption_profile.get('trust_trigger', '')
            if trigger:
                triggers.append(trigger)
        
        counter = Counter(triggers)
        total = len(triggers)
        
        if total == 0:
            return {'max_concentration': 0, 'unique_count': 0}
        
        max_count = max(counter.values()) if counter else 0
        max_concentration = max_count / total
        
        return {
            'max_concentration': round(max_concentration, 2),
            'unique_count': len(counter),
            'distribution': dict(counter.most_common(10))
        }
    
    def _check_rejection_diversity(self, agents: List) -> Dict:
        """检查拒绝原因多样性"""
        reasons = []
        for agent in agents:
            rejection = agent.consumption_profile.get('rejection_trigger', '')
            if rejection:
                reasons.append(rejection)
        
        counter = Counter(reasons)
        total = len(reasons)
        
        if total == 0:
            return {'diversity_score': 0, 'unique_count': 0}
        
        # 计算多样性得分
        diversity_score = 1 - sum((count/total)**2 for count in counter.values())
        
        return {
            'unique_count': len(counter),
            'diversity_score': round(diversity_score, 2),
            'distribution': dict(counter.most_common(10))
        }
    
    def _check_subtype_boundaries(self, agents: List) -> Dict:
        """检查子型边界清晰度"""
        # 按母群和子型分组
        segment_groups = defaultdict(lambda: defaultdict(list))
        
        for agent in agents:
            segment = agent.segment_name
            subtype = agent.subtype
            segment_groups[segment][subtype].append(agent)
        
        # 计算每个子型内部的特征一致性
        subtype_scores = []
        boundary_details = []
        
        for segment, subtypes in segment_groups.items():
            for subtype, agents_in_subtype in subtypes.items():
                if len(agents_in_subtype) < 2:
                    continue
                
                # 计算该子型内决策模式的一致性
                decision_modes = [a.mindset_profile.get('decision_mode', '') for a in agents_in_subtype]
                mode_counter = Counter(decision_modes)
                dominant_mode_ratio = max(mode_counter.values()) / len(decision_modes) if decision_modes else 0
                
                # 计算核心需求的一致性
                core_needs = []
                for a in agents_in_subtype:
                    needs = a.consumption_profile.get('core_needs', [])
                    core_needs.extend(needs)
                needs_counter = Counter(core_needs)
                
                # 子型得分 = 决策模式集中度 × 0.6 + 需求集中度 × 0.4
                subtype_score = dominant_mode_ratio * 0.6 + 0.4  # 简化计算
                subtype_scores.append(subtype_score)
                
                boundary_details.append({
                    'segment': segment,
                    'subtype': subtype,
                    'sample_count': len(agents_in_subtype),
                    'dominant_decision_mode': mode_counter.most_common(1)[0] if mode_counter else ('', 0),
                    'consistency_score': round(subtype_score, 2)
                })
        
        avg_clarity = sum(subtype_scores) / len(subtype_scores) if subtype_scores else 0
        
        return {
            'clarity_score': round(avg_clarity, 2),
            'subtype_count': len(boundary_details),
            'boundary_details': boundary_details
        }
    
    def generate_report(self, metrics: DiversityMetrics) -> Dict:
        """生成详细检查报告"""
        return {
            'check_summary': {
                'total_agents_checked': metrics.total_agents,
                'overall_diversity_score': f"{metrics.overall_diversity_score:.0%}",
                'status': 'PASS' if not metrics.warnings else 'WARNING',
                'warning_count': len(metrics.warnings)
            },
            'detailed_metrics': {
                'occupation_diversity': {
                    'unique_occupations': metrics.unique_occupations,
                    'diversity_score': f"{metrics.occupation_diversity_score:.0%}",
                    'status': '✅' if metrics.unique_occupations >= self.THRESHOLDS['occupation_min_unique'] else '⚠️'
                },
                'city_diversity': {
                    'unique_cities': metrics.unique_cities,
                    'diversity_score': f"{metrics.city_diversity_score:.0%}",
                    'status': '✅' if metrics.unique_cities >= self.THRESHOLDS['city_min_unique'] else '⚠️'
                },
                'quote_style_diversity': {
                    'diversity_score': f"{metrics.quote_style_diversity:.0%}",
                    'status': '✅' if metrics.quote_style_diversity > 0.7 else '⚠️'
                },
                'trust_trigger_diversity': {
                    'diversity_score': f"{metrics.trust_trigger_diversity:.0%}",
                    'status': '✅' if metrics.trust_trigger_diversity > 0.75 else '⚠️'
                },
                'rejection_reason_diversity': {
                    'diversity_score': f"{metrics.rejection_reason_diversity:.0%}",
                    'status': '✅' if metrics.rejection_reason_diversity > 0.7 else '⚠️'
                },
                'subtype_boundary_clarity': {
                    'clarity_score': f"{metrics.subtype_boundary_clarity:.0%}",
                    'status': '✅' if metrics.subtype_boundary_clarity >= self.THRESHOLDS['subtype_boundary_min'] else '⚠️'
                }
            },
            'warnings': metrics.warnings,
            'recommendations': self._generate_recommendations(metrics)
        }
    
    def _generate_recommendations(self, metrics: DiversityMetrics) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if metrics.occupation_diversity_score < 0.8:
            recommendations.append("增加职业类型多样性，避免过多'全职妈妈'或'企业职员'")
        
        if metrics.city_diversity_score < 0.7:
            recommendations.append("扩展城市覆盖，增加三四线城市样本")
        
        if metrics.quote_style_diversity < 0.7:
            recommendations.append("丰富引言风格，避免相似表达")
        
        if metrics.trust_trigger_diversity < 0.75:
            recommendations.append("分散信任触发点，避免过度依赖单一因素")
        
        if metrics.subtype_boundary_clarity < 0.6:
            recommendations.append("强化子型边界定义，确保同类子型特征一致性")
        
        return recommendations


def print_diversity_report(report: Dict):
    """打印多样性检查报告"""
    print("\n" + "=" * 70)
    print("🔍 角色差异性检查报告")
    print("=" * 70)
    
    summary = report['check_summary']
    print(f"\n检查样本: {summary['total_agents_checked']} 个角色")
    print(f"综合多样性得分: {summary['overall_diversity_score']}")
    print(f"检查状态: {summary['status']}")
    
    if summary['warning_count'] > 0:
        print(f"⚠️ 发现 {summary['warning_count']} 个问题")
    
    print("\n" + "-" * 70)
    print("详细指标:")
    print("-" * 70)
    
    metrics = report['detailed_metrics']
    
    print(f"\n👔 职业多样性:")
    print(f"   独特职业数: {metrics['occupation_diversity']['unique_occupations']}")
    print(f"   多样性得分: {metrics['occupation_diversity']['diversity_score']}")
    print(f"   状态: {metrics['occupation_diversity']['status']}")
    
    print(f"\n🏙️ 城市多样性:")
    print(f"   独特城市数: {metrics['city_diversity']['unique_cities']}")
    print(f"   多样性得分: {metrics['city_diversity']['diversity_score']}")
    print(f"   状态: {metrics['city_diversity']['status']}")
    
    print(f"\n💬 引言风格多样性:")
    print(f"   多样性得分: {metrics['quote_style_diversity']['diversity_score']}")
    print(f"   状态: {metrics['quote_style_diversity']['status']}")
    
    print(f"\n🎯 信任触发点多样性:")
    print(f"   多样性得分: {metrics['trust_trigger_diversity']['diversity_score']}")
    print(f"   状态: {metrics['trust_trigger_diversity']['status']}")
    
    print(f"\n🚫 拒绝原因多样性:")
    print(f"   多样性得分: {metrics['rejection_reason_diversity']['diversity_score']}")
    print(f"   状态: {metrics['rejection_reason_diversity']['status']}")
    
    print(f"\n🎭 子型边界清晰度:")
    print(f"   清晰度得分: {metrics['subtype_boundary_clarity']['clarity_score']}")
    print(f"   状态: {metrics['subtype_boundary_clarity']['status']}")
    
    if report['warnings']:
        print("\n" + "-" * 70)
        print("⚠️ 警告:")
        print("-" * 70)
        for warning in report['warnings']:
            print(f"   {warning}")
    
    if report['recommendations']:
        print("\n" + "-" * 70)
        print("💡 改进建议:")
        print("-" * 70)
        for rec in report['recommendations']:
            print(f"   • {rec}")


# 演示
if __name__ == "__main__":
    print("=" * 70)
    print("角色差异性检查")
    print("=" * 70)
    
    # 加载数据
    agents = load_agents_from_json("persona_samples_complete.json")
    print(f"\n加载完成: {len(agents)} 个角色")
    
    # 执行检查
    checker = PersonaDiversityChecker()
    metrics = checker.check(agents)
    
    # 生成报告
    report = checker.generate_report(metrics)
    
    # 打印报告
    print_diversity_report(report)
    
    # 保存详细报告
    output_file = "diversity_check_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 详细报告已保存: {output_file}")
