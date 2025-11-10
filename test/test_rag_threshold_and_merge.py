"""
测试RAG优化：调整阈值和问题融合
1. 测试1：调整阈值（提高卡牌查询阈值到0.6）
2. 测试2：融合单张牌的查询（将2-3个相关查询合并）
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import ReadingService
from app.models.schemas import UserProfileCreate
from app.core.database import get_supabase_service
from app.services.rag import rag_service


def analyze_rag_duplicates(rag_queries):
    """分析RAG查询的重复chunk情况"""
    chunk_usage = Counter()
    query_to_chunks = {}
    
    for query_record in rag_queries:
        query = query_record.get('query', '')
        query_type = query_record.get('type', 'unknown')
        citations = query_record.get('result', {}).get('citations', [])
        
        chunk_ids = []
        for citation in citations:
            chunk_id = citation.get('chunk_id', '')
            if chunk_id:
                chunk_ids.append(chunk_id)
                chunk_usage[chunk_id] += 1
        
        if chunk_ids:
            query_to_chunks[query] = {
                'type': query_type,
                'chunk_ids': chunk_ids,
                'chunk_count': len(chunk_ids)
            }
    
    # 找出重复使用的chunks
    duplicate_chunks = {chunk_id: count for chunk_id, count in chunk_usage.items() if count > 1}
    
    # 统计信息
    total_queries = len(query_to_chunks)
    total_unique_chunks = len(chunk_usage)
    total_chunk_uses = sum(chunk_usage.values())
    duplicate_count = len(duplicate_chunks)
    duplicate_uses = sum(duplicate_chunks.values())
    
    # 计算重复率
    if total_chunk_uses > 0:
        duplicate_rate = (duplicate_uses - duplicate_count) / total_chunk_uses * 100
    else:
        duplicate_rate = 0
    
    return {
        'total_queries': total_queries,
        'total_unique_chunks': total_unique_chunks,
        'total_chunk_uses': total_chunk_uses,
        'duplicate_chunks': duplicate_chunks,
        'duplicate_count': duplicate_count,
        'duplicate_uses': duplicate_uses,
        'duplicate_rate': duplicate_rate,
        'query_to_chunks': query_to_chunks,
        'chunk_usage': dict(chunk_usage)
    }


def get_first_test_cards():
    """从第一次测试结果中获取牌面信息"""
    # 从JSON文件读取第一次测试的reading_id
    result_file = Path(__file__).parent / "result" / "rag_optimization_test_20251107_214927.json"
    
    if not result_file.exists():
        print(f"❌ 未找到第一次测试结果文件: {result_file}")
        return None
    
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    reading_id = data.get('reading_result', {}).get('reading_id')
    if not reading_id:
        print("❌ 第一次测试结果中没有reading_id")
        return None
    
    print(f"📋 使用reading_id: {reading_id}")
    
    # 从数据库读取牌面信息
    supabase = get_supabase_service()
    
    # 先读取reading_cards
    cards_data = supabase.table('reading_cards').select('*').eq('reading_id', reading_id).order('position_order').execute()
    
    if not cards_data.data:
        print(f"❌ 未找到reading_id={reading_id}的牌面信息")
        return None
    
    # 获取每张牌的详细信息
    cards = []
    for card_record in cards_data.data:
        card_id = card_record.get('card_id')
        # 查询tarot_cards表获取牌的信息
        tarot_card_data = supabase.table('tarot_cards').select('*').eq('id', card_id).execute()
        tarot_card = tarot_card_data.data[0] if tarot_card_data.data else {}
        
        cards.append({
            'card_id': card_id,
            'card_name_en': tarot_card.get('card_name_en', ''),
            'card_name_cn': tarot_card.get('card_name_cn', ''),
            'position': card_record.get('position', ''),
            'position_order': card_record.get('position_order', 0),
            'is_reversed': card_record.get('is_reversed', False)
        })
    
    print(f"\n✅ 获取到第一次测试的牌面信息:")
    for card in cards:
        print(f"  {card['position_order']}. {card['position']}: {card['card_name_en']} ({card['card_name_cn']}) {'[逆位]' if card['is_reversed'] else ''}")
    
    return cards


async def test_adjusted_threshold(cards, user_profile, question):
    """测试1：调整阈值（提高卡牌查询阈值到0.6）"""
    print("\n" + "="*80)
    print("测试1: 调整阈值（卡牌查询阈值提高到0.6）")
    print("="*80)
    
    async def modified_retrieve_card_info(cards, rag_queries=None):
        """修改版本的卡牌信息检索，使用0.6阈值"""
        from app.services.tarot.card_selection import SelectedCard
        from app.services.rag import rag_service
        import asyncio
        
        card_info = {}
        if rag_queries is None:
            rag_queries = []
        
        async def retrieve_single_card_enhanced(card):
            card_queries = []
            queries = []
            
            # 构建查询（与原版相同）
            queries.append({
                'query': f"{card.card_name_en} tarot card meaning divinatory meaning",
                'type': 'basic_meaning'
            })
            queries.append({
                'query': f"{card.card_name_en} tarot card description image visual appearance",
                'type': 'visual_description'
            })
            if card.is_reversed:
                queries.append({
                    'query': f"{card.card_name_en} tarot card reversed meaning divinatory reversed",
                    'type': 'reversed_meaning'
                })
            else:
                queries.append({
                    'query': f"{card.card_name_en} tarot card upright meaning divinatory upright",
                    'type': 'upright_meaning'
                })
            if card.position:
                queries.append({
                    'query': f"{card.card_name_en} tarot card {card.position} position meaning interpretation",
                    'type': 'position_meaning'
                })
            queries.append({
                'query': f"{card.card_name_en} tarot card psychological meaning psychological interpretation",
                'type': 'psychological_meaning'
            })
            
            async def execute_query(query_info):
                try:
                    # 使用0.6阈值
                    rag_result = await rag_service.answer_query(
                        query_info['query'], 
                        top_k=5,
                        min_similarity=0.6  # 提高到0.6
                    )
                    return {
                        'query': query_info['query'],
                        'type': query_info['type'],
                        'card_id': card.card_id,
                        'card_name_en': card.card_name_en,
                        'result': {
                            'text': rag_result.get('text', ''),
                            'citations': rag_result.get('citations', []),
                            'debug': rag_result.get('debug', {})
                        }
                    }
                except Exception as e:
                    return {
                        'query': query_info['query'],
                        'type': query_info['type'],
                        'card_id': card.card_id,
                        'card_name_en': card.card_name_en,
                        'error': str(e),
                        'result': None
                    }
            
            query_tasks = [execute_query(q) for q in queries]
            query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
            
            for result in query_results:
                if not isinstance(result, Exception):
                    card_queries.append(result)
            
            all_texts = []
            all_citations = []
            for result in card_queries:
                if result.get('result'):
                    text = result['result'].get('text', '')
                    if text:
                        all_texts.append(f"[{result['type']}] {text}")
                    citations = result['result'].get('citations', [])
                    all_citations.extend(citations)
            
            combined_text = "\n\n".join(all_texts)
            seen_chunk_ids = set()
            unique_citations = []
            for citation in all_citations:
                chunk_id = citation.get('chunk_id', '')
                if chunk_id and chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    unique_citations.append(citation)
            
            return card.card_id, {
                'card_name_en': card.card_name_en,
                'card_name_cn': card.card_name_cn,
                'position': card.position,
                'is_reversed': card.is_reversed,
                'rag_text': combined_text,
                'citations': unique_citations,
                'query_count': len(card_queries),
            }, card_queries
        
        tasks = [retrieve_single_card_enhanced(card) for card in cards]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if not isinstance(result, Exception):
                card_id, card_data, query_records = result
                card_info[card_id] = card_data
                rag_queries.extend(query_records)
        
        return card_info
    
    start_time = time.time()
    
    try:
        # 使用相同的牌面创建占卜（需要修改reading_service以支持固定牌面）
        # 这里我们只测试RAG查询部分
        from app.services.tarot.card_selection import SelectedCard
        
        # 需要从数据库获取完整的牌信息
        supabase = get_supabase_service()
        selected_cards = []
        for card_data in cards:
            # 获取牌的完整信息
            tarot_card_data = supabase.table('tarot_cards').select('*').eq('id', card_data['card_id']).execute()
            tarot_card = tarot_card_data.data[0] if tarot_card_data.data else {}
            
            selected_cards.append(SelectedCard(
                card_id=card_data['card_id'],
                card_name_en=card_data['card_name_en'],
                card_name_cn=card_data['card_name_cn'],
                suit=tarot_card.get('suit', ''),
                card_number=tarot_card.get('card_number', 0),
                arcana=tarot_card.get('arcana', ''),
                position=card_data['position'],
                position_order=card_data['position_order'],
                position_description=None,
                is_reversed=card_data['is_reversed']
            ))
        
        rag_queries = []
        card_info = await modified_retrieve_card_info(selected_cards, rag_queries)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"\n✅ 测试1完成")
        print(f"总耗时: {elapsed_ms}ms")
        
        if rag_queries:
            analysis = analyze_rag_duplicates(rag_queries)
            print(f"\nRAG重复率分析:")
            print(f"  总查询数: {analysis['total_queries']}")
            print(f"  唯一文档块数: {analysis['total_unique_chunks']}")
            print(f"  重复率: {analysis['duplicate_rate']:.2f}%")
            
            return analysis, elapsed_ms, rag_queries
        
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


async def test_merged_queries(cards, user_profile, question, spread_type="three_card"):
    """测试2：融合单张牌的查询（将2-3个相关查询合并）+ 占卜方法和牌型分析"""
    print("\n" + "="*80)
    print("测试2: 融合单张牌的查询（2-3个相关查询合并）+ 占卜方法和牌型分析")
    print("="*80)
    
    from app.services.tarot.card_selection import SelectedCard
    from app.services.rag import rag_service
    import asyncio
    
    # 将cards转换为SelectedCard对象
    supabase = get_supabase_service()
    selected_cards = []
    for card_data in cards:
        # 获取牌的完整信息
        tarot_card_data = supabase.table('tarot_cards').select('*').eq('id', card_data['card_id']).execute()
        tarot_card = tarot_card_data.data[0] if tarot_card_data.data else {}
        
        selected_cards.append(SelectedCard(
            card_id=card_data['card_id'],
            card_name_en=card_data['card_name_en'],
            card_name_cn=card_data['card_name_cn'],
            suit=tarot_card.get('suit', ''),
            card_number=tarot_card.get('card_number', 0),
            arcana=tarot_card.get('arcana', ''),
            position=card_data['position'],
            position_order=card_data['position_order'],
            position_description=None,
            is_reversed=card_data['is_reversed']
        ))
    
    card_info = {}
    rag_queries = []
    
    async def retrieve_single_card_merged(card):
        """融合版本的卡牌信息检索"""
        card_queries = []
        
        # 融合策略：将相关查询合并（进一步融合）
        # 1. 基本含义 + 正位/逆位含义 + 花色/元素含义（合并）
        # 2. 视觉描述（单独）
        # 3. 位置含义 + 心理含义（合并）
        
        merged_queries = []
        
        # 根据卡牌的花色确定元素
        suit_to_element = {
            'swords': 'air element thought',
            'wands': 'fire element will',
            'cups': 'water element emotion',
            'pentacles': 'earth element material'
        }
        element_desc = suit_to_element.get(card.suit.lower(), 'element')
        
        # 合并1：基本含义 + 正位/逆位 + 花色/元素含义
        if card.is_reversed:
            merged_queries.append({
                'query': f"{card.card_name_en} tarot card meaning divinatory meaning reversed meaning {element_desc} suit meaning interpretation",
                'type': 'basic_reversed_suit_meaning'
            })
        else:
            merged_queries.append({
                'query': f"{card.card_name_en} tarot card meaning divinatory meaning upright meaning {element_desc} suit meaning interpretation",
                'type': 'basic_upright_suit_meaning'
            })
        
        # 单独查询：视觉描述
        merged_queries.append({
            'query': f"{card.card_name_en} tarot card description image visual appearance",
            'type': 'visual_description'
        })
        
        # 合并2：位置含义 + 心理含义
        if card.position:
            merged_queries.append({
                'query': f"{card.card_name_en} tarot card {card.position} position meaning psychological meaning interpretation",
                'type': 'position_and_psychological_meaning'
            })
        else:
            merged_queries.append({
                'query': f"{card.card_name_en} tarot card psychological meaning psychological interpretation",
                'type': 'psychological_meaning'
            })
        
        async def execute_query(query_info):
            try:
                # 对于融合查询，使用更大的top_k值（10）以获取更多chunk
                # 对于单独的查询（如visual_description），使用较小的top_k（5）
                top_k_value = 10 if query_info['type'] in ['basic_upright_suit_meaning', 'basic_reversed_suit_meaning', 'position_and_psychological_meaning'] else 5
                
                rag_result = await rag_service.answer_query(
                    query_info['query'], 
                    top_k=top_k_value,
                    min_similarity=0.5  # 保持0.5阈值
                )
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'card_id': card.card_id,
                    'card_name_en': card.card_name_en,
                    'result': {
                        'text': rag_result.get('text', ''),
                        'citations': rag_result.get('citations', []),
                        'debug': rag_result.get('debug', {})
                    }
                }
            except Exception as e:
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'card_id': card.card_id,
                    'card_name_en': card.card_name_en,
                    'error': str(e),
                    'result': None
                }
        
        query_tasks = [execute_query(q) for q in merged_queries]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        for result in query_results:
            if not isinstance(result, Exception):
                card_queries.append(result)
        
        all_texts = []
        all_citations = []
        for result in card_queries:
            if result.get('result'):
                text = result['result'].get('text', '')
                if text:
                    all_texts.append(f"[{result['type']}] {text}")
                citations = result['result'].get('citations', [])
                all_citations.extend(citations)
        
        combined_text = "\n\n".join(all_texts)
        seen_chunk_ids = set()
        unique_citations = []
        for citation in all_citations:
            chunk_id = citation.get('chunk_id', '')
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                unique_citations.append(citation)
        
        return card.card_id, {
            'card_name_en': card.card_name_en,
            'card_name_cn': card.card_name_cn,
            'position': card.position,
            'is_reversed': card.is_reversed,
            'rag_text': combined_text,
            'citations': unique_citations,
            'query_count': len(card_queries),
        }, card_queries
    
    start_time = time.time()
    
    # 1. 检索卡牌信息（融合查询）
    tasks = [retrieve_single_card_merged(card) for card in selected_cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if not isinstance(result, Exception):
            card_id, card_data, query_records = result
            card_info[card_id] = card_data
            rag_queries.extend(query_records)
    
    # 2. 检索占卜方法信息
    async def retrieve_spread_method():
        """检索占卜方法信息"""
        spread_queries = []
        queries = []
        
        queries.append({
            'query': f"{spread_type} spread tarot divination method how to use steps",
            'type': 'method_steps'
        })
        queries.append({
            'query': f"{spread_type} spread tarot card positions meaning interpretation",
            'type': 'position_interpretation'
        })
        queries.append({
            'query': f"{spread_type} spread tarot psychological approach interpretation",
            'type': 'psychological_background'
        })
        queries.append({
            'query': f"{spread_type} spread tarot traditional divination method ancient celtic",
            'type': 'traditional_method'
        })
        
        async def execute_query(query_info):
            try:
                rag_result = await rag_service.answer_query(
                    query_info['query'], 
                    top_k=5,
                    min_similarity=0.25  # 占卜方法查询使用较低阈值
                )
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'spread_type': spread_type,
                    'result': {
                        'text': rag_result.get('text', ''),
                        'citations': rag_result.get('citations', []),
                        'debug': rag_result.get('debug', {})
                    }
                }
            except Exception as e:
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'spread_type': spread_type,
                    'error': str(e),
                    'result': None
                }
        
        query_tasks = [execute_query(q) for q in queries]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        for result in query_results:
            if not isinstance(result, Exception):
                spread_queries.append(result)
        
        return spread_queries
    
    # 3. 检索牌之间的关系和模式信息
    async def retrieve_card_relationships():
        """检索牌之间的关系和模式信息"""
        relationship_queries = []
        queries = []
        
        card_names = [card.card_name_en for card in selected_cards]
        reversed_count = sum(1 for card in selected_cards if card.is_reversed)
        
        # 分析牌的特征
        suits = [card.suit for card in selected_cards]
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # 构建查询
        if len(set(card_names)) < len(card_names):
            queries.append({
                'query': f"tarot card same cards repeated meaning {', '.join(card_names)}",
                'type': 'same_cards'
            })
        
        # 数字模式
        queries.append({
            'query': f"tarot card number patterns same numbers sequences in spread {', '.join(card_names)}",
            'type': 'number_patterns'
        })
        
        # 花色分布
        suit_dist = ', '.join([f"{suit}" for suit in suit_counts.keys()])
        queries.append({
            'query': f"tarot card suit distribution element balance {suit_dist} in spread",
            'type': 'suit_distribution'
        })
        
        # 逆位模式
        if reversed_count > 0:
            queries.append({
                'query': f"tarot reversed cards pattern meaning {reversed_count} reversed cards in spread interpretation",
                'type': 'reversed_pattern'
            })
        
        # 牌之间的关系
        position_info = ', '.join([f"{card.card_name_en} ({card.position})" for card in selected_cards])
        queries.append({
            'query': f"tarot card relationships sequence meaning {position_info}",
            'type': 'card_relationships'
        })
        
        async def execute_query(query_info):
            try:
                rag_result = await rag_service.answer_query(
                    query_info['query'], 
                    top_k=5,
                    min_similarity=0.25  # 关系查询使用较低阈值
                )
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'result': {
                        'text': rag_result.get('text', ''),
                        'citations': rag_result.get('citations', []),
                        'debug': rag_result.get('debug', {})
                    }
                }
            except Exception as e:
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'error': str(e),
                    'result': None
                }
        
        query_tasks = [execute_query(q) for q in queries]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        for result in query_results:
            if not isinstance(result, Exception):
                relationship_queries.append(result)
        
        return relationship_queries
    
    # 并行执行所有查询
    spread_queries, relationship_queries = await asyncio.gather(
        retrieve_spread_method(),
        retrieve_card_relationships()
    )
    
    rag_queries.extend(spread_queries)
    rag_queries.extend(relationship_queries)
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    print(f"\n✅ 测试2完成")
    print(f"总耗时: {elapsed_ms}ms")
    print(f"  卡牌信息查询: {len([q for q in rag_queries if q.get('card_id')])}个")
    print(f"  占卜方法查询: {len(spread_queries)}个")
    print(f"  牌型分析查询: {len(relationship_queries)}个")
    
    if rag_queries:
        analysis = analyze_rag_duplicates(rag_queries)
        print(f"\nRAG重复率分析:")
        print(f"  总查询数: {analysis['total_queries']}")
        print(f"  唯一文档块数: {analysis['total_unique_chunks']}")
        print(f"  重复率: {analysis['duplicate_rate']:.2f}%")
        
        return analysis, elapsed_ms, rag_queries
    
    return None, None, None


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("RAG优化测试：调整阈值和问题融合")
    print("="*80)
    
    # 获取第一次测试的牌面
    cards = get_first_test_cards()
    if not cards:
        print("❌ 无法获取第一次测试的牌面信息")
        return
    
    # 创建用户信息（与第一次测试相同）
    user_profile = UserProfileCreate(
        age=30,
        gender="male",
        zodiac_sign="Scorpio",
        appearance_type="swords",
        personality_type="cups",
        preferred_source="pkt"
    )
    
    question = "我下个月运势如何"
    
    # 测试1：调整阈值
    analysis1, time1, queries1 = await test_adjusted_threshold(cards, user_profile, question)
    
    # 测试2：融合查询（包含占卜方法和牌型分析）
    analysis2, time2, queries2 = await test_merged_queries(cards, user_profile, question, spread_type="three_card")
    
    # 对比结果
    print("\n" + "="*80)
    print("测试结果对比")
    print("="*80)
    
    print(f"\n测试1（阈值0.6）:")
    if analysis1:
        print(f"  总查询数: {analysis1['total_queries']}")
        print(f"  唯一文档块数: {analysis1['total_unique_chunks']}")
        print(f"  重复率: {analysis1['duplicate_rate']:.2f}%")
        print(f"  耗时: {time1}ms")
    
    print(f"\n测试2（融合查询）:")
    if analysis2:
        print(f"  总查询数: {analysis2['total_queries']}")
        print(f"  唯一文档块数: {analysis2['total_unique_chunks']}")
        print(f"  重复率: {analysis2['duplicate_rate']:.2f}%")
        print(f"  耗时: {time2}ms")
    
    # 保存结果
    result_file = Path(__file__).parent / "result" / f"rag_threshold_merge_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_file.parent.mkdir(exist_ok=True)
    
    output = {
        'test_time': datetime.now().isoformat(),
        'cards': cards,
        'test1_threshold_0_6': {
            'analysis': analysis1,
            'time_ms': time1,
            'query_count': len(queries1) if queries1 else 0
        },
        'test2_merged_queries': {
            'analysis': analysis2,
            'time_ms': time2,
            'query_count': len(queries2) if queries2 else 0
        }
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {result_file}")


if __name__ == "__main__":
    asyncio.run(main())

