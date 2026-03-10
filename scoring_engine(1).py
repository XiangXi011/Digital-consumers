#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评分引擎 - 完全透明的购买意愿计算

计算链路:
1. 五维度评分 (0-10) → 2. 加权综合评分 → 3. 价格接受度修正 → 4. 场景因子调整 → 5. 购买意愿
"""

from dataclasses import dataclass
from typing import Dict, List, Any
import json


@dataclass
class ScoringDimension:
    """评分维度定义"""
    name: str
    weight: float
    description: str
    calculation_logic: str


class PurchaseIntentionEngine:
    """
    购买意愿计算引擎
    
    公式:
    购买意愿 = (Σ(维度得分 × 维度权重) / 10) × 价格接受度 × 场景因子
    
    维度权重总和 = 1.0
    """
    
    # 五维度评分体系
    DIMENSIONS = {
        'function_match': ScoringDimension(
            name='功能匹配度',
            weight=0.30,
            description='产品功能与消费者核心需求的匹配程度',
            calculation_logic='匹配需求数 × 2 + 基础分5分, 上限10分'
        ),
        'brand_trust': ScoringDimension(
            name='品牌信任度', 
            weight=0.20,
            description='消费者对品牌的信任程度',
            calculation_logic='基于信任触发点: 大牌偏好+3分, 医生背书+2分, 网红推荐+1分'
        ),
        'reputation': ScoringDimension(
            name='口碑评分',
            weight=0.20,
            description='产品口碑对决策的影响',
            calculation_logic='产品评分 × 2 (如4.5分→9分), 无评分默认5分'
        ),
        'packaging': ScoringDimension(
            name='包装吸引力',
            weight=0.15,
            description='包装设计的吸引力',
            calculation_logic='外观敏感度高: 包装好=7分, 一般=4分; 敏感度低: 统一5分'
        ),
        'innovation': ScoringDimension(
            name='创新性评分',
            weight=0.15,
            description='产品创新点对开放型消费者的吸引力',
            calculation_logic='开放度高+创新卖点=8分; 开放度低=5分'
        )
    }
    
    # 价格敏感度系数
    PRICE_SENSITIVITY_FACTOR = {
        'low': 1.2,      # 低敏感: 预算上限 × 1.2
        'medium': 1.0,   # 中敏感: 预算上限 × 1.0
        'high': 0.8      # 高敏感: 预算上限 × 0.8
    }
    
    # 场景因子
    SCENARIO_FACTOR = {
        'normal': 1.0,
        'promotion': 1.3,
        'social': 1.5,
        'urgent_need': 1.4
    }
    
    @classmethod
    def calculate(cls, agent_profile: Dict, product: Any, scenario: str = 'normal') -> Dict:
        """
        计算购买意愿 - 完整透明链路
        
        Returns:
            {
                'dimension_scores': {...},      # 五维度得分
                'weighted_score': float,         # 加权综合分(0-10)
                'price_acceptance': float,       # 价格接受度(0-1)
                'scenario_factor': float,        # 场景因子
                'purchase_intention': float,     # 最终购买意愿(0-1)
                'calculation_trace': [...],      # 计算过程追溯
                'confidence_level': str          # 置信度
            }
        """
        trace = []
        
        # Step 1: 五维度评分
        trace.append("=" * 50)
        trace.append("STEP 1: 五维度评分 (0-10分)")
        trace.append("=" * 50)
        
        dimension_scores = cls._calculate_dimensions(agent_profile, product, trace)
        
        # Step 2: 加权综合评分
        trace.append("\n" + "=" * 50)
        trace.append("STEP 2: 加权综合评分")
        trace.append("=" * 50)
        
        weighted_score = cls._calculate_weighted_score(dimension_scores, trace)
        
        # Step 3: 价格接受度
        trace.append("\n" + "=" * 50)
        trace.append("STEP 3: 价格接受度计算")
        trace.append("=" * 50)
        
        price_acceptance = cls._calculate_price_acceptance(agent_profile, product, trace)
        
        # Step 4: 场景因子
        trace.append("\n" + "=" * 50)
        trace.append("STEP 4: 场景因子调整")
        trace.append("=" * 50)
        
        scenario_factor = cls.SCENARIO_FACTOR.get(scenario, 1.0)
        trace.append(f"场景: {scenario} → 因子: {scenario_factor}")
        
        # Step 5: 最终购买意愿
        trace.append("\n" + "=" * 50)
        trace.append("STEP 5: 最终购买意愿计算")
        trace.append("=" * 50)
        
        # 公式: (加权综合分/10) × 价格接受度 × 场景因子
        base_intention = weighted_score / 10
        purchase_intention = base_intention * price_acceptance * scenario_factor
        purchase_intention = min(1.0, purchase_intention)  # 上限1.0
        
        trace.append(f"公式: (加权综合分/10) × 价格接受度 × 场景因子")
        trace.append(f"计算: ({weighted_score}/10) × {price_acceptance:.2f} × {scenario_factor}")
        trace.append(f"结果: {base_intention:.2f} × {price_acceptance:.2f} × {scenario_factor} = {purchase_intention:.2f}")
        
        # 置信度评估
        confidence = cls._assess_confidence(dimension_scores, price_acceptance)
        trace.append(f"\n置信度评估: {confidence}")
        
        return {
            'dimension_scores': dimension_scores,
            'weighted_score': round(weighted_score, 2),
            'price_acceptance': round(price_acceptance, 2),
            'scenario_factor': scenario_factor,
            'purchase_intention': round(purchase_intention, 2),
            'calculation_trace': trace,
            'confidence_level': confidence,
            'formula': '(Σ(维度得分×权重)/10) × 价格接受度 × 场景因子'
        }
    
    @classmethod
    def _calculate_dimensions(cls, agent_profile: Dict, product: Any, trace: List) -> Dict:
        """计算五维度得分"""
        scores = {}
        consumption = agent_profile.get('consumption_profile', {})
        mindset = agent_profile.get('mindset_profile', {})
        
        # 1. 功能匹配度
        needs = consumption.get('core_needs', [])
        features = getattr(product, 'features', [])
        selling_points = getattr(product, 'selling_points', [])
        
        match_count = sum(1 for need in needs 
                         for f in features + selling_points 
                         if need in f or f in need)
        scores['function_match'] = min(10, 5 + match_count * 1.5)
        
        trace.append(f"\n【功能匹配度】权重: {cls.DIMENSIONS['function_match'].weight}")
        trace.append(f"  消费者需求: {needs}")
        trace.append(f"  产品功能: {features}")
        trace.append(f"  匹配数: {match_count}")
        trace.append(f"  计算: 5 + {match_count}×1.5 = {scores['function_match']}")
        
        # 2. 品牌信任度
        trust_trigger = consumption.get('trust_trigger', '')
        brand = getattr(product, 'brand', '')
        
        base_trust = 5
        if '大牌' in trust_trigger or '品牌' in trust_trigger:
            base_trust = 7 if brand in ['知名品牌', '国际品牌', '舒客'] else 5
        if '医生' in trust_trigger:
            base_trust += 2 if any('医生' in sp for sp in selling_points) else 0
        if '网红' in trust_trigger or 'KOL' in trust_trigger:
            base_trust += 1
            
        scores['brand_trust'] = min(10, base_trust)
        
        trace.append(f"\n【品牌信任度】权重: {cls.DIMENSIONS['brand_trust'].weight}")
        trace.append(f"  信任触发点: {trust_trigger}")
        trace.append(f"  产品品牌: {brand}")
        trace.append(f"  基础信任分: {base_trust}")
        
        # 3. 口碑评分
        rating = getattr(product, 'rating', 0)
        scores['reputation'] = rating * 2 if rating else 5
        
        trace.append(f"\n【口碑评分】权重: {cls.DIMENSIONS['reputation'].weight}")
        trace.append(f"  产品评分: {rating}")
        trace.append(f"  计算: {rating} × 2 = {scores['reputation']}")
        
        # 4. 包装吸引力
        appearance_sens = mindset.get('appearance_sensitivity', 'medium')
        packaging = getattr(product, 'packaging', {})
        is_attractive = packaging.get('attractive', False)
        
        if appearance_sens == 'high':
            scores['packaging'] = 7 if is_attractive else 4
        elif appearance_sens == 'low':
            scores['packaging'] = 5
        else:
            scores['packaging'] = 6 if is_attractive else 5
        
        trace.append(f"\n【包装吸引力】权重: {cls.DIMENSIONS['packaging'].weight}")
        trace.append(f"  外观敏感度: {appearance_sens}")
        trace.append(f"  包装吸引力: {is_attractive}")
        trace.append(f"  得分: {scores['packaging']}")
        
        # 5. 创新性评分
        openness = mindset.get('openness_level', 'medium')
        has_innovation = any('创新' in sp or '新' in sp for sp in selling_points)
        
        if openness == 'high' and has_innovation:
            scores['innovation'] = 8
        elif openness == 'low':
            scores['innovation'] = 4
        else:
            scores['innovation'] = 6 if has_innovation else 5
        
        trace.append(f"\n【创新性评分】权重: {cls.DIMENSIONS['innovation'].weight}")
        trace.append(f"  开放程度: {openness}")
        trace.append(f"  创新卖点: {has_innovation}")
        trace.append(f"  得分: {scores['innovation']}")
        
        return scores
    
    @classmethod
    def _calculate_weighted_score(cls, dimension_scores: Dict, trace: List) -> float:
        """计算加权综合分"""
        weighted_sum = 0
        trace.append("维度得分 × 权重:")
        
        for dim_name, score in dimension_scores.items():
            dim = cls.DIMENSIONS[dim_name]
            weighted = score * dim.weight
            weighted_sum += weighted
            trace.append(f"  {dim.name}: {score} × {dim.weight} = {weighted:.2f}")
        
        trace.append(f"\n加权总分: {weighted_sum:.2f}/10")
        return weighted_sum
    
    @classmethod
    def _calculate_price_acceptance(cls, agent_profile: Dict, product: Any, trace: List) -> float:
        """计算价格接受度"""
        consumption = agent_profile.get('consumption_profile', {})
        mindset = agent_profile.get('mindset_profile', {})
        
        budget_range = consumption.get('budget_range', '0-100')
        price = getattr(product, 'price', 0)
        
        # 解析预算
        trace.append(f"消费者预算范围: {budget_range}")
        trace.append(f"产品价格: ¥{price}")
        
        try:
            budget_clean = budget_range.replace('元', '').replace('/支', '').replace(',', '')
            if '-' in budget_clean:
                parts = budget_clean.split('-')
                budget_min = float(parts[0])
                budget_max = float(parts[1])
            else:
                budget_min = 0
                budget_max = float(budget_clean)
        except:
            budget_min, budget_max = 0, 100
        
        trace.append(f"解析预算: ¥{budget_min} - ¥{budget_max}")
        
        # 价格敏感度调整
        price_sens = mindset.get('price_sensitivity', 'medium')
        sens_factor = cls.PRICE_SENSITIVITY_FACTOR.get(price_sens, 1.0)
        adjusted_max = budget_max * sens_factor
        
        trace.append(f"价格敏感度: {price_sens} → 调整系数: {sens_factor}")
        trace.append(f"调整后预算上限: ¥{adjusted_max:.1f}")
        
        # 计算接受度
        if price <= budget_min:
            acceptance = 1.0
            trace.append(f"价格低于预算下限 → 接受度: 100%")
        elif price <= adjusted_max:
            acceptance = 0.7 + 0.3 * (adjusted_max - price) / (adjusted_max - budget_min)
            trace.append(f"价格在预算范围内 → 接受度: {acceptance:.2f}")
        else:
            over_ratio = (price - adjusted_max) / adjusted_max
            acceptance = max(0.1, 0.5 - over_ratio * 0.5)
            trace.append(f"价格超出预算 → 接受度: {acceptance:.2f}")
        
        return acceptance
    
    @classmethod
    def _assess_confidence(cls, dimension_scores: Dict, price_acceptance: float) -> str:
        """评估置信度"""
        # 如果多个维度得分极端(0或10)，置信度降低
        extreme_count = sum(1 for s in dimension_scores.values() if s in [0, 10])
        
        if extreme_count >= 3:
            return "低 - 多个维度得分极端，建议人工复核"
        elif price_acceptance < 0.3:
            return "中 - 价格接受度低，可能快速拒绝"
        else:
            return "高 - 计算基于完整画像数据"


class ConversionSimulator:
    """
    转化模拟器 - 明确区分"模拟指标"和"业务指标"
    """
    
    @staticmethod
    def simulate_conversion_rate(evaluations: List[Dict]) -> Dict:
        """
        模拟成交倾向率 (非真实转化率)
        
        计算逻辑:
        - 强烈购买: 100% 转化权重
        - 考虑购买: 30% 转化权重  
        - 犹豫观望: 10% 转化权重
        - 明确拒绝: 0% 转化权重
        """
        decision_weights = {
            '强烈购买': 1.0,
            '考虑购买': 0.3,
            '犹豫观望': 0.1,
            '明确拒绝': 0.0
        }
        
        total_weight = 0
        decision_counts = {}
        
        for ev in evaluations:
            decision = ev.get('decision', '犹豫观望')
            weight = decision_weights.get(decision, 0.1)
            total_weight += weight
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        simulated_rate = (total_weight / len(evaluations) * 100) if evaluations else 0
        
        return {
            'simulated_conversion_rate': round(simulated_rate, 1),
            'decision_distribution': decision_counts,
            'weight_formula': '强烈购买×1.0 + 考虑购买×0.3 + 犹豫观望×0.1 + 明确拒绝×0',
            'disclaimer': '此为模拟指标，用于产品概念测试的相对比较，不等同真实市场转化',
            'applicable_scenarios': [
                '产品概念A/B测试对比',
                '不同人群接受度比较',
                '卖点优化方向判断',
                '价格敏感度分析'
            ],
            'not_applicable': [
                '直接作为销售预测',
                '与真实电商转化率对比',
                '财务预算依据'
            ]
        }


# 演示
if __name__ == "__main__":
    from digital_consumer_agents import load_agents_from_json, create_sample_product
    
    print("=" * 60)
    print("购买意愿计算引擎 - 透明化演示")
    print("=" * 60)
    
    # 加载一个示例角色
    agents = load_agents_from_json("persona_samples_complete.json")
    agent = agents[0]
    
    print(f"\n角色: {agent.basic_profile.get('nickname')}")
    print(f"人群段: {agent.segment_name}")
    print(f"决策模式: {agent.mindset_profile.get('decision_mode')}")
    
    # 创建产品
    product = create_sample_product()
    print(f"\n测试产品: {product.name} (¥{product.price})")
    
    # 计算购买意愿
    result = PurchaseIntentionEngine.calculate(
        agent_profile=agent.to_dict(),
        product=product,
        scenario='normal'
    )
    
    # 打印完整计算过程
    print("\n" + "=" * 60)
    print("完整计算过程")
    print("=" * 60)
    for line in result['calculation_trace']:
        print(line)
    
    print("\n" + "=" * 60)
    print("最终结果")
    print("=" * 60)
    print(f"五维度得分: {result['dimension_scores']}")
    print(f"加权综合分: {result['weighted_score']}/10")
    print(f"价格接受度: {result['price_acceptance']:.0%}")
    print(f"场景因子: {result['scenario_factor']}")
    print(f"购买意愿: {result['purchase_intention']:.0%}")
    print(f"置信度: {result['confidence_level']}")
