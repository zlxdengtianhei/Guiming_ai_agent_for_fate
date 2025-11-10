"""
生成问题与RAG搜索结果对应的易读文档
"""

import json
from pathlib import Path
from datetime import datetime


def generate_readable_mapping(analysis_file: str, output_file: str):
    """生成易读的问题与RAG搜索结果对应文档"""
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    question = analysis['question']
    mapping = analysis['query_result_mapping']
    summary = analysis['summary']
    duplicates = analysis['duplicate_analysis']
    quality = analysis['quality_analysis']
    
    # 生成Markdown文档
    doc_lines = [
        "# RAG查询结果分析报告",
        "",
        f"**问题**: {question}",
        f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 📊 总体统计",
        "",
        f"- **总查询数**: {summary['total_queries']}",
        f"- **唯一chunk数**: {summary['total_unique_chunks']}",
        f"- **重复chunk数**: {summary['duplicate_chunks_count']}",
        "",
        "### 查询类型分布",
        "",
        "| 查询类型 | 数量 |",
        "|---------|------|"
    ]
    
    for query_type, count in sorted(summary['queries_by_type'].items(), key=lambda x: x[1], reverse=True):
        doc_lines.append(f"| {query_type} | {count} |")
    
    doc_lines.extend([
        "",
        "### 相似度统计",
        "",
        f"- **最低相似度**: {summary['similarity_stats']['min']:.4f}",
        f"- **最高相似度**: {summary['similarity_stats']['max']:.4f}",
        f"- **平均相似度**: {summary['similarity_stats']['avg']:.4f}",
        "",
        "### 来源分布",
        "",
        "| 来源 | 引用次数 |",
        "|------|---------|"
    ])
    
    for source, count in sorted(summary['source_distribution'].items(), key=lambda x: x[1], reverse=True):
        doc_lines.append(f"| {source} | {count} |")
    
    doc_lines.extend([
        "",
        "### 质量分布",
        "",
        "| 质量等级 | 查询数 | 说明 |",
        "|---------|--------|------|",
        f"| 优秀 | {summary['quality_distribution']['excellent']} | 最高相似度 > 0.6 |",
        f"| 良好 | {summary['quality_distribution']['good']} | 最高相似度 0.4-0.6 |",
        f"| 一般 | {summary['quality_distribution']['fair']} | 最高相似度 0.3-0.4 |",
        f"| 较差 | {summary['quality_distribution']['poor']} | 最高相似度 < 0.3 或无结果 |",
        "",
        "---",
        "",
        "## 🔍 详细查询结果映射",
        "",
        "### 查询结果说明",
        "",
        "- **num_results_retrieved**: 每次搜索返回的结果数量",
        "- **similarity**: 相似度分数（0-1，越高越相关）",
        "- **chunk_id**: 文档块的唯一标识",
        "",
        "---",
        ""
    ])
    
    # 按查询类型分组
    queries_by_type = {}
    for query in mapping:
        query_type = query['query_type']
        if query_type not in queries_by_type:
            queries_by_type[query_type] = []
        queries_by_type[query_type].append(query)
    
    # 生成每个查询的详细信息
    for query_type, queries in sorted(queries_by_type.items()):
        doc_lines.extend([
            f"### {query_type}",
            ""
        ])
        
        for query in queries:
            card_name = query.get('card_name') or "N/A"
            doc_lines.extend([
                f"#### 查询 #{query['query_index']}: {query_type}",
                "",
                f"- **查询文本**: `{query['query_text']}`",
                f"- **关联卡牌**: {card_name}",
                f"- **返回结果数**: {query['num_results_retrieved']}",
                f"- **处理时间**: {query['latency_ms']}ms",
                "",
                "**检索到的文档块**:",
                ""
            ])
            
            if query['citations']:
                doc_lines.append("| 来源 | Chunk ID | 相似度 |")
                doc_lines.append("|------|----------|--------|")
                for citation in query['citations']:
                    doc_lines.append(
                        f"| {citation['source']} | `{citation['chunk_id']}` | {citation['similarity']:.4f} |"
                    )
            else:
                doc_lines.append("*无结果*")
            
            doc_lines.extend([
                "",
                f"**结果预览**: {query['result_text_preview']}",
                "",
                "---",
                ""
            ])
    
    # 添加重复分析
    doc_lines.extend([
        "## 🔄 重复内容分析",
        "",
        f"共有 **{duplicates['total_duplicate_chunks']}** 个文档块在多个查询中重复出现。",
        "",
        "### 重复最多的文档块",
        ""
    ])
    
    # 显示前10个重复最多的chunk
    sorted_dups = sorted(
        duplicates['duplicates'].items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]
    
    for chunk_id, usages in sorted_dups:
        doc_lines.extend([
            f"#### `{chunk_id}`",
            "",
            f"出现在 **{len(usages)}** 个查询中:",
            ""
        ])
        
        for usage in usages[:5]:  # 只显示前5个
            doc_lines.append(
                f"- **{usage['query_type']}** ({usage['card_name']}): "
                f"相似度 {usage['similarity']:.4f} - `{usage['query'][:60]}...`"
            )
        
        if len(usages) > 5:
            doc_lines.append(f"- ... 还有 {len(usages) - 5} 个查询")
        
        doc_lines.append("")
    
    # 添加质量分析
    doc_lines.extend([
        "## 📈 质量分析",
        ""
    ])
    
    if quality['queries_with_no_results']:
        doc_lines.extend([
            "### ⚠️ 无结果的查询",
            "",
            f"共有 {len(quality['queries_with_no_results'])} 个查询没有返回结果:",
            ""
        ])
        for q in quality['queries_with_no_results']:
            doc_lines.append(f"- **{q['type']}** ({q['card_name']}): `{q['query']}`")
        doc_lines.append("")
    
    if quality['queries_with_low_similarity']:
        doc_lines.extend([
            "### ⚠️ 低相似度查询（相似度 < 0.3）",
            "",
            f"共有 {len(quality['queries_with_low_similarity'])} 个查询相似度较低:",
            ""
        ])
        for q in quality['queries_with_low_similarity'][:10]:
            doc_lines.append(
                f"- **{q['type']}** ({q['card_name']}): "
                f"最高相似度 {q['max_similarity']:.4f} - `{q['query'][:60]}...`"
            )
        doc_lines.append("")
    
    if quality['queries_with_high_similarity']:
        doc_lines.extend([
            "### ✅ 高相似度查询（相似度 > 0.6）",
            "",
            f"共有 {len(quality['queries_with_high_similarity'])} 个查询相似度很高:",
            ""
        ])
        for q in quality['queries_with_high_similarity'][:10]:
            doc_lines.append(
                f"- **{q['type']}** ({q['card_name']}): "
                f"最高相似度 {q['max_similarity']:.4f} - `{q['query'][:60]}...`"
            )
        doc_lines.append("")
    
    # 添加总结
    doc_lines.extend([
        "---",
        "",
        "## 📝 总结",
        "",
        "### 主要发现",
        "",
        "1. **搜索数据量**:",
        f"   - 大部分查询（{summary['queries_by_type'].get('basic_meaning', 0) + summary['queries_by_type'].get('visual_description', 0)}个）返回5个结果",
        f"   - 平均相似度 {summary['similarity_stats']['avg']:.4f}，说明搜索结果相关性较好",
        "",
        "2. **重复情况**:",
        f"   - 有 {summary['duplicate_chunks_count']} 个文档块在多个查询中重复出现",
        "   - 这可能是正常的，因为同一张牌的不同查询类型（如basic_meaning、upright_meaning）可能检索到相同的文档块",
        "",
        "3. **搜索结果质量**:",
        f"   - {summary['quality_distribution']['excellent']} 个查询质量优秀（相似度>0.6）",
        f"   - {summary['quality_distribution']['good']} 个查询质量良好（相似度0.4-0.6）",
        f"   - 只有 {summary['quality_distribution']['poor']} 个查询质量较差",
        "",
        "4. **来源分布**:",
        f"   - 78_degrees_of_wisdom.txt: {summary['source_distribution'].get('78_degrees_of_wisdom.txt', 0)} 次引用",
        f"   - pkt.txt: {summary['source_distribution'].get('pkt.txt', 0)} 次引用",
        "   - 两个来源都有较好的覆盖",
        ""
    ])
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(doc_lines))
    
    print(f"✅ 易读文档已生成: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python generate_rag_mapping_doc.py <analysis_json_file> [output_md_file]")
        sys.exit(1)
    
    analysis_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else analysis_file.replace('.json', '_mapping.md')
    
    generate_readable_mapping(analysis_file, output_file)





