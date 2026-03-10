#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数字消费者角色单元系统 (Digital Consumer Agent System)
200个可控数字人物库 - 8类主画像 × 每类25个数字人物

架构:
- 代码层: persona数据、参数约束、行为逻辑、状态管理
- LLM层: 自然语言表达、评论生成、短轮讨论
- 编排层: 回合控制、抽样、汇总、报告生成

运行模式:
- 第一层: 200个角色批量静默评估
- 第二层: 抽取代表角色进行小组讨论
- 第三层: 对少量关键角色做深度追问
"""

import json
import random
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import copy


class DecisionMode(Enum):
    """决策模式"""
    AUTHORITY_DEPENDENT = "权威依赖"
    SOCIAL_FOLLOWER = "社交跟随"
    PRICE_SENSITIVE = "价格敏感"
    EXPERIENCE_DRIVEN = "体验驱动"
    SELF_DIRECTED = "自我主导"


class PurchaseAction(Enum):
    """购买行为动作"""
    BROWSE = "浏览"
    COMPARE = "比较"
    COLLECT = "收藏"
    ADD_CART = "加购"
    PURCHASE = "购买"
    REVIEW = "评价"
    SHARE = "分享"
    SKIP = "跳过"


@dataclass
class Product:
    """产品定义"""
    name: str
    brand: str
    category: str
    price: float
    original_price: Optional[float] = None
    features: List[str] = field(default_factory=list)
    selling_points: List[str] = field(default_factory=list)
    packaging: Dict[str, Any] = field(default_factory=dict)
    reviews: List[Dict] = field(default_factory=list)
    rating: float = 0.0
    sales_volume: int = 0


@dataclass
class DigitalConsumerAgent:
    """
    数字消费者角色单元
    
    核心属性:
    - sample_id: 唯一标识 (如 M01-01)
    - segment_id: 所属人群段 (如 M01)
    - basic_profile: 基础画像 (年龄、城市、收入等)
    - mindset_profile: 心智特征 (决策模式、敏感度等)
    - consumption_profile: 消费偏好 (需求、渠道、预算等)
    - behavior_profile: 行为特征 (内容习惯、决策风格等)
    
    运行时状态:
    - memory: 当前任务中的短期记忆
    - state: 当前行为状态
    - interaction_history: 互动历史
    """
    
    # 基础标识
    sample_id: str
    segment_id: str
    segment_name: str
    subtype: str
    
    # 画像数据
    basic_profile: Dict[str, Any] = field(default_factory=dict)
    mindset_profile: Dict[str, Any] = field(default_factory=dict)
    consumption_profile: Dict[str, Any] = field(default_factory=dict)
    behavior_profile: Dict[str, Any] = field(default_factory=dict)
    expression_profile: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时状态
    memory: Dict[str, Any] = field(default_factory=dict)
    current_state: str = "idle"
    interaction_history: List[Dict] = field(default_factory=list)
    purchase_history: List[Dict] = field(default_factory=list)
    
    # 情绪/态度状态 (0-1)
    satisfaction: float = 0.5
    trust_level: float = 0.5
    interest_level: float = 0.5
    
    def __post_init__(self):
        """初始化后设置默认值"""
        if not self.memory:
            self.memory = {
                "current_product": None,
                "current_context": None,
                "recent_interactions": [],
                "task_goal": None
            }
    
    def get_persona_prompt(self) -> str:
        """生成角色提示词，用于LLM调用"""
        return f"""你是一位真实的消费者，请始终扮演以下角色：

【基本信息】
- 昵称: {self.basic_profile.get('nickname', '匿名')}
- 年龄: {self.basic_profile.get('age', 30)}岁
- 城市: {self.basic_profile.get('city', '未知')}
- 职业: {self.basic_profile.get('occupation', '未知')}
- 家庭年收入: {self.basic_profile.get('household_income_band', '未知')}
- 孩子年龄: {self.basic_profile.get('child_age_stage', '未知')}

