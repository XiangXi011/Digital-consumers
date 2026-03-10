#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数字妈妈体验官人物库生成器
生成200个JSON格式的人物样本（8人群 × 25人）
"""

import json
import re
import random
from datetime import datetime
from pathlib import Path

import yaml
THREE_POINT_SCALE = ['low', 'medium', 'high']
FIVE_POINT_SCALE = ['very_low', 'low', 'medium', 'high', 'very_high']

MINDSET_FIELD_SCALES = {
    'openness_level': THREE_POINT_SCALE,
    'time_investment': FIVE_POINT_SCALE,
    'appearance_sensitivity': FIVE_POINT_SCALE,
    'evidence_sensitivity': FIVE_POINT_SCALE,
    'trend_sensitivity': FIVE_POINT_SCALE,
    'price_sensitivity': FIVE_POINT_SCALE,
    'switching_willingness': FIVE_POINT_SCALE,
}


def load_segment_rules():
    """Load the segment-level constraint rules from the local YAML file."""
    base_dir = Path(__file__).resolve().parent
    matches = sorted(base_dir.glob("persona_generation_rules*.yaml"))
    if not matches:
        raise FileNotFoundError("persona_generation_rules YAML not found")

    with open(matches[0], 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def sample_from_whitelist(options, count=None):
    """Sample one or many values from a segment-specific whitelist."""
    if count is None:
        return random.choice(options)
    if count >= len(options):
        return random.sample(options, len(options))
    return random.sample(options, count)


def constrained_ordinal_choice(center_value, scale, max_distance=1):
    """Pick a value near the segment center while allowing bounded variation."""
    center_index = scale.index(center_value)
    candidates = []
    weights = []

    for idx, value in enumerate(scale):
        distance = abs(idx - center_index)
        if distance > max_distance:
            continue
        candidates.append(value)
        weights.append(6 if distance == 0 else 2)

    return random.choices(candidates, weights=weights, k=1)[0]


SEGMENT_RULES = load_segment_rules()
random.seed(42)


def extract_budget_floor(budget_text):
    """Return the first numeric value in the budget text."""
    matches = re.findall(r"\d+(?:\.\d+)?", budget_text)
    if not matches:
        return 0
    return float(matches[0])

# 设置随机种子以确保可重复性
random.seed(42)

# ==================== 配置数据 ====================

# 姓氏库
SURNAMES = ['李', '王', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗', 
            '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧', '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
            '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎', '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜']

# 女性名字库
FEMALE_NAMES = ['婉清', '雅琳', '诗涵', '雨萱', '梦琪', '晓雯', '静怡', '思琪', '佳怡', '雨婷', '欣怡', '梓涵', '语桐', '若曦', 
                '梦瑶', '紫萱', '可馨', '佳琪', '思颖', '雨欣', '美琳', '惠茜', '漫妮', '月婵', '嫦曦', '静香', '梦洁', '凌薇',
                '美莲', '雅静', '雪丽', '依娜', '雅芙', '怡香', '珺瑶', '婉婷', '睿婕', '馨蕊', '雪雁', '煜婷', '笑怡', '优璇',
                '雨嘉', '娅楠', '明美', '子涵', '欣妍', '子萱', '子怡', '梓萱', '思涵', '语嫣', '诗琪', '佳慧', '晓燕', '丽华',
                '淑芬', '秀兰', '桂英', '玉兰', '秀英', '晓梅', '红梅', '凤英', '春梅', '冬梅', '桂兰', '秀珍', '秀芳', '玉梅',
                '海燕', '彩霞', '小红', '小芳', '小玲', '小敏', '小静', '小倩', '小艳', '小慧', '小娟', '小霞', '小兰', '小英',
                '小凤', '小琴', '小云', '小珍', '小蓉', '小萍', '小薇', '小菲', '小璐', '小琳', '小婷', '小媛', '小妮', '小娜']

# 子型分布配置
SUBTYPE_DISTRIBUTION = {
    'M01': {'权威依赖型': 8, '品牌崇拜型': 7, '身份焦虑型': 6, '审美驱动型': 4},
    'M02': {'颜值种草型': 10, '新概念尝鲜型': 8, '社媒跟风型': 7},
    'M03': {'经验主义型': 12, '老牌子忠诚型': 8, '实用主义型': 5},
    'M04': {'效率至上型': 12, 'KOL依赖型': 8, '销量导向型': 5},
    'M05': {'成分党型': 12, '研究型': 8, '性价比导向型': 5},
    'M06': {'面子消费型': 10, '直播间冲动型': 8, '功能崇拜型': 7},
    'M07': {'数据驱动型': 10, '系统管理型': 8, '完美主义型': 7},
    'M08': {'实用主义型': 15, '价格敏感型': 10}
}

# 人群详细配置
SEGMENT_CONFIG = {
    'M01': {
        'name': '宠爱富养家',
        'age_range': [35, 45],
        'cities': {
            '北京': ['朝阳区', '海淀区', '顺义区', '通州区'],
            '上海': ['静安区', '浦东新区', '徐汇区', '长宁区', '黄浦区'],
            '深圳': ['南山区', '福田区', '宝安区', '龙华区'],
            '广州': ['天河区', '番禺区', '珠江新城']
        },
        'city_tier': '一线',
        'occupations': ['投行高管', '律所合伙人', '科技公司CFO', '企业主', '大学教授', '奢侈品品牌高管', 
                       '私募基金合伙人', '医院副院长', '咨询公司合伙人', '影视制片人', '画廊主理人',
                       '珠宝品牌创始人', '国际学校校长', '建筑设计事务所合伙人', '医疗器械公司高管', '全职妈妈(前高管)'],
        'income_bands': ['80万-120万', '120万-200万', '200万-300万', '300万-600万', '600万以上'],
        'family_structures': ['三口之家', '三口之家+保姆', '三口之家+住家阿姨', '三口之家+育儿嫂', '三口之家+司机+保姆'],
        'child_ages': ['3岁', '4岁', '5岁', '6岁', '7岁', '8岁', '9岁', '10岁', '12岁'],
        'budget': '60-100元/支',
        'rating': 4.0,
        'decision': '明确不买'
    },
    'M02': {
        'name': '自在成长家',
        'age_range': [25, 35],
        'cities': {
            '杭州': ['西湖区', '滨江区', '余杭区'],
            '成都': ['锦江区', '武侯区', '高新区'],
            '南京': ['鼓楼区', '建邺区', '玄武区'],
            '苏州': ['工业园区', '姑苏区', '高新区'],
            '武汉': ['江汉区', '武昌区', '洪山区'],
            '西安': ['雁塔区', '碑林区', '未央区'],
            '长沙': ['芙蓉区', '天心区', '岳麓区'],
            '郑州': ['金水区', '二七区', '中原区'],
            '青岛': ['市南区', '市北区', '崂山区'],
            '宁波': ['海曙区', '江北区', '鄞州区'],
            '厦门': ['思明区', '湖里区'],
            '合肥': ['蜀山区', '包河区', '庐阳区'],
            '济南': ['历下区', '市中区', '历城区'],
            '东莞': ['南城街道', '东城街道'],
            '福州': ['鼓楼区', '台江区', '仓山区']
        },
        'city_tier': '新一线',
        'occupations': ['互联网产品经理', 'UI设计师', '市场营销', '外企HR', '小学老师', '银行职员',
                       '新媒体运营', '会计', '设计师', '旅游策划', '公务员', '护士', '电商运营',
                       '行政', '人事经理', '平面设计师', '教师', '保险代理', '旅行社经理', '外贸公司职员'],
        'income_bands': ['20万-25万', '25万-30万', '30万-35万', '35万-40万'],
        'family_structures': ['三口之家', '三口之家(老人偶尔帮忙)'],
        'child_ages': ['0岁', '1岁', '2岁', '3岁', '4岁', '5岁', '6岁', '7岁', '8岁'],
        'budget': '15-30元/支',
        'rating': 7.0,
        'decision': '会购买'
    },
    'M03': {
        'name': '传统关爱妈',
        'age_range': [38, 48],
        'cities': {
            '武汉': ['江汉区', '武昌区'],
            '西安': ['雁塔区', '碑林区'],
            '郑州': ['金水区', '二七区'],
            '长沙': ['芙蓉区', '天心区'],
            '合肥': ['蜀山区', '包河区'],
            '南昌': ['东湖区', '西湖区'],
            '昆明': ['五华区', '盘龙区'],
            '南宁': ['青秀区', '兴宁区'],
            '贵阳': ['南明区', '云岩区'],
            '兰州': ['城关区', '七里河区'],
            '太原': ['小店区', '迎泽区'],
            '石家庄': ['长安区', '桥西区'],
            '哈尔滨': ['南岗区', '道里区'],
            '长春': ['朝阳区', '南关区'],
            '沈阳': ['和平区', '沈河区'],
            '济南': ['历下区', '市中区'],
            '青岛': ['市南区', '市北区'],
            '大连': ['中山区', '西岗区'],
            '无锡': ['梁溪区', '滨湖区'],
            '常州': ['天宁区', '钟楼区']
        },
        'city_tier': '二线',
        'occupations': ['中学老师', '小学老师', '银行职员', '会计', '行政主管', '事业单位职员',
                       '国企员工', '护士', '医生(非口腔)', '公务员', '超市收银员', '工厂管理人员',
                       '小企业主', '个体户', '全职妈妈'],
        'income_bands': ['15万-20万', '20万-25万', '25万-30万'],
        'family_structures': ['三口之家', '三口之家+老人同住'],
        'child_ages': ['6岁', '7岁', '8岁', '9岁', '10岁', '11岁', '12岁', '13岁', '14岁'],
        'budget': '10-20元/支',
        'rating': 7.0,
        'decision': '会购买'
    },
    'M04': {
        'name': '高线忙碌派',
        'age_range': [32, 40],
        'cities': {
            '北京': ['朝阳区', '海淀区'],
            '上海': ['浦东新区', '静安区'],
            '深圳': ['南山区', '福田区'],
            '广州': ['天河区', '海珠区'],
            '杭州': ['滨江区', '西湖区'],
            '成都': ['高新区', '锦江区'],
            '南京': ['建邺区', '鼓楼区'],
            '苏州': ['工业园区', '姑苏区'],
            '武汉': ['江汉区', '武昌区']
        },
        'city_tier': '一线/新一线',
        'occupations': ['互联网大厂经理', '金融分析师', '外企中层', '律师', '医生', '建筑师',
                       '市场总监', '销售总监', '运营总监', '产品经理', '项目经理', '咨询顾问',
                       '审计师', '税务师'],
        'income_bands': ['50万-70万', '70万-100万', '100万-150万'],
        'family_structures': ['三口之家+老人帮忙', '双职工+育儿嫂'],
        'child_ages': ['3岁', '4岁', '5岁', '6岁', '7岁', '8岁'],
        'budget': '20-40元/支',
        'rating': 7.5,
        'decision': '会购买并回购'
    },
    'M05': {
        'name': '品质精算师',
        'age_range': [30, 38],
        'cities': {
            '杭州': ['西湖区', '滨江区'],
            '南京': ['鼓楼区', '建邺区'],
            '苏州': ['工业园区', '高新区'],
            '成都': ['高新区', '武侯区'],
            '武汉': ['武昌区', '江汉区'],
            '北京': ['海淀区', '朝阳区'],
            '上海': ['徐汇区', '静安区'],
            '深圳': ['南山区', '福田区'],
            '广州': ['天河区', '越秀区'],
            '宁波': ['鄞州区', '海曙区'],
            '无锡': ['滨湖区', '梁溪区'],
            '青岛': ['崂山区', '市南区']
        },
        'city_tier': '新一线/一线',
        'occupations': ['工程师', '数据分析师', '科研人员', '医生', '药剂师', '营养师',
                       '教师', '会计师', '审计师', '律师', '记者', '编辑', 'IT工程师', '产品经理'],
        'income_bands': ['35万-50万', '50万-70万', '70万-100万'],
        'family_structures': ['三口之家', '三口之家(偶尔老人帮忙)'],
        'child_ages': ['2岁', '3岁', '4岁', '5岁', '6岁', '7岁', '8岁', '9岁'],
        'budget': '15-35元/支',
        'rating': 7.0,
        'decision': '会购买但持续对比'
    },
    'M06': {
        'name': '小镇贵妇妈',
        'age_range': [28, 38],
        'cities': {
            '浙江某县': ['县城', '镇区'],
            '江苏某县': ['县城', '镇区'],
            '福建某县': ['县城', '镇区'],
            '广东某县': ['县城', '镇区'],
            '山东某县': ['县城', '镇区'],
            '河南某县': ['县城', '镇区'],
            '河北某县': ['县城', '镇区'],
            '四川某县': ['县城', '镇区'],
            '湖南某县': ['县城', '镇区'],
            '湖北某县': ['县城', '镇区']
        },
        'city_tier': '三线/四线',
        'occupations': ['个体户老板娘', '小企业主', '美容院老板', '服装店店主', '微商',
                       '直播主播', '幼儿园老师', '小学老师', '银行职员', '公务员',
                       '事业单位', '医院护士', '全职妈妈', '老公做生意'],
        'income_bands': ['20万-30万', '30万-40万', '40万-50万'],
        'family_structures': ['三口之家+老人带娃', '三口之家(老公做生意)'],
        'child_ages': ['2岁', '3岁', '4岁', '5岁', '6岁', '7岁', '8岁'],
        'budget': '10-25元/支',
        'rating': 8.5,
        'decision': '最愿意购买'
    },
    'M07': {
        'name': '全能优等家',
        'age_range': [33, 42],
        'cities': {
            '北京': ['海淀区', '朝阳区'],
            '上海': ['徐汇区', '静安区'],
            '深圳': ['南山区', '福田区'],
            '广州': ['天河区', '越秀区'],
            '杭州': ['西湖区', '滨江区'],
            '南京': ['鼓楼区', '建邺区'],
            '苏州': ['工业园区', '高新区'],
            '成都': ['高新区', '锦江区']
        },
        'city_tier': '一线/新一线',
        'occupations': ['企业高管', '医生', '律师', '投行VP', '咨询公司总监',
                       '科技公司高管', '大学教授', '研究所负责人', '高级公务员', '外企总监'],
        'income_bands': ['80万-120万', '120万-200万', '200万-300万'],
        'family_structures': ['三口之家+家教', '三口之家+保姆', '精英教育家庭'],
        'child_ages': ['5岁', '6岁', '7岁', '8岁', '9岁', '10岁', '11岁', '12岁'],
        'budget': '50-100元/支',
        'rating': 6.0,
        'decision': '不会作为首选'
    },
    'M08': {
        'name': '佛系粗养家',
        'age_range': [35, 45],
        'cities': {
            '地级市': ['市区', '郊区'],
            '县级市': ['市区', '镇区'],
            '县城': ['县城', '乡镇']
        },
        'city_tier': '三线/四线',
        'occupations': ['工厂工人', '超市员工', '服务员', '保洁', '保安', '司机',
                       '小职员', '小学老师', '幼儿园老师', '护士', '银行柜员',
                       '普通公务员', '事业单位普通职员'],
        'income_bands': ['12万-15万', '15万-18万', '18万-22万'],
        'family_structures': ['三口之家+老人带娃', '双职工+老人'],
        'child_ages': ['4岁', '5岁', '6岁', '7岁', '8岁', '9岁', '10岁'],
        'budget': '10-20元/支',
        'rating': 8.0,
        'decision': '会购买'
    }
}

# 子型特征配置
SUBTYPE_FEATURES = {
    '权威依赖型': {
        'decision_mode': '权威依赖',
        'trust_trigger': '医生推荐+专业背书',
        'rejection_trigger': '无医生背书',
        'tone': '理性分析+权威口吻',
        'quote': '牙医说用什么我就用什么',
        'review_focus': ['医生背书', '专业认证', '医院渠道']
    },
    '品牌崇拜型': {
        'decision_mode': '品牌优先',
        'trust_trigger': '品牌档次+进口标识',
        'rejection_trigger': '国产品牌+低价',
        'tone': '身份焦虑+品牌崇拜',
        'quote': '大品牌有保障，小牌子不敢用',
        'review_focus': ['品牌档次', '进口标识', '包装质感']
    },
    '身份焦虑型': {
        'decision_mode': '社交驱动',
        'trust_trigger': '社交圈层口碑+品牌档次',
        'rejection_trigger': '圈层不认可',
        'tone': '身份焦虑+社交口吻',
        'quote': '妈妈群里都在用XX牌子，我不能让孩子用差的',
        'review_focus': ['社交圈层', '品牌档次', '身份认同']
    },
    '审美驱动型': {
        'decision_mode': '颜值优先',
        'trust_trigger': '包装设计+颜值',
        'rejection_trigger': '包装丑+设计普通',
        'tone': '审美驱动+精英视角',
        'quote': '包装太丑了，我不想放在洗漱台上',
        'review_focus': ['包装设计', '颜值', '设计感']
    },
    '颜值种草型': {
        'decision_mode': '颜值优先',
        'trust_trigger': '包装好看+小红书种草',
        'rejection_trigger': '包装丑',
        'tone': '轻松随意+种草口吻',
        'quote': '这个包装太好看了，小红书刷到就下单了',
        'review_focus': ['包装颜值', '小红书口碑', '孩子喜欢']
    },
    '新概念尝鲜型': {
        'decision_mode': '尝鲜驱动',
        'trust_trigger': '新概念+新功能',
        'rejection_trigger': '没新意+老套',
        'tone': '好奇探索+尝鲜口吻',
        'quote': '看到新品就想试试，反正不贵',
        'review_focus': ['新功能', '新概念', '尝鲜体验']
    },
    '社媒跟风型': {
        'decision_mode': '社媒种草',
        'trust_trigger': '小红书推荐+博主种草',
        'rejection_trigger': '没人推荐',
        'tone': '轻松随意+跟风口吻',
        'quote': '小红书好多博主推荐，跟风买了',
        'review_focus': ['小红书口碑', '博主推荐', '跟风购买']
    },
    '经验主义型': {
        'decision_mode': '经验依赖',
        'trust_trigger': '老牌子+多年经验',
        'rejection_trigger': '新牌子+没听过',
        'tone': '朴实直接+经验口吻',
        'quote': '老牌子用了这么多年，放心',
        'review_focus': ['品牌历史', '老牌子信任', '使用经验']
    },
    '老牌子忠诚型': {
        'decision_mode': '品牌忠诚',
        'trust_trigger': '品牌历史+超市有卖',
        'rejection_trigger': '新牌子+网上才有',
        'tone': '朴实直接+忠诚口吻',
        'quote': '一直用这个牌子，不换',
        'review_focus': ['品牌历史', '超市渠道', '忠诚度']
    },
    '实用主义型': {
        'decision_mode': '实用优先',
        'trust_trigger': '功能简单+价格实惠',
        'rejection_trigger': '功能花哨+价格贵',
        'tone': '朴实直接+实用导向',
        'quote': '能防蛀就行，别的无所谓',
        'review_focus': ['防蛀效果', '价格实惠', '简单好用']
    },
    '效率至上型': {
        'decision_mode': '效率优先',
        'trust_trigger': '销量高+好评多+KOL推荐',
        'rejection_trigger': '需要研究对比',
        'tone': '简洁直接+效率口吻',
        'quote': '销量高总不会错，懒得研究',
        'review_focus': ['销量数据', '好评率', 'KOL推荐']
    },
    'KOL依赖型': {
        'decision_mode': 'KOL信任',
        'trust_trigger': 'KOL推荐+博主背书',
        'rejection_trigger': '无KOL推荐',
        'tone': '信任转移+KOL口吻',
        'quote': 'XX博主推荐的，她选品很严格',
        'review_focus': ['KOL推荐', '博主背书', '信任转移']
    },
    '销量导向型': {
        'decision_mode': '销量导向',
        'trust_trigger': '销量排行+好评率',
        'rejection_trigger': '销量低+差评多',
        'tone': '数据导向+销量口吻',
        'quote': '月销10万+，应该没问题',
        'review_focus': ['销量排行', '好评率', '数据证明']
    },
    '成分党型': {
        'decision_mode': '成分研究',
        'trust_trigger': '成分表详细+氟含量明确',
        'rejection_trigger': '成分表模糊+营销话术',
        'tone': '理性分析+质疑态度',
        'quote': '我要看成分表，氟含量多少？',
        'review_focus': ['成分表', '氟含量', '无添加']
    },
    '研究型': {
        'decision_mode': '数据驱动',
        'trust_trigger': '专业文章+检测报告',
        'rejection_trigger': '无科学依据',
        'tone': '理性分析+数据导向',
        'quote': '知乎上研究过，这个成分安全',
        'review_focus': ['科学依据', '专业文章', '检测报告']
    },
    '性价比导向型': {
        'decision_mode': '性价比计算',
        'trust_trigger': '成分好+价格合理',
        'rejection_trigger': '价格虚高+成分一般',
        'tone': '理性分析+性价比口吻',
        'quote': '成分差不多，这个性价比高',
        'review_focus': ['性价比', '成分对比', '价格合理']
    },
    '面子消费型': {
        'decision_mode': '面子导向',
        'trust_trigger': '包装高级+功能多',
        'rejection_trigger': '包装普通+功能少',
        'tone': '热情夸张+面子口吻',
        'quote': '这个看着高级，送人也有面子',
        'review_focus': ['包装高级', '功能数量', '面子感']
    },
    '直播间冲动型': {
        'decision_mode': '直播冲动',
        'trust_trigger': '主播推荐+限时优惠',
        'rejection_trigger': '无优惠+没直播',
        'tone': '热情夸张+冲动口吻',
        'quote': '主播说效果好，还有优惠，买了！',
        'review_focus': ['直播间话术', '优惠力度', '主播推荐']
    },
    '功能崇拜型': {
        'decision_mode': '功能数量',
        'trust_trigger': '功能多=高级',
        'rejection_trigger': '功能少=低端',
        'tone': '热情夸张+功能口吻',
        'quote': '功能越多越好，这个有5种功能',
        'review_focus': ['功能数量', '功能描述', '高级感']
    },
    '数据驱动型': {
        'decision_mode': '数据驱动',
        'trust_trigger': '临床数据+效果追踪',
        'rejection_trigger': '无数据支撑',
        'tone': '理性分析+数据导向',
        'quote': '有没有临床数据？效果怎么追踪？',
        'review_focus': ['临床数据', '效果追踪', '专业背书']
    },
    '系统管理型': {
        'decision_mode': '系统管理',
        'trust_trigger': '系统性方案+配套工具',
        'rejection_trigger': '单一产品+无配套',
        'tone': '理性分析+系统思维',
        'quote': '需要配套刷牙APP和追踪工具',
        'review_focus': ['系统性方案', '配套工具', '管理思维']
    },
    '完美主义型': {
        'decision_mode': '完美主义',
        'trust_trigger': '最好品质+专业认证',
        'rejection_trigger': '普通品质+无认证',
        'tone': '高标准+专业口吻',
        'quote': '要最好的，不能有瑕疵',
        'review_focus': ['品质标准', '专业认证', '完美度']
    },
    '价格敏感型': {
        'decision_mode': '价格敏感',
        'trust_trigger': '价格便宜+老牌子',
        'rejection_trigger': '价格贵+新牌子',
        'tone': '朴实随意+价格口吻',
        'quote': '便宜就行，太贵买不起',
        'review_focus': ['价格便宜', '老牌子', '实惠']
    }
}

# 模拟反馈模板
FEEDBACK_TEMPLATES = {
    'M01': [
        "舒客？没听过。{price}？这能防蛀？我给孩子用的是{brand}，一支{high_price}，用了{year}年没蛀牙。",
        "我在{channel}买儿童牙膏，只看进口区。舒客放在国产货架上，我看都不会看一眼。",
        "我们小区妈妈群，孩子用的东西都是互相推荐的。舒客？没人提过。",
        "我儿子的牙医是{title}，他推荐什么我买什么。舒客？牙医没提过。",
        "我研究过儿童牙膏，舒客的成分表写得不够详细。{brand}的成分标注很清楚。",
        "我做{job}这么多年，太清楚品牌意味着什么。舒客这种国产牌子，包装就透着一股廉价感。",
        "我儿子的所有用品，从奶粉到牙膏，都是儿科医生开的单子。舒客？没出现在医生的推荐清单里。",
        "我工作太忙，没时间对比各种牙膏。我的策略是：买最贵的进口牌子，至少不会踩雷。",
        "我是做{job}的，对审美有要求。舒客的包装...怎么说呢，太普通了。",
        "我儿子戴牙套，牙医专门推荐了矫正期专用牙膏。舒客这种通用型的，不适合我们。"
    ],
    'M02': [
        "小红书刷到的，包装太好看了！{price}也不贵，买了试试。",
        "看到新品就想试试，反正不贵。孩子挺喜欢的，味道不错。",
        "好多博主推荐，跟风买了。用着还行，性价比可以。",
        "颜值即正义！这个包装太好看了，孩子也喜欢。",
        "{channel}上种草买的，包装好看，孩子愿意用。",
        "新概念？听起来不错，试试。反正{price}不贵。",
        "小红书好多人说好，我也买了。确实不错，会回购。",
        "包装好看，味道好闻，孩子喜欢。这就够了！",
        "看到{channel}推荐，顺手买了。用着还行。",
        "新出的？试试呗，{price}买不了吃亏。"
    ],
    'M03': [
        "老牌子了，超市一直有卖。{price}合适，用着放心。",
        "用了{year}年了，孩子没蛀牙。老牌子值得信赖。",
        "超市里随手拿的，老牌子，{price}也不贵。",
        "邻居推荐的，说用了好几年。我也买了，确实不错。",
        "功能简单，就是防蛀。{price}实惠，老牌子放心。",
        "一直用这个牌子，不换。孩子习惯了，效果也好。",
        "{channel}买的，老牌子，价格便宜。",
        "我妈说老牌子好，我就买了。用着还行。",
        "不追求什么新功能，能防蛀就行。{price}合适。",
        "老牌子，超市有卖，{price}实惠。这就够了。"
    ],
    'M04': [
        "没时间研究，看销量买的。月销{sales}，应该没问题。",
        "{kol}推荐的，她选品很严格。懒得自己研究，跟着买。",
        "京东销量排行第一，随手买了。用着还行，不踩雷。",
        "工作太忙，没时间对比。看好评率{rate}%就买了。",
        "{channel}上销量很高，懒得研究，买了。",
        "KOL推荐的，信任她。{price}也不贵，试试。",
        "看销量和好评买的，没踩雷。会回购。",
        "没时间看成分，看销量排行买的。效果还行。",
        "{channel}随手拿的，销量高，应该不错。",
        "效率至上，看数据买。销量{sales}，好评{rate}%，够了。"
    ],
    'M05': [
        "研究了成分表，氟含量{fluoride_percent}，符合标准。性价比不错。",
        "知乎上对比过，这个成分和{brand}差不多，价格便宜一半。",
        "看了丁香医生的科普，这个成分安全。买了。",
        "成分党表示，这个配方可以。{price}性价比高。",
        "对比了{brand}和舒客，成分差不多，舒客更便宜。",
        "检测报告齐全，成分透明。{price}合理，买了。",
        "研究了{hour}小时，这个性价比最高。",
        "成分表写得清楚，氟含量明确。专业。",
        "知乎大神推荐的，成分没问题。{price}合适。",
        "对比了5个牌子，这个成分最好，价格最合理。"
    ],
    'M06': [
        "直播间看到的，主播说效果好！还有优惠，买了！",
        "包装好高级！功能好多！{price}也不贵，赚了！",
        "功能越多越好，这个有{feature}种功能，值！",
        "{channel}直播间买的，主播推荐，还有赠品。",
        "看着高级，送人也有面子。{price}便宜。",
        "直播间限时优惠，抢到了！功能多，包装好。",
        "主播说孩子用了牙齿变白了，买了试试。",
        "功能多显高级，便宜显精明。这个都有！",
        "{channel}上刷到的，包装好看，功能多，买了。",
        "直播间冲动消费，但确实不错。功能多，孩子喜欢。"
    ],
    'M07': [
        "有没有临床数据？效果怎么追踪？我需要系统性方案。",
        "需要配套刷牙APP和追踪工具。单一牙膏不够。",
        "要最好的，不能有瑕疵。舒客？还需要提升。",
        "我给孩子用的是{brand}，有完整的口腔护理系统。",
        "数据呢？检测报告呢？专业背书呢？",
        "需要医生推荐+数据支撑+配套工具。舒客还差一些。",
        "品质可以，但不是最好的。我会继续寻找更好的。",
        "作为{job}，我对品质要求很高。舒客及格，但不够优秀。",
        "需要系统性管理，不只是牙膏。舒客只是其中一环。",
        "专业度可以，但缺少配套方案。不会作为首选。"
    ],
    'M08': [
        "便宜就行，{price}合适。老牌子，安全。",
        "不讲究，能用就行。{price}便宜，买了。",
        "老人说好用，我就买了。孩子没喊牙疼就行。",
        "{channel}买的，{price}，老牌子。不指望牙膏有多大用。",
        "便宜、安全就行。舒客都符合。",
        "没时间研究，{price}便宜就买了。用着还行。",
        "不追求什么功能，能刷牙就行。{price}合适。",
        "老牌子，价格便宜。孩子用了没蛀牙，够了。",
        "{channel}随手买的，{price}，老牌子。",
        "便宜实惠，老牌子放心。不讲究那么多。"
    ]
}

def generate_nickname():
    """生成随机昵称"""
    surname = random.choice(SURNAMES)
    name = random.choice(FEMALE_NAMES)
    return surname + name

def generate_persona(segment_id, sample_num):
    config = SEGMENT_CONFIG[segment_id]
    segment_rules = SEGMENT_RULES[segment_id]

    nickname = generate_nickname()
    age = random.randint(config['age_range'][0], config['age_range'][1])

    city = random.choice(list(config['cities'].keys()))
    district = random.choice(config['cities'][city])

    occupation = random.choice(config['occupations'])
    income = random.choice(config['income_bands'])

    family_structure = random.choice(config['family_structures'])
    child_age = random.choice(config['child_ages'])
    """
    child_gender = random.choice(['\u7537', '\u5973'])
    child_gender = random.choice(['男', '女'])
    child_gender = random.choice(['鐢?, '濂?])

    child_gender = random.choice(['\u7537', '\u5973'])

    """
    child_gender = random.choice(['\u7537', '\u5973'])

    subtype_list = []
    for subtype_name, count in SUBTYPE_DISTRIBUTION[segment_id].items():
        subtype_list.extend([subtype_name] * count)
    subtype = subtype_list[sample_num - 1] if sample_num <= len(subtype_list) else random.choice(subtype_list)

    subtype_features = SUBTYPE_FEATURES[subtype]

    mindset_profile = {
        "decision_mode": subtype_features['decision_mode'],
        "openness_level": constrained_ordinal_choice(segment_rules['openness_level'], MINDSET_FIELD_SCALES['openness_level']),
        "time_investment": constrained_ordinal_choice(segment_rules['time_investment'], MINDSET_FIELD_SCALES['time_investment']),
        "appearance_sensitivity": constrained_ordinal_choice(segment_rules['appearance_sensitivity'], MINDSET_FIELD_SCALES['appearance_sensitivity']),
        "evidence_sensitivity": constrained_ordinal_choice(segment_rules['evidence_sensitivity'], MINDSET_FIELD_SCALES['evidence_sensitivity']),
        "trend_sensitivity": constrained_ordinal_choice(segment_rules['trend_sensitivity'], MINDSET_FIELD_SCALES['trend_sensitivity']),
        "price_sensitivity": constrained_ordinal_choice(segment_rules['price_sensitivity'], MINDSET_FIELD_SCALES['price_sensitivity'])
    }

    consumption_profile = {
        "core_needs": sample_from_whitelist(segment_rules['core_needs_options'], 3),
        "preferred_channels": sample_from_whitelist(segment_rules['preferred_channels'], 3),
        "trust_trigger": subtype_features['trust_trigger'],
        "rejection_trigger": subtype_features['rejection_trigger'],
        "budget_range": config['budget']
    }

    behavior_profile = {
        "content_habit": sample_from_whitelist(segment_rules['content_habits']),
        "decision_style": sample_from_whitelist(segment_rules['decision_styles']),
        "family_role": sample_from_whitelist(segment_rules['family_roles']),
        "switching_willingness": constrained_ordinal_choice(segment_rules['switching_willingness'], MINDSET_FIELD_SCALES['switching_willingness'])
    }

    feedback_template = random.choice(FEEDBACK_TEMPLATES[segment_id])
    """
    feedback = feedback_template.format(
        price=str(int(extract_budget_floor(config['budget']))),
        high_price=str(int(extract_budget_floor(config['budget'])) * 3 or 60),
        brand=random.choice(['寰峰浗Putzi', '鏃ユ湰鐙帇', '缇庡浗Tom', '鐟炲＋Elmex', '婢虫床Jack']),
        year=random.choice(['涓?, '涓?, '鍥?, '浜?]),
        channel=sample_from_whitelist(segment_rules['preferred_channels']),
        title=random.choice(['鐪佸彛鑵斾富浠?, '涓夌敳鍎跨涓讳换', '绉佺珛鍖婚櫌闄㈤暱', '鍎跨鐗欑涓撳']),
        job=random.choice(['鏃跺皻鏉傚織涓荤紪', '濂緢鍝侀珮绠?, '澶у鏁欐巿', '鎶曡VP']),
        sales=random.choice(['10涓?', '5涓?', '3涓?', '8涓?]),
        rate=random.choice(['98', '96', '95', '97']),
        kol=random.choice(['骞寸硶濡堝', '澶灏廌', '宕旂帀娑?, '涓侀濡堝']),
        fluoride_percent=random.choice(['0.05%', '0.06%', '0.07%', '0.08%']),
        hour=random.choice(['2', '3', '4', '5']),
        feature=random.choice(['3', '4', '5', '6'])
    )

    """
    budget_floor = int(extract_budget_floor(config['budget']))
    feedback = feedback_template.format(
        price=str(budget_floor),
        high_price=str(budget_floor * 3 if budget_floor else 60),
        brand=random.choice(['Putzi', 'Lion', 'Toms', 'Elmex', 'Jack N Jill']),
        year=random.choice(['1', '2', '4', '8']),
        channel=sample_from_whitelist(segment_rules['preferred_channels']),
        title=random.choice(['chief dentist', 'pediatric director', 'private hospital dean', 'children dental expert']),
        job=random.choice(['magazine editor', 'luxury executive', 'professor', 'investment VP']),
        sales=random.choice(['100k', '50k', '30k', '80k']),
        rate=random.choice(['98', '96', '95', '97']),
        kol=random.choice(['Nian Gao Mama', 'Big J Little D', 'Cui Yutao', 'Ding Xiang Mama']),
        fluoride_percent=random.choice(['0.05%', '0.06%', '0.07%', '0.08%']),
        hour=random.choice(['2', '3', '4', '5']),
        feature=random.choice(['3', '4', '5', '6'])
    )

    persona = {
        "sample_id": f"{segment_id}-{sample_num:02d}",
        "segment_id": segment_id,
        "segment_name": config['name'],
        "basic_profile": {
            "nickname": nickname,
            "age": age,
            "city": city,
            "district": district,
            "city_tier": config['city_tier'],
            "marital_status": "\u5df2\u5a5a",
            "marital_status": "宸插",
            "child_age_stage": child_age,
            "marital_status": "\u5df2\u5a5a",
            "child_gender": child_gender,
            "occupation": occupation,
            "household_income_band": income,
            "family_structure": family_structure
        },
        "mindset_profile": mindset_profile,
        "consumption_profile": consumption_profile,
        "behavior_profile": behavior_profile,
        "expression_profile": {
            "tone_style": subtype_features['tone'],
            "likely_quote": subtype_features['quote']
        },
        "review_focus": subtype_features['review_focus'],
        "subtype": subtype,
        "product_rating": int(config['rating']),
        "purchase_decision": config['decision'],
        "simulated_feedback": feedback
    }

    return persona
    """生成单个人物样本"""
    config = SEGMENT_CONFIG[segment_id]
    
    # 基本信息
    nickname = generate_nickname()
    age = random.randint(config['age_range'][0], config['age_range'][1])
    
    # 城市和区域
    city = random.choice(list(config['cities'].keys()))
    district = random.choice(config['cities'][city])
    
    # 职业和收入
    occupation = random.choice(config['occupations'])
    income = random.choice(config['income_bands'])
    
    # 家庭结构和孩子
    family_structure = random.choice(config['family_structures'])
    child_age = random.choice(config['child_ages'])
    child_gender = random.choice(['男', '女'])
    
    # 子型分配
    subtype_list = []
    for subtype, count in SUBTYPE_DISTRIBUTION[segment_id].items():
        subtype_list.extend([subtype] * count)
    subtype = subtype_list[sample_num - 1] if sample_num <= len(subtype_list) else random.choice(subtype_list)
    
    # 子型特征
    subtype_features = SUBTYPE_FEATURES[subtype]
    
    # 生成模拟反馈
    feedback_template = random.choice(FEEDBACK_TEMPLATES[segment_id])
    # 替换模板变量
    feedback = feedback_template.format(
        price=config['budget'].split('元')[0],
        high_price=str(int(config['budget'].split('-')[0].replace('元', '').strip()) * 3) if '-' in config['budget'] else '60',
        brand=random.choice(['德国Putzi', '日本狮王', '美国Tom', '瑞士Elmex', '澳洲Jack']),
        year=random.choice(['两', '三', '四', '五']),
        channel=random.choice(['Ole精品超市', 'CitySuper', '天猫国际', '京东', '小红书', '抖音直播间', '当地超市']),
        title=random.choice(['省口腔主任', '三甲儿科主任', '私立医院院长', '儿童牙科专家']),
        job=random.choice(['时尚杂志主编', '奢侈品高管', '大学教授', '投行VP']),
        sales=random.choice(['10万+', '5万+', '3万+', '8万+']),
        rate=random.choice(['98', '96', '95', '97']),
        kol=random.choice(['年糕妈妈', '大J小D', '崔玉涛', '丁香妈妈']),
        fluoride_percent=random.choice(['0.05%', '0.06%', '0.07%', '0.08%']),
        hour=random.choice(['2', '3', '4', '5']),
        feature=random.choice(['3', '4', '5', '6'])
    )
    
    # 构建人物样本
    persona = {
        "sample_id": f"{segment_id}-{sample_num:02d}",
        "segment_id": segment_id,
        "segment_name": config['name'],
        "basic_profile": {
            "nickname": nickname,
            "age": age,
            "city": city,
            "district": district,
            "city_tier": config['city_tier'],
            "marital_status": "已婚",
            "child_age_stage": child_age,
            "child_gender": child_gender,
            "occupation": occupation,
            "household_income_band": income,
            "family_structure": family_structure
        },
        "mindset_profile": {
            "decision_mode": subtype_features['decision_mode'],
            "openness_level": random.choice(['low', 'medium', 'high']),
            "time_investment": random.choice(['very_low', 'low', 'medium', 'high', 'very_high']),
            "appearance_sensitivity": random.choice(['very_low', 'low', 'medium', 'high', 'very_high']),
            "evidence_sensitivity": random.choice(['very_low', 'low', 'medium', 'high', 'very_high']),
            "trend_sensitivity": random.choice(['very_low', 'low', 'medium', 'high', 'very_high']),
            "price_sensitivity": random.choice(['very_low', 'low', 'medium', 'high', 'very_high'])
        },
        "consumption_profile": {
            "core_needs": random.sample(['防蛀效果', '价格实惠', '品牌信任', '成分安全', '孩子喜欢', '颜值包装', '老牌子', '医生推荐'], 3),
            "preferred_channels": random.sample(['天猫', '京东', '小红书', '抖音', '超市', '母婴店', '直播间', '牙医推荐'], 3),
            "trust_trigger": subtype_features['trust_trigger'],
            "rejection_trigger": subtype_features['rejection_trigger'],
            "budget_range": config['budget']
        },
        "behavior_profile": {
            "content_habit": random.choice(['小红书种草', '超市货架', '牙医建议', '直播间', '知乎研究']),
            "decision_style": random.choice(['理性分析型', '情绪直觉型', '货架消费者', '效率至上']),
            "family_role": random.choice(['决策者', '主要购买者', '品质把关人']),
            "switching_willingness": random.choice(['very_low', 'low', 'medium', 'high', 'very_high'])
        },
        "expression_profile": {
            "tone_style": subtype_features['tone'],
            "likely_quote": subtype_features['quote']
        },
        "review_focus": subtype_features['review_focus'],
        "subtype": subtype,
        "product_rating": int(config['rating']),
        "purchase_decision": config['decision'],
        "simulated_feedback": feedback
    }
    
    return persona

def generate_all_personas():
    """生成所有200个人物样本"""
    all_samples = []
    
    for segment_id in ['M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08']:
        for i in range(1, 26):
            persona = generate_persona(segment_id, i)
            all_samples.append(persona)
    
    return all_samples

def generate_report(samples):
    """生成统计报告"""
    report = {
        "metadata": {
            "system": "数字妈妈体验官系统",
            "version": "1.0",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_samples": len(samples),
            "segments": 8,
            "samples_per_segment": 25
        },
        "segment_summary": {},
        "subtype_distribution": {},
        "age_distribution": {},
        "city_distribution": {},
        "occupation_distribution": {},
        "rating_distribution": {}
    }
    
    # 统计各人群
    for sample in samples:
        seg_id = sample['segment_id']
        seg_name = sample['segment_name']
        
        if seg_id not in report['segment_summary']:
            report['segment_summary'][seg_id] = {
                "name": seg_name,
                "count": 0,
                "avg_rating": 0,
                "subtypes": {}
            }
        
        report['segment_summary'][seg_id]['count'] += 1
        report['segment_summary'][seg_id]['avg_rating'] += sample['product_rating']
        
        # 子型统计
        subtype = sample['subtype']
        if subtype not in report['segment_summary'][seg_id]['subtypes']:
            report['segment_summary'][seg_id]['subtypes'][subtype] = 0
        report['segment_summary'][seg_id]['subtypes'][subtype] += 1
        
        # 全局子型统计
        if subtype not in report['subtype_distribution']:
            report['subtype_distribution'][subtype] = 0
        report['subtype_distribution'][subtype] += 1
        
        # 年龄分布
        age = sample['basic_profile']['age']
        age_group = f"{age//5*5}-{(age//5+1)*5-1}岁"
        if age_group not in report['age_distribution']:
            report['age_distribution'][age_group] = 0
        report['age_distribution'][age_group] += 1
        
        # 城市分布
        city = sample['basic_profile']['city']
        if city not in report['city_distribution']:
            report['city_distribution'][city] = 0
        report['city_distribution'][city] += 1
        
        # 评分分布
        rating = sample['product_rating']
        if rating not in report['rating_distribution']:
            report['rating_distribution'][rating] = 0
        report['rating_distribution'][rating] += 1
    
    # 计算平均评分
    for seg_id in report['segment_summary']:
        report['segment_summary'][seg_id]['avg_rating'] = round(
            report['segment_summary'][seg_id]['avg_rating'] / report['segment_summary'][seg_id]['count'], 1
        )
    
    return report

def main():
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    """主函数"""
    print("=" * 60)
    print("数字妈妈体验官人物库生成器")
    print("=" * 60)
    
    # 生成所有样本
    print("\n正在生成200个人物样本...")
    samples = generate_all_personas()
    
    # 保存完整数据
    output_file = "persona_samples_complete.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "system": "数字妈妈体验官系统",
                "version": "1.0",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_samples": 200,
                "segments": 8,
                "samples_per_segment": 25
            },
            "samples": samples
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已保存到: {output_file}")
    
    # 生成统计报告
    print("\n正在生成统计报告...")
    report = generate_report(samples)
    
    # 保存报告
    report_file = "persona_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 报告已保存到: {report_file}")
    
    # 打印报告摘要
    print("\n" + "=" * 60)
    print("生成报告摘要")
    print("=" * 60)
    
    print(f"\n总样本数: {report['metadata']['total_samples']}")
    print(f"人群分类: {report['metadata']['segments']}个")
    print(f"每类样本: {report['metadata']['samples_per_segment']}个")
    
    print("\n【各人群概览】")
    for seg_id, seg_data in report['segment_summary'].items():
        print(f"\n{seg_id} - {seg_data['name']}")
        print(f"  样本数: {seg_data['count']}")
        print(f"  平均评分: {seg_data['avg_rating']}")
        print(f"  子型分布: {seg_data['subtypes']}")
    
    print("\n【子型分布统计】")
    for subtype, count in sorted(report['subtype_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {subtype}: {count}人")
    
    print("\n【年龄分布】")
    for age_group, count in sorted(report['age_distribution'].items()):
        print(f"  {age_group}: {count}人")
    
    print("\n【评分分布】")
    for rating, count in sorted(report['rating_distribution'].items()):
        print(f"  {rating}分: {count}人")
    
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
