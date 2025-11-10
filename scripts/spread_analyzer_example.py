"""
牌型分析器示例

展示如何分析牌型、生成RAG查询、并生成解牌
"""

import json
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 牌型配置
SPREAD_CONFIGS = {
    "three_card": {
        "name": "三牌阵",
        "name_en": "Three Card Spread",
        "num_positions": 3,
        "positions": [
            {
                "number": 1,
                "name": "past",
                "name_cn": "过去",
                "description": "过去的影响和背景"
            },
            {
                "number": 2,
                "name": "present",
                "name_cn": "现在",
                "description": "当前状况和情况"
            },
            {
                "number": 3,
                "name": "future",
                "name_cn": "未来",
                "description": "未来趋势和结果"
            }
        ]
    },
    "celtic_cross": {
        "name": "凯尔特十字",
        "name_en": "Celtic Cross",
        "num_positions": 10,
        "positions": [
            {
                "number": 1,
                "name": "cover",
                "name_cn": "覆盖",
                "description": "覆盖Significator的牌，代表当前情况"
            },
            {
                "number": 2,
                "name": "crossing",
                "name_cn": "交叉",
                "description": "横跨第一张牌的牌，代表阻碍或帮助"
            },
            {
                "number": 3,
                "name": "basis",
                "name_cn": "基础",
                "description": "位于Significator下方的牌，代表基础或根源"
            },
            {
                "number": 4,
                "name": "behind",
                "name_cn": "后方",
                "description": "代表过去的影响"
            },
            {
                "number": 5,
                "name": "crowned",
                "name_cn": "加冕",
                "description": "代表可能的结果或目标"
            },
            {
                "number": 6,
                "name": "before",
                "name_cn": "前方",
                "description": "代表即将到来的未来"
            },
            {
                "number": 7,
                "name": "self",
                "name_cn": "自我",
                "description": "代表问卜者自身"
            },
            {
                "number": 8,
                "name": "environment",
                "name_cn": "环境",
                "description": "代表周围环境和他人影响"
            },
            {
                "number": 9,
                "name": "hopes_and_fears",
                "name_cn": "希望与恐惧",
                "description": "代表问卜者的希望和恐惧"
            },
            {
                "number": 10,
                "name": "outcome",
                "name_cn": "结果",
                "description": "代表最终结果"
            }
        ]
    }
}