【心智特征】
- 决策模式: {self.mindset_profile.get('decision_mode', '未知')}
- 开放程度: {self.mindset_profile.get('openness_level', 'medium')}
- 时间投入: {self.mindset_profile.get('time_investment', 'medium')}
- 价格敏感度: {self.mindset_profile.get('price_sensitivity', 'medium')}

【消费偏好】
- 核心需求: {', '.join(self.consumption_profile.get('core_needs', []))}
- 偏好渠道: {', '.join(self.consumption_profile.get('preferred_channels', []))}
- 信任触发点: {self.consumption_profile.get('trust_trigger', '未知')}
- 拒绝触发点: {self.consumption_profile.get('rejection_trigger', '未知')}
- 预算范围: {self.consumption_profile.get('budget_range', '未知')}

【表达风格】
- 语气风格: {self.expression_profile.get('tone_style', '自然')}
- 典型语录: "{self.expression_profile.get('likely_quote', '')}"

重要规则：
1. 始终保持这个角色的人设，不要跳出角色
2. 回答要符合这个角色的认知水平和表达习惯
3. 决策要基于角色的偏好和约束条件
4. 用第一人称"我"来表达
"""
    
    def evaluate_product(self, product: Product, context: Dict = None) -> Dict:
        """
        评估产品 (第一层: 批量静默评估)
        
        返回评估结果，包含:
        - overall_score: 综合评分 (0-10)
        - purchase_intention: 购买意愿 (0-1)
        - decision: 决策结果 (购买/考虑/拒绝)
        - reasoning: 决策理由
        - key_concerns: 关键关注点
        - preferred_features: 偏好的卖点
        """
        result = {
            "agent_id": self.sample_id,
            "agent_name": self.basic_profile.get('nickname'),
            "segment": self.segment_name,
            "product": product.name,
            "timestamp": self._get_timestamp()
        }
        
        # 基于画像特征计算评分
        scores = self._calculate_scores(product)
        
        # 综合评分
        overall_score = sum(scores.values()) / len(scores)
        
        # 购买意愿 (考虑价格敏感度)
        price_factor = self._evaluate_price(product)
        purchase_intention = (overall_score / 10) * price_factor
        
        # 决策判断
        if purchase_intention >= 0.7:
            decision = "强烈购买"
        elif purchase_intention >= 0.5:
            decision = "考虑购买"
        elif purchase_intention >= 0.3:
            decision = "犹豫观望"
        else:
            decision = "明确拒绝"
        
        result.update({
            "overall_score": round(overall_score, 2),
            "dimension_scores": scores,
            "purchase_intention": round(purchase_intention, 2),
            "decision": decision,
            "price_evaluation": price_factor,
            "reasoning": self._generate_reasoning(product, scores, decision),
            "key_concerns": self._identify_concerns(product),
            "preferred_features": self._identify_preferred_features(product)
        })
        
        # 更新记忆
        self.memory["last_evaluation"] = result
        self.interaction_history.append({
            "type": "evaluation",
            "product": product.name,
            "result": decision
        })
        
        return result
    
    def _calculate_scores(self, product: Product) -> Dict[str, float]:
        """基于画像计算各维度评分"""
        scores = {}
        
        # 功能匹配度
        needs = self.consumption_profile.get('core_needs', [])
        feature_match = len([f for f in product.features if any(n in f for n in needs)])
        scores['function_match'] = min(10, feature_match * 2 + 5)
        
        # 品牌信任度
        trust_trigger = self.consumption_profile.get('trust_trigger', '')
        if '大牌' in trust_trigger or '品牌' in trust_trigger:
            scores['brand_trust'] = 8 if product.brand in ['知名品牌', '国际品牌'] else 5
        else:
            scores['brand_trust'] = 6
        
        # 口碑评分
        scores['reputation'] = product.rating * 2 if product.rating else 5
        
        # 包装吸引力
        appearance_sens = self.mindset_profile.get('appearance_sensitivity', 'medium')
        if appearance_sens == 'high':
            scores['packaging'] = 7 if product.packaging.get('attractive') else 4
        else:
            scores['packaging'] = 5
        
        # 创新性评分
        openness = self.mindset_profile.get('openness_level', 'medium')
        if openness == 'high':
            scores['innovation'] = 8 if '创新' in product.selling_points else 5
        else:
            scores['innovation'] = 5
        
        return scores
    
    def _evaluate_price(self, product: Product) -> float:
        """评估价格接受度"""
        budget = self.consumption_profile.get('budget_range', '0-100')
        
        # 解析预算范围
        try:
            budget_parts = budget.replace('元', '').replace('/支', '').replace(',', '').split('-')
            budget_min = float(budget_parts[0])
            budget_max = float(budget_parts[1]) if len(budget_parts) > 1 else budget_min * 2
        except:
            budget_min, budget_max = 0, 100
        
        # 价格敏感度调整
        price_sens = self.mindset_profile.get('price_sensitivity', 'medium')
        sensitivity_factor = {'low': 1.2, 'medium': 1.0, 'high': 0.8}.get(price_sens, 1.0)
        
        adjusted_max = budget_max * sensitivity_factor
        
        if product.price <= budget_min:
            return 1.0
        elif product.price <= adjusted_max:
            return 0.7 + 0.3 * (adjusted_max - product.price) / (adjusted_max - budget_min)
        else:
            return max(0.1, 0.5 - (product.price - adjusted_max) / adjusted_max)
    
    def _generate_reasoning(self, product: Product, scores: Dict, decision: str) -> str:
        """生成决策理由 (简化版，实际可调用LLM生成更自然的表达)"""
        reasons = []
        
        if scores.get('function_match', 0) >= 7:
            reasons.append("功能符合我的需求")
        elif scores.get('function_match', 0) <= 4:
            reasons.append("功能不太符合我的需求")
        
        if scores.get('price_evaluation', 1) >= 0.8:
            reasons.append("价格在预算范围内")
        elif scores.get('price_evaluation', 1) <= 0.4:
            reasons.append("价格超出我的预算")
        
        trust_trigger = self.consumption_profile.get('trust_trigger', '')
        if '医生' in trust_trigger and '医生' in str(product.selling_points):
            reasons.append("有医生背书，我比较信任")
        
        if not reasons:
            reasons.append("整体感觉一般，没有特别吸引我的点")
        
        return "；".join(reasons)
    
    def _identify_concerns(self, product: Product) -> List[str]:
        """识别关键顾虑点"""
        concerns = []
        
        rejection = self.consumption_profile.get('rejection_trigger', '')
        if '价格' in rejection and product.price > 50:
            concerns.append("价格偏高")
        if '成分' in rejection:
            concerns.append("担心成分安全性")
        if '效果' in rejection:
            concerns.append("不确定实际效果")
        
        return concerns
    
    def _identify_preferred_features(self, product: Product) -> List[str]:
        """识别偏好的产品卖点"""
        preferred = []
        needs = self.consumption_profile.get('core_needs', [])
        
        for point in product.selling_points:
            if any(need in point for need in needs):
                preferred.append(point)
        
        return preferred[:3]
    
    def simulate_behavior(self, product: Product, scenario: str = "normal") -> Dict:
        """
        模拟消费者行为
        
        scenario: normal(正常浏览), promotion(促销活动), social(社交推荐)
        """
        evaluation = self.evaluate_product(product)
        intention = evaluation['purchase_intention']
        
        # 根据场景调整
        if scenario == "promotion":
            intention = min(1.0, intention * 1.3)
        elif scenario == "social":
            if self.mindset_profile.get('decision_mode') == '社交跟随':
                intention = min(1.0, intention * 1.5)
        
        # 行为链模拟
        behavior_chain = []
        
        # 浏览
        behavior_chain.append({"action": PurchaseAction.BROWSE.value, "duration": random.randint(10, 60)})
        
        if intention > 0.3:
            # 比较
            behavior_chain.append({"action": PurchaseAction.COMPARE.value, "items_compared": random.randint(2, 5)})
        
        if intention > 0.5:
            # 收藏或加购
            if random.random() < 0.5:
                behavior_chain.append({"action": PurchaseAction.COLLECT.value})
            behavior_chain.append({"action": PurchaseAction.ADD_CART.value})
        
        if intention > 0.7:
            # 购买
            behavior_chain.append({"action": PurchaseAction.PURCHASE.value, "quantity": random.randint(1, 3)})
            
            # 评价
            if random.random() < 0.6:
                behavior_chain.append({
                    "action": PurchaseAction.REVIEW.value,
                    "rating": random.randint(4, 5) if intention > 0.8 else random.randint(3, 4),
                    "content_type": "detailed" if self.mindset_profile.get('time_investment') == 'high' else "brief"
                })
            
            # 分享
            if random.random() < 0.3:
                behavior_chain.append({"action": PurchaseAction.SHARE.value, "channel": random.choice(['微信', '小红书', '微博'])})
        
        return {
            "agent_id": self.sample_id,
            "agent_name": self.basic_profile.get('nickname'),
            "product": product.name,
            "scenario": scenario,
            "purchase_intention": round(intention, 2),
            "final_decision": evaluation['decision'],
            "behavior_chain": behavior_chain,
            "estimated_conversion": self._calculate_conversion_probability(behavior_chain)
        }
    
    def _calculate_conversion_probability(self, behavior_chain: List[Dict]) -> float:
        """计算转化概率"""
        actions = [b['action'] for b in behavior_chain]
        if PurchaseAction.PURCHASE.value in actions:
            return 1.0
        elif PurchaseAction.ADD_CART.value in actions:
            return 0.6
        elif PurchaseAction.COLLECT.value in actions:
            return 0.3
        else:
            return 0.1
    
    def generate_response(self, message: str, context: Dict = None) -> str:
        """
        生成对话回复 (第二层/第三层: 讨论和追问)
        
        实际实现中这里会调用LLM，传入persona_prompt和当前消息
        """
        # 简化版实现，实际应调用LLM
        tone = self.expression_profile.get('tone_style', '自然')
        quote = self.expression_profile.get('likely_quote', '')
        
        # 根据决策模式生成不同风格的回复
        decision_mode = self.mindset_profile.get('decision_mode')
        
        if decision_mode == '权威依赖':
            prefix = "我觉得吧，还是要听专业人士的意见。"
        elif decision_mode == '社交跟随':
            prefix = "我身边的朋友都这么说，"
        elif decision_mode == '价格敏感':
            prefix = "我先看看价格合不合适，"
        else:
            prefix = ""
        
        # 这里应该调用LLM生成更自然的回复
        return f"[{self.basic_profile.get('nickname')}] {prefix}{quote}"
    
    def participate_discussion(self, topic: str, other_opinions: List[Dict] = None) -> Dict:
        """
        参与小组讨论 (第二层: 代表角色讨论)
        
        other_opinions: 其他Agent的观点
        """
        # 考虑社交影响
        my_opinion = self.evaluate_product(self.memory.get('current_product'))
        
        if other_opinions and self.mindset_profile.get('decision_mode') == '社交跟随':
            # 社交跟随型会受到他人影响
            avg_others = sum(o['purchase_intention'] for o in other_opinions) / len(other_opinions)
            my_opinion['purchase_intention'] = (my_opinion['purchase_intention'] + avg_others) / 2
        
        response = self.generate_response(topic)
        
        return {
            "agent_id": self.sample_id,
            "agent_name": self.basic_profile.get('nickname'),
            "segment": self.segment_name,
            "opinion": my_opinion,
            "response": response,
            "influence_level": self._calculate_influence_level()
        }
    
    def _calculate_influence_level(self) -> float:
        """计算在群体中的影响力"""
        # 基于职业、收入等因素
        occupation = self.basic_profile.get('occupation', '')
        income = self.basic_profile.get('household_income_band', '')
        
        influence = 0.5
        
        if any(title in occupation for title in ['医生', '专家', '教授', '高管']):
            influence += 0.3
        income_floor_match = re.search(r"\d+(?:\.\d+)?", income)
        income_floor = float(income_floor_match.group()) if income_floor_match else 0
        if income_floor > 50:
            influence += 0.2
        
        return min(1.0, influence)
    
    def deep_interview(self, questions: List[str]) -> List[Dict]:
        """
        深度访谈 (第三层: 关键角色深度追问)
        """
        responses = []
        
        for q in questions:
            # 这里应该调用LLM生成深度回答
            response = {
                "question": q,
                "answer": self.generate_response(q),
                "underlying_motivation": self._extract_motivation(q),
                "emotional_trigger": self._identify_emotional_trigger(q)
            }
            responses.append(response)
        
        return responses
    
    def _extract_motivation(self, question: str) -> str:
        """提取潜在动机"""
        needs = self.consumption_profile.get('core_needs', [])
        return f"核心需求驱动: {', '.join(needs[:2])}"
    
    def _identify_emotional_trigger(self, question: str) -> str:
        """识别情感触发点"""
        triggers = []
        if '孩子' in question:
            triggers.append("对孩子的关爱")
        if '安全' in question or '健康' in question:
            triggers.append("对健康的担忧")
        if '价格' in question or '贵' in question:
            triggers.append("经济压力")
        
        return ', '.join(triggers) if triggers else "理性考量"
    
    def reset_state(self):
        """重置状态，准备新任务"""
        self.memory = {
            "current_product": None,
            "current_context": None,
            "recent_interactions": [],
            "task_goal": None
        }
        self.current_state = "idle"
        self.interaction_history = []
        self.satisfaction = 0.5
        self.trust_level = 0.5
        self.interest_level = 0.5
    
    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            "sample_id": self.sample_id,
            "segment_id": self.segment_id,
            "segment_name": self.segment_name,
            "subtype": self.subtype,
            "basic_profile": self.basic_profile,
            "mindset_profile": self.mindset_profile,
            "consumption_profile": self.consumption_profile,
            "behavior_profile": self.behavior_profile,
            "expression_profile": self.expression_profile,
            "current_state": self.current_state,
            "satisfaction": self.satisfaction,
            "trust_level": self.trust_level,
            "interest_level": self.interest_level
        }
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AgentOrchestrator:
    """
    Agent编排器
    
    负责:
    - 批量调度200个Agent
    - 分层运行控制
    - 结果汇总和报告生成
    """
    
    def __init__(self, agents_data: List[Dict] = None):
        self.agents: Dict[str, DigitalConsumerAgent] = {}
        self.segments: Dict[str, List[str]] = {}  # segment_id -> [agent_ids]
        
        if agents_data:
            self.load_agents(agents_data)
    
    def load_agents(self, data: List[Dict]):
        """从JSON数据加载Agent"""
        for item in data:
            agent = DigitalConsumerAgent(
                sample_id=item['sample_id'],
                segment_id=item['segment_id'],
                segment_name=item['segment_name'],
                subtype=item.get('subtype', '未知'),
                basic_profile=item.get('basic_profile', {}),
                mindset_profile=item.get('mindset_profile', {}),
                consumption_profile=item.get('consumption_profile', {}),
                behavior_profile=item.get('behavior_profile', {}),
                expression_profile=item.get('expression_profile', {})
            )
            self.agents[agent.sample_id] = agent
            
            # 按人群段分组
            if agent.segment_id not in self.segments:
                self.segments[agent.segment_id] = []
            self.segments[agent.segment_id].append(agent.sample_id)
    
    # ==================== 第一层: 批量静默评估 ====================
    
    def batch_evaluate(self, product: Product, segment_filter: str = None) -> List[Dict]:
        """
        批量评估产品
        
        segment_filter: 可选，指定只评估某个人群段 (如 "M01")
        """
        results = []
        
        agent_ids = self.segments.get(segment_filter, list(self.agents.keys())) if segment_filter else list(self.agents.keys())
        
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            result = agent.evaluate_product(product)
            results.append(result)
        
        return results
    
    def batch_simulate(self, product: Product, scenario: str = "normal", sample_size: int = None) -> List[Dict]:
        """
        批量行为模拟
        
        sample_size: 可选，指定抽样数量 (用于快速预览)
        """
        results = []
        agent_ids = list(self.agents.keys())
        
        if sample_size and sample_size < len(agent_ids):
            agent_ids = random.sample(agent_ids, sample_size)
        
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            result = agent.simulate_behavior(product, scenario)
            results.append(result)
        
        return results
    
    # ==================== 第二层: 小组讨论 ====================
    
    def select_representatives(self, segment_id: str = None, method: str = "stratified", count: int = 8) -> List[str]:
        """
        选择代表角色进行讨论
        
        method: 
        - stratified: 分层抽样 (每个子型选代表)
        - random: 随机抽样
        - extreme: 极端用户 (最高和最低购买意愿)
        """
        if segment_id:
            agent_ids = self.segments.get(segment_id, [])
        else:
            agent_ids = list(self.agents.keys())
        
        if method == "random":
            return random.sample(agent_ids, min(count, len(agent_ids)))
        
        elif method == "stratified":
            # 按子型分层
            subtype_groups = {}
            for aid in agent_ids:
                agent = self.agents[aid]
                st = agent.subtype
                if st not in subtype_groups:
                    subtype_groups[st] = []
                subtype_groups[st].append(aid)
            
            selected = []
            per_subtype = max(1, count // len(subtype_groups))
            for st, ids in subtype_groups.items():
                selected.extend(random.sample(ids, min(per_subtype, len(ids))))
            
            return selected[:count]
        
        elif method == "extreme":
            # 需要先评估
            # 这里简化处理，返回随机样本
            return random.sample(agent_ids, min(count, len(agent_ids)))
        
        return agent_ids[:count]
    
    def group_discussion(self, topic: str, product: Product, participant_ids: List[str]) -> Dict:
        """
        组织小组讨论
        """
        # 设置当前产品
        for pid in participant_ids:
            self.agents[pid].memory['current_product'] = product
        
        # 收集各方观点
        opinions = []
        for pid in participant_ids:
            agent = self.agents[pid]
            opinion = agent.participate_discussion(topic, opinions)
            opinions.append(opinion)
        
        # 汇总讨论结果
        return {
            "topic": topic,
            "product": product.name,
            "participants": [self.agents[pid].basic_profile.get('nickname') for pid in participant_ids],
            "opinions": opinions,
            "consensus_level": self._calculate_consensus(opinions),
            "key_insights": self._extract_discussion_insights(opinions)
        }
    
    def _calculate_consensus(self, opinions: List[Dict]) -> float:
        """计算共识度"""
        if len(opinions) < 2:
            return 1.0
        
        intentions = [o['opinion']['purchase_intention'] for o in opinions]
        variance = sum((i - sum(intentions)/len(intentions))**2 for i in intentions) / len(intentions)
        return max(0, 1 - variance * 4)  # 归一化到0-1
    
    def _extract_discussion_insights(self, opinions: List[Dict]) -> List[str]:
        """提取讨论洞察"""
        insights = []
        
        # 统计支持/反对
        supporters = [o for o in opinions if o['opinion']['decision'] in ['强烈购买', '考虑购买']]
        opposers = [o for o in opinions if o['opinion']['decision'] in ['明确拒绝', '犹豫观望']]
        
        insights.append(f"支持者: {len(supporters)}人, 反对者: {len(opposers)}人")
        
        # 提取主要顾虑
        all_concerns = []
        for o in opinions:
            all_concerns.extend(o['opinion'].get('key_concerns', []))
        
        if all_concerns:
            from collections import Counter
            top_concerns = Counter(all_concerns).most_common(3)
            insights.append(f"主要顾虑: {', '.join([c[0] for c in top_concerns])}")
        
        return insights
    
    # ==================== 第三层: 深度追问 ====================
    
    def deep_dive(self, agent_id: str, questions: List[str]) -> Dict:
        """
        对关键角色进行深度追问
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        
        responses = agent.deep_interview(questions)
        
        return {
            "agent_id": agent_id,
            "agent_name": agent.basic_profile.get('nickname'),
            "segment": agent.segment_name,
            "profile_summary": {
                "age": agent.basic_profile.get('age'),
                "occupation": agent.basic_profile.get('occupation'),
                "income": agent.basic_profile.get('household_income_band'),
                "decision_mode": agent.mindset_profile.get('decision_mode')
            },
            "interview_responses": responses,
            "persona_consistency_score": self._check_consistency(agent, responses)
        }
    
    def _check_consistency(self, agent: DigitalConsumerAgent, responses: List[Dict]) -> float:
        """检查角色一致性"""
        # 简化实现，实际应分析回答是否符合人设
        return 0.85
    
    # ==================== 报告生成 ====================
    
    def generate_report(self, evaluation_results: List[Dict], output_format: str = "json") -> Dict:
        """
        生成评估报告
        """
        report = {
            "summary": {
                "total_evaluated": len(evaluation_results),
                "avg_score": round(sum(r['overall_score'] for r in evaluation_results) / len(evaluation_results), 2) if evaluation_results else 0,
                "avg_intention": round(sum(r['purchase_intention'] for r in evaluation_results) / len(evaluation_results), 2) if evaluation_results else 0,
            },
            "decision_distribution": self._count_decisions(evaluation_results),
            "segment_analysis": self._analyze_by_segment(evaluation_results),
            "key_findings": self._generate_findings(evaluation_results)
        }
        
        # 计算转化率预估
        strong_buyers = len([r for r in evaluation_results if r['decision'] == '强烈购买'])
        consider_buyers = len([r for r in evaluation_results if r['decision'] == '考虑购买'])
        report['summary']['estimated_conversion_rate'] = round((strong_buyers + consider_buyers * 0.3) / len(evaluation_results) * 100, 1) if evaluation_results else 0
        
        return report
    
    def _count_decisions(self, results: List[Dict]) -> Dict:
        """统计决策分布"""
        from collections import Counter
        decisions = [r['decision'] for r in results]
        return dict(Counter(decisions))
    
    def _analyze_by_segment(self, results: List[Dict]) -> Dict:
        """按人群段分析"""
        segment_stats = {}
        
        for r in results:
            seg = r.get('segment', '未知')
            if seg not in segment_stats:
                segment_stats[seg] = {'count': 0, 'total_score': 0, 'total_intention': 0}
            segment_stats[seg]['count'] += 1
            segment_stats[seg]['total_score'] += r['overall_score']
            segment_stats[seg]['total_intention'] += r['purchase_intention']
        
        # 计算平均值
        for seg in segment_stats:
            count = segment_stats[seg]['count']
            segment_stats[seg]['avg_score'] = round(segment_stats[seg]['total_score'] / count, 2)
            segment_stats[seg]['avg_intention'] = round(segment_stats[seg]['total_intention'] / count, 2)
            del segment_stats[seg]['total_score']
            del segment_stats[seg]['total_intention']
        
        return segment_stats
    
    def _generate_findings(self, results: List[Dict]) -> List[str]:
        """生成关键发现"""
        findings = []
        
        # 整体接受度
        avg_intention = sum(r['purchase_intention'] for r in results) / len(results) if results else 0
        if avg_intention > 0.6:
            findings.append("整体接受度较高，产品具有市场潜力")
        elif avg_intention < 0.4:
            findings.append("整体接受度偏低，需要优化产品或定位")
        else:
            findings.append("接受度中等，存在明显的人群差异")
        
        # 价格敏感度
        price_concerns = sum(1 for r in results if '价格' in str(r.get('key_concerns', [])))
        if price_concerns > len(results) * 0.3:
            findings.append(f"约{round(price_concerns/len(results)*100)}%的用户对价格有顾虑")
        
        return findings


