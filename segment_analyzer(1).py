#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人群段深度分析器 - 提供完整的证据链

不是简单总结"哪个人群更好"，而是提供可审计的分析维度：
1. 平均购买意愿及分布
2. 价格接受度分析
3. 卖点匹配度统计
4. 拒绝理由分析
5. 评论正向率
6. 人群内部一致性
"""

import json
from typing import Dict, List, Any
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class SegmentEvidence:
    """人群段证据数据"""
    segment_name: str
    sample_count: int
    
    # 购买意愿证据
    avg_purchase_intention: float
    intention_distribution: Dict[str, int]
    high_intention_rate: float
    
    # 价格证据
    avg_price_acceptance: float
    price_rejection_rate: float
    budget_mismatch_count: int
    
    # 卖点匹配证据
    top_matched_features: List[tuple]
    feature_match_rate: float
    
    # 拒绝证据
    rejection_reasons: Dict[str, int]
    primary_rejection_reason: str
    
    # 评分证据
    avg_overall_score: float
    score_std: float
    
    # 一致性证据
    internal_consistency: float
    decision_concentration: float


class SegmentAnalyzer:
    """人群段分析器 - 提供完整证据链"""
    
    def analyze(self, evaluations: List[Dict], segment_key: str = 'segment') -> Dict[str, SegmentEvidence]:
        """
        分析所有人群段，返回带证据链的结果
        """
        # 按人群段分组
        segment_groups = defaultdict(list)
        for ev in evaluations:
            seg = ev.get(segment_key, '未知')
            segment_groups[seg].append(ev)
        
        results = {}
        for segment_name, group in segment_groups.items():
            evidence = self._analyze_single_segment(segment_name, group)
            results[segment_name] = evidence
        
        return results
    
    def _analyze_single_segment(self, name: str, evaluations: List[Dict]) -> SegmentEvidence:
        """分析单个人群段"""
        n = len(evaluations)
        
        # 1. 购买意愿分析
        intentions = [e.get('purchase_intention', 0) for e in evaluations]
        avg_intention = sum(intentions) / n if n > 0 else 0
        
        # 意愿分布
        intention_dist = {
            '高意愿(>60%)': sum(1 for i in intentions if i > 0.6),
            '中意愿(30-60%)': sum(1 for i in intentions if 0.3 <= i <= 0.6),
            '低意愿(<30%)': sum(1 for i in intentions if i < 0.3)
        }
        high_intention_rate = intention_dist['高意愿(>60%)'] / n if n > 0 else 0
        
        # 2. 价格接受度分析
        price_accepts = [e.get('price_evaluation', 0) for e in evaluations]
        avg_price_accept = sum(price_accepts) / n if n > 0 else 0
        price_rejections = sum(1 for p in price_accepts if p < 0.5)
        
        # 3. 卖点匹配分析
        all_features = []
        for e in evaluations:
            preferred = e.get('preferred_features', [])
            all_features.extend(preferred)
        feature_counter = Counter(all_features)
        top_features = feature_counter.most_common(5)
        
        # 计算匹配率 (至少匹配1个卖点的比例)
        has_match = sum(1 for e in evaluations if len(e.get('preferred_features', [])) > 0)
        match_rate = has_match / n if n > 0 else 0
        
        # 4. 拒绝理由分析
        all_concerns = []
        for e in evaluations:
            concerns = e.get('key_concerns', [])
            all_concerns.extend(concerns)
        concern_counter = Counter(all_concerns)
        top_concern = concern_counter.most_common(1)[0][0] if concern_counter else "无明显顾虑"
        
        # 5. 评分统计
        scores = [e.get('overall_score', 0) for e in evaluations]
        avg_score = sum(scores) / n if n > 0 else 0
        score_variance = sum((s - avg_score)**2 for s in scores) / n if n > 0 else 0
        score_std = score_variance ** 0.5
        
        # 6. 内部一致性 (标准差越小越一致)
        consistency = max(0, 1 - score_std / 5)  # 归一化
        
        # 决策集中度
        decisions = [e.get('decision', '犹豫') for e in evaluations]
        decision_counter = Counter(decisions)
        max_decision_ratio = max(decision_counter.values()) / n if n > 0 else 0
        
        return SegmentEvidence(
            segment_name=name,
            sample_count=n,
            avg_purchase_intention=round(avg_intention, 2),
            intention_distribution=intention_dist,
            high_intention_rate=round(high_intention_rate, 2),
            avg_price_acceptance=round(avg_price_accept, 2),
            price_rejection_rate=round(price_rejections / n, 2) if n > 0 else 0,
            budget_mismatch_count=price_rejections,
            top_matched_features=top_features,
            feature_match_rate=round(match_rate, 2),
            rejection_reasons=dict(concern_counter.most_common(5)),
            primary_rejection_reason=top_concern,
            avg_overall_score=round(avg_score, 2),
            score_std=round(score_std, 2),
            internal_consistency=round(consistency, 2),
            decision_concentration=round(max_decision_ratio, 2)
        )
    
    def generate_audit_report(self, segment_evidence: Dict[str, SegmentEvidence], 
                             top_n: int = 3) -> Dict:
        """
        生成可审计的分析报告
        """
        # 按购买意愿排序
        sorted_segments = sorted(
            segment_evidence.items(),
            key=lambda x: x[1].avg_purchase_intention,
            reverse=True
        )
        
        report = {
            'report_type': '人群段机会分析 - 完整证据链',
            'generated_at': self._get_timestamp(),
            'total_segments': len(segment_evidence),
            'total_samples': sum(ev.sample_count for ev in segment_evidence.values()),
            'ranking_criteria': '平均购买意愿 (Average Purchase Intention)',
            'top_opportunity_segments': []
        }
        
        for i, (name, ev) in enumerate(sorted_segments[:top_n], 1):
            segment_report = {
                'rank': i,
                'segment_name': name,
                'sample_size': ev.sample_count,
                'conclusion': f"{name}是第{i}大机会人群",
                'evidence_chain': {
                    'purchase_intention': {
                        'metric': '平均购买意愿',
                        'value': f"{ev.avg_purchase_intention:.0%}",
                        'benchmark': '人群平均',
                        'interpretation': '高' if ev.avg_purchase_intention > 0.5 else '中' if ev.avg_purchase_intention > 0.3 else '低',
                        'distribution': ev.intention_distribution,
                        'high_intention_rate': f"{ev.high_intention_rate:.0%}"
                    },
                    'price_acceptance': {
                        'metric': '平均价格接受度',
                        'value': f"{ev.avg_price_acceptance:.0%}",
                        'price_rejection_rate': f"{ev.price_rejection_rate:.0%}",
                        'interpretation': '价格接受度高' if ev.avg_price_acceptance > 0.7 else '价格敏感' if ev.avg_price_acceptance < 0.5 else '价格接受度中等'
                    },
                    'feature_match': {
                        'metric': '卖点匹配率',
                        'value': f"{ev.feature_match_rate:.0%}",
                        'top_matched_features': [
                            {'feature': f[0], 'match_count': f[1]} 
                            for f in ev.top_matched_features
                        ],
                        'interpretation': f"{ev.feature_match_rate:.0%}的样本找到了匹配的卖点"
                    },
                    'rejection_analysis': {
                        'metric': '主要拒绝原因',
                        'primary_reason': ev.primary_rejection_reason,
                        'all_reasons': ev.rejection_reasons,
                        'interpretation': f"最大顾虑是{ev.primary_rejection_reason}" if ev.rejection_reasons else "无明显顾虑"
                    },
                    'internal_consistency': {
                        'metric': '内部一致性',
                        'score_std': ev.score_std,
                        'consistency_score': f"{ev.internal_consistency:.0%}",
                        'decision_concentration': f"{ev.decision_concentration:.0%}",
                        'interpretation': '高度一致' if ev.internal_consistency > 0.8 else '中度分散' if ev.internal_consistency > 0.5 else '意见分歧大'
                    }
                },
                'supporting_data': {
                    'avg_overall_score': ev.avg_overall_score,
                    'sample_quotes': self._generate_sample_quotes(ev)
                }
            }
            report['top_opportunity_segments'].append(segment_report)
        
        # 添加对比分析
        report['comparative_analysis'] = self._generate_comparison(sorted_segments[:top_n])
        
        return report
    
    def _generate_sample_quotes(self, evidence: SegmentEvidence) -> List[str]:
        """生成代表性语录"""
        quotes = []
        
        if evidence.avg_purchase_intention > 0.6:
            quotes.append(f"\"{evidence.segment_name}整体接受度高，{evidence.high_intention_rate:.0%}的成员表现出强烈购买意愿\"")
        
        if evidence.price_rejection_rate < 0.2:
            quotes.append(f"\"价格接受度良好，仅{evidence.price_rejection_rate:.0%}因价格拒绝\"")
        
        if evidence.feature_match_rate > 0.7:
            quotes.append(f"\"卖点匹配度高，{evidence.feature_match_rate:.0%}找到了感兴趣的卖点\"")
        
        return quotes
    
    def _generate_comparison(self, sorted_segments: List[tuple]) -> Dict:
        """生成人群段对比分析"""
        if len(sorted_segments) < 2:
            return {}
        
        top = sorted_segments[0][1]
        second = sorted_segments[1][1]
        
        return {
            'top_vs_second': {
                'purchase_intention_gap': f"{(top.avg_purchase_intention - second.avg_purchase_intention):.0%}",
                'price_acceptance_gap': f"{(top.avg_price_acceptance - second.avg_price_acceptance):.0%}",
                'key_difference': self._identify_key_difference(top, second)
            },
            'why_top_is_opportunity': [
                f"购买意愿领先第2名{(top.avg_purchase_intention - second.avg_purchase_intention):.0%}",
                f"{top.high_intention_rate:.0%}的成员属于高意愿群体" if top.high_intention_rate > 0.3 else "",
                f"价格接受度{top.avg_price_acceptance:.0%}，抵触较少" if top.price_rejection_rate < 0.3 else "",
                f"卖点匹配率{top.feature_match_rate:.0%}，需求契合度高" if top.feature_match_rate > 0.6 else ""
            ]
        }
    
    def _identify_key_difference(self, top: SegmentEvidence, second: SegmentEvidence) -> str:
        """识别关键差异点"""
        differences = []
        
        if abs(top.avg_purchase_intention - second.avg_purchase_intention) > 0.15:
            differences.append("购买意愿")
        if abs(top.avg_price_acceptance - second.avg_price_acceptance) > 0.15:
            differences.append("价格接受度")
        if abs(top.feature_match_rate - second.feature_match_rate) > 0.15:
            differences.append("卖点匹配度")
        
        return "、".join(differences) if differences else "综合因素"
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def print_audit_report(self, report: Dict):
        """打印可审计报告"""
        print("\n" + "=" * 70)
        print(f"📊 {report['report_type']}")
        print("=" * 70)
        print(f"生成时间: {report['generated_at']}")
        print(f"分析样本: {report['total_samples']} 个角色，{report['total_segments']} 个人群段")
        print(f"排序依据: {report['ranking_criteria']}")
        
        for seg_report in report['top_opportunity_segments']:
            print(f"\n{'='*70}")
            print(f"#{seg_report['rank']} 机会人群: {seg_report['segment_name']}")
            print(f"{'='*70}")
            print(f"样本量: {seg_report['sample_size']} 人")
            
            ev = seg_report['evidence_chain']
            
            print(f"\n📈 购买意愿证据:")
            print(f"   • 平均购买意愿: {ev['purchase_intention']['value']}")
            print(f"   • 高意愿成员占比: {ev['purchase_intention']['high_intention_rate']}")
            print(f"   • 分布: {ev['purchase_intention']['distribution']}")
            
            print(f"\n💰 价格接受度证据:")
            print(f"   • 平均价格接受度: {ev['price_acceptance']['value']}")
            print(f"   • 价格拒绝率: {ev['price_acceptance']['price_rejection_rate']}")
            
            print(f"\n🎯 卖点匹配证据:")
            print(f"   • 卖点匹配率: {ev['feature_match']['value']}")
            print(f"   • 热门匹配卖点:")
            for feat in ev['feature_match']['top_matched_features'][:3]:
                print(f"     - {feat['feature']}: {feat['match_count']} 次匹配")
            
            print(f"\n⚠️ 拒绝理由证据:")
            print(f"   • 主要顾虑: {ev['rejection_analysis']['primary_reason']}")
            if ev['rejection_analysis']['all_reasons']:
                print(f"   • 顾虑分布: {ev['rejection_analysis']['all_reasons']}")
            
            print(f"\n🎭 内部一致性证据:")
            print(f"   • 一致性评分: {ev['internal_consistency']['consistency_score']}")
            print(f"   • 评分标准差: {ev['internal_consistency']['score_std']}")
            print(f"   • 决策集中度: {ev['internal_consistency']['decision_concentration']}")
            
            print(f"\n💬 代表性观察:")
            for quote in seg_report['supporting_data']['sample_quotes']:
                if quote:
                    print(f"   • {quote}")
        
        # 对比分析
        if 'comparative_analysis' in report:
            comp = report['comparative_analysis']
            print(f"\n{'='*70}")
            print("📊 人群段对比分析")
            print(f"{'='*70}")
            print(f"第1名 vs 第2名:")
            print(f"   • 购买意愿差距: {comp['top_vs_second']['purchase_intention_gap']}")
            print(f"   • 价格接受度差距: {comp['top_vs_second']['price_acceptance_gap']}")
            print(f"   • 关键差异维度: {comp['top_vs_second']['key_difference']}")
            
            print(f"\n为什么第1名是最佳机会人群:")
            for reason in comp['why_top_is_opportunity']:
                if reason:
                    print(f"   ✓ {reason}")


# 演示
if __name__ == "__main__":
    import sys
    from datetime import datetime
    sys.path.insert(0, '/Users/xiangdong/.openclaw/workspace/reports')
    
    from digital_consumer_agents import AgentOrchestrator, load_agents_from_json, create_sample_product
    from scoring_engine import PurchaseIntentionEngine
    
    print("=" * 70)
    print("人群段分析器 - 完整证据链演示")
    print("=" * 70)
    
    # 加载数据
    agents = load_agents_from_json("persona_samples_complete.json")
    orchestrator = AgentOrchestrator()
    orchestrator.load_agents([a.to_dict() for a in agents])
    product = create_sample_product()
    
    print(f"\n加载完成: {len(agents)} 个角色")
    print(f"测试产品: {product.name}")
    
    # 使用新引擎进行评估
    print("\n使用透明化评分引擎进行评估...")
    evaluations = []
    for agent in agents:
        result = PurchaseIntentionEngine.calculate(
            agent_profile=agent.to_dict(),
            product=product
        )
        
        # 生成决策
        intention = result['purchase_intention']
        if intention >= 0.7:
            decision = '强烈购买'
        elif intention >= 0.5:
            decision = '考虑购买'
        elif intention >= 0.3:
            decision = '犹豫观望'
        else:
            decision = '明确拒绝'
        
        evaluations.append({
            'agent_id': agent.sample_id,
            'segment': agent.segment_name,
            'purchase_intention': intention,
            'price_evaluation': result['price_acceptance'],
            'overall_score': result['weighted_score'],
            'decision': decision,
            'preferred_features': [],  # 简化处理
            'key_concerns': []
        })
    
    # 分析人群段
    analyzer = SegmentAnalyzer()
    segment_evidence = analyzer.analyze(evaluations)
    
    # 生成审计报告
    report = analyzer.generate_audit_report(segment_evidence, top_n=3)
    
    # 打印报告
    analyzer.print_audit_report(report)
    
    # 保存详细报告
    output_file = f"segment_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 详细报告已保存: {output_file}")