class SpreadAnalyzer:
    """牌型分析器"""
    
    def __init__(self):
        self.spread_configs = SPREAD_CONFIGS
    
    def analyze_spread_structure(
        self, 
        cards: List[Dict[str, Any]], 
        spread_type: str
    ) -> Dict[str, Any]:
        """
        分析牌型结构
        
        Args:
            cards: 抽出的牌列表，每张牌包含：
                - card_name: 牌名
                - card_number: 编号
                - suit: 花色
                - arcana: 大/小阿卡纳
                - is_reversed: 是否逆位（可选）
            spread_type: 牌型类型
        
        Returns:
            分析结果字典
        """
        if spread_type not in self.spread_configs:
            raise ValueError(f"不支持的牌型: {spread_type}")
        
        spread_config = self.spread_configs[spread_type]
        
        if len(cards) != spread_config["num_positions"]:
            logger.warning(
                f"牌的数量({len(cards)})与牌型要求({spread_config['num_positions']})不匹配"
            )
        
        # 为每张牌分配位置
        analyzed_cards = []
        for i, card in enumerate(cards):
            position_num = i + 1
            position_info = spread_config["positions"][i] if i < len(spread_config["positions"]) else None
            
            analyzed_card = {
                "card_name": card.get("card_name", ""),
                "card_name_cn": card.get("card_name_cn", ""),
                "card_number": card.get("card_number", 0),
                "suit": card.get("suit", ""),
                "arcana": card.get("arcana", ""),
                "position": position_num,
                "position_name": position_info["name"] if position_info else f"position_{position_num}",
                "position_name_cn": position_info["name_cn"] if position_info else f"位置{position_num}",
                "position_description": position_info["description"] if position_info else "",
                "is_reversed": card.get("is_reversed", False),
                "order": i + 1
            }
            analyzed_cards.append(analyzed_card)
        
        # 统计分析
        major_count = sum(1 for c in analyzed_cards if c["arcana"] == "major")
        minor_count = sum(1 for c in analyzed_cards if c["arcana"] == "minor")
        reversed_count = sum(1 for c in analyzed_cards if c["is_reversed"])
        
        suits_distribution = {}
        for card in analyzed_cards:
            if card["suit"] != "major":
                suits_distribution[card["suit"]] = suits_distribution.get(card["suit"], 0) + 1
        
        # 识别模式
        patterns = []
        if major_count > len(analyzed_cards) / 2:
            patterns.append("大量大阿卡纳出现，表示重要的生活转折点")
        if reversed_count > len(analyzed_cards) / 2:
            patterns.append("大量逆位牌出现，表示需要特别注意的阻碍")
        if len(set([c["card_name"] for c in analyzed_cards])) < len(analyzed_cards):
            patterns.append("有重复的牌出现，表示该主题的重要性")
        
        return {
            "spread_type": spread_type,
            "spread_info": {
                "name": spread_config["name"],
                "name_en": spread_config["name_en"],
                "num_positions": spread_config["num_positions"],
                "description": f"{spread_config['name']}，{spread_config['num_positions']}张牌布局"
            },
            "cards": analyzed_cards,
            "analysis": {
                "major_arcana_count": major_count,
                "minor_arcana_count": minor_count,
                "suits_distribution": suits_distribution,
                "reversed_count": reversed_count,
                "patterns": patterns
            }
        }
    
    def generate_position_queries(
        self, 
        spread_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        为每个位置生成RAG查询
        
        Args:
            spread_analysis: 牌型分析结果
        
        Returns:
            查询列表
        """
        queries = []
        spread_type = spread_analysis["spread_type"]
        spread_name = spread_analysis["spread_info"]["name"]
        
        for card_info in spread_analysis["cards"]:
            position = card_info["position"]
            position_name = card_info["position_name"]
            position_name_cn = card_info["position_name_cn"]
            
            # 生成中英文查询
            query_cn = f"{spread_name}牌型中，Position {position} {position_name_cn}（{position_name}）位置的含义是什么？如何解牌？"
            query_en = f"What is the meaning of Position {position} {position_name} in {spread_type} spread? How to interpret it?"
            
            queries.append({
                "position": position,
                "position_name": position_name,
                "position_name_cn": position_name_cn,
                "query": query_cn,
                "query_en": query_en,
                "card_name": card_info["card_name"]
            })
        
        return queries
    
    def generate_interpretation_prompt(
        self,
        question: str,
        spread_analysis: Dict[str, Any],
        position_meanings: Dict[int, Dict[str, Any]],
        card_meanings: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        生成解牌Prompt
        
        Args:
            question: 用户问题
            spread_analysis: 牌型分析结果
            position_meanings: 位置含义（从RAG获取）
            card_meanings: 牌的含义（从数据库获取）
        
        Returns:
            Prompt字符串
        """
        spread_info = spread_analysis["spread_info"]
        cards = spread_analysis["cards"]
        
        # 构建位置含义文本
        position_meanings_text = "\n\n".join([
            f"Position {pos}: {spread_analysis['cards'][pos-1]['position_name_cn']}\n"
            f"含义: {meanings.get('meaning', '')}\n"
            f"来源: {', '.join([c.get('source', '') for c in meanings.get('citations', [])])}"
            for pos, meanings in position_meanings.items()
        ])
        
        # 构建牌的含义文本
        card_meanings_text = "\n\n".join([
            f"{card['card_name']} ({card['card_name_cn']}):\n"
            f"正位: {card_meanings.get(card['card_name'], {}).get('upright', '')}\n"
            f"逆位: {card_meanings.get(card['card_name'], {}).get('reversed', '')}"
            for card in cards
        ])
        
        # 构建牌和位置信息
        cards_with_positions = "\n".join([
            f"Position {card['position']} ({card['position_name_cn']}): "
            f"{card['card_name']} ({'逆位' if card['is_reversed'] else '正位'})"
            for card in cards
        ])
        
        prompt = f"""
你是一个专业的塔罗占卜师。请基于以下信息生成完整的解牌。

**用户问题**：
{question}

**牌型信息**：
- 牌型：{spread_info['name']} ({spread_info['name_en']})
- 描述：{spread_info['description']}

**抽出的牌和位置**：
{cards_with_positions}

**位置含义**（从RAG获取）：
{position_meanings_text}

**每张牌的含义**（从数据库获取）：
{card_meanings_text}

**任务**：
1. 结合每张牌的含义和位置含义，生成该位置的解牌
2. 考虑牌的正位/逆位
3. 分析牌之间的关联和组合
4. 生成整体解读

请用JSON格式输出，包含以下字段：
- reading_summary: 整体摘要
- position_interpretations: 每个位置的解牌列表
- overall_interpretation: 整体解牌
- references: 引用来源列表
"""
        
        return prompt


# 使用示例
def example_usage():
    """使用示例"""
    
    analyzer = SpreadAnalyzer()
    
    # 示例：三牌阵
    cards = [
        {
            "card_name": "The Fool",
            "card_name_cn": "愚人",
            "card_number": 0,
            "suit": "major",
            "arcana": "major",
            "is_reversed": False
        },
        {
            "card_name": "The Magician",
            "card_name_cn": "魔术师",
            "card_number": 1,
            "suit": "major",
            "arcana": "major",
            "is_reversed": False
        },
        {
            "card_name": "The World",
            "card_name_cn": "世界",
            "card_number": 21,
            "suit": "major",
            "arcana": "major",
            "is_reversed": False
        }
    ]
    
    # 1. 分析牌型
    spread_analysis = analyzer.analyze_spread_structure(cards, "three_card")
    print("牌型分析结果:")
    print(json.dumps(spread_analysis, indent=2, ensure_ascii=False))
    
    # 2. 生成位置查询
    queries = analyzer.generate_position_queries(spread_analysis)
    print("\n生成的RAG查询:")
    for query in queries:
        print(f"  Position {query['position']}: {query['query']}")
    
    # 3. 生成解牌Prompt（示例，实际需要从RAG和数据库获取数据）
    position_meanings = {
        1: {
            "meaning": "过去的影响，代表背景情况",
            "citations": [{"source": "PKT"}]
        },
        2: {
            "meaning": "当前状况，代表现在的情况",
            "citations": [{"source": "PKT"}]
        },
        3: {
            "meaning": "未来趋势，代表可能的结果",
            "citations": [{"source": "PKT"}]
        }
    }
    
    card_meanings = {
        "The Fool": {
            "upright": "新的开始，冒险精神",
            "reversed": "鲁莽，缺乏计划"
        },
        "The Magician": {
            "upright": "技能，行动力",
            "reversed": "缺乏意志力"
        },
        "The World": {
            "upright": "完成，成就",
            "reversed": "未完成，缺乏成就感"
        }
    }
    
    prompt = analyzer.generate_interpretation_prompt(
        question="我的事业发展如何？",
        spread_analysis=spread_analysis,
        position_meanings=position_meanings,
        card_meanings=card_meanings
    )
    
    print("\n生成的解牌Prompt:")
    print(prompt)


if __name__ == "__main__":
    example_usage()