# ==================== 工具函数 ====================

def load_agents_from_json(file_path: str) -> List[DigitalConsumerAgent]:
    """从JSON文件加载Agent数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    agents = []
    for item in data.get('samples', []):
        agent = DigitalConsumerAgent(
            sample_id=item['sample_id'],
            segment_id=item['segment_id'],
            segment_name=item['segment_name'],
            subtype=item.get('subtype', '未知'),
            basic_profile=item.get('basic_profile', {}),
            mindset_profile=item.get('mindset_profile', {}),
            consumption_profile=item.get('consumption_profile', {}),
            behavior_profile=item.get('behavior_profile', {}),
            expression_profile=item.get('expression_profile', {})
        )
        agents.append(agent)
    
    return agents


def create_sample_product() -> Product:
    """创建示例产品"""
    return Product(
        name="舒客儿童益生菌牙膏",
        brand="舒客",
        category="儿童口腔护理",
        price=39.9,
        original_price=59.9,
        features=[
            "益生菌配方",
            "低氟防蛀",
            "水果口味",
            "可吞咽安全"
        ],
        selling_points=[
            "医生推荐使用",
            "99%天然成分",
            "无添加防腐剂",
            "卡通联名包装"
        ],
        packaging={
            "attractive": True,
            "size": "60g",
            "design": "卡通联名"
        },
        rating=4.6,
        sales_volume=50000
    )


# ==================== 演示运行 ====================

if __name__ == "__main__":
    # 加载200个Agent
    print("正在加载200个数字消费者角色...")
    agents = load_agents_from_json("persona_samples_complete.json")
    print(f"成功加载 {len(agents)} 个角色")
    
    # 创建编排器
    orchestrator = AgentOrchestrator()
    orchestrator.load_agents([a.to_dict() for a in agents])
    
    # 创建测试产品
    product = create_sample_product()
    print(f"\n测试产品: {product.name} (¥{product.price})")
    
    # ========== 第一层: 批量静默评估 ==========
    print("\n" + "="*50)
    print("第一层: 批量静默评估 (200个角色)")
    print("="*50)
    
    eval_results = orchestrator.batch_evaluate(product)
    report = orchestrator.generate_report(eval_results)
    
    print(f"\n评估汇总:")
    print(f"- 平均评分: {report['summary']['avg_score']}/10")
    print(f"- 平均购买意愿: {report['summary']['avg_intention']:.0%}")
    print(f"- 预估转化率: {report['summary']['estimated_conversion_rate']}%")
    print(f"\n决策分布:")
    for decision, count in report['decision_distribution'].items():
        print(f"  - {decision}: {count}人 ({count/len(eval_results)*100:.1f}%)")
    
    print(f"\n人群段分析:")
    for segment, stats in list(report['segment_analysis'].items())[:3]:
        print(f"  - {segment}: 平均意愿 {stats['avg_intention']:.0%}")
    
    # ========== 第二层: 小组讨论 ==========
    print("\n" + "="*50)
    print("第二层: 小组讨论 (抽取代表角色)")
    print("="*50)
    
    representatives = orchestrator.select_representatives(method="stratified", count=8)
    discussion = orchestrator.group_discussion(
        topic="你会给孩子买这款牙膏吗？为什么？",
        product=product,
        participant_ids=representatives
    )
    
    print(f"\n讨论主题: {discussion['topic']}")
    print(f"参与者: {', '.join(discussion['participants'])}")
    print(f"共识度: {discussion['consensus_level']:.0%}")
    print(f"\n关键洞察:")
    for insight in discussion['key_insights']:
        print(f"  - {insight}")
    
    # ========== 第三层: 深度追问 ==========
    print("\n" + "="*50)
    print("第三层: 深度追问 (关键角色)")
    print("="*50)
    
    # 选择一个高影响力角色
    key_agent_id = representatives[0]
    deep_dive = orchestrator.deep_dive(
        agent_id=key_agent_id,
        questions=[
            "你平时如何给孩子选择牙膏？",
            "什么情况下你会尝试新品牌？",
            "你对这款产品的最大顾虑是什么？"
        ]
    )
    
    print(f"\n深度访谈对象: {deep_dive['agent_name']}")
    print(f"人群段: {deep_dive['segment']}")
    print(f"角色一致性评分: {deep_dive['persona_consistency_score']}")
    print(f"\n访谈问答:")
    for resp in deep_dive['interview_responses']:
        print(f"\nQ: {resp['question']}")
        print(f"A: {resp['answer']}")
        print(f"  [潜在动机: {resp['underlying_motivation']}]")
        print(f"  [情感触发: {resp['emotional_trigger']}]")
    
    print("\n" + "="*50)
    print("演示完成!")
    print("="*50)
