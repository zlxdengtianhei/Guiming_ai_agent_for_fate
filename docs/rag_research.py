#!/usr/bin/env python3
"""
RAG Research Tool

This script performs RAG searches and saves all text results to files.
Input: User question
Output: All query results saved to research_results subfolder
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.rag import rag_service
from app.core.config import settings


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Convert text to a safe filename."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


async def perform_rag_search(query: str, top_k: int = 20, min_similarity: float = 0.3) -> Dict[str, Any]:
    """
    Perform RAG search and return all results.
    
    Args:
        query: User's question
        top_k: Number of chunks to retrieve
        min_similarity: Minimum similarity threshold
        
    Returns:
        Dictionary with chunks, citations, and debug info
    """
    print(f"\n🔍 Performing RAG search...")
    print(f"Query: {query}")
    print(f"Top K: {top_k}, Min Similarity: {min_similarity}")
    
    try:
        # Use search_only to get raw chunks without LLM processing
        result = await rag_service.search_only(
            query=query,
            top_k=top_k,
            balance_sources=True,
            min_similarity=min_similarity
        )
        
        return result
    except Exception as e:
        print(f"❌ Error during RAG search: {e}")
        raise


def save_results(query: str, result: Dict[str, Any], output_dir: Path):
    """
    Save RAG search results to files.
    
    Args:
        query: Original query
        result: RAG search result dictionary
        output_dir: Output directory path
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename from query
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = sanitize_filename(query)
    filename_base = f"{timestamp}_{safe_query}"
    
    # Save full JSON result
    json_file = output_dir / f"{filename_base}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'query': query,
            'timestamp': timestamp,
            'result': result
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved JSON result to: {json_file}")
    
    # Save readable text summary
    txt_file = output_dir / f"{filename_base}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAG Research Results\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Query: {query}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"\n")
        
        # Debug info
        debug = result.get('debug', {})
        f.write("Search Statistics:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Results: {debug.get('num_results', 0)}\n")
        f.write(f"Latency: {debug.get('latency_ms', 0)}ms\n")
        f.write(f"\n")
        
        # Chunks
        chunks = result.get('chunks', [])
        if chunks:
            f.write("=" * 80 + "\n")
            f.write("Retrieved Chunks\n")
            f.write("=" * 80 + "\n\n")
            
            for i, chunk in enumerate(chunks, 1):
                f.write(f"\n--- Chunk {i} ---\n")
                f.write(f"Source: {chunk.get('source', 'Unknown')}\n")
                f.write(f"Chunk ID: {chunk.get('chunk_id', 'N/A')}\n")
                f.write(f"Similarity: {chunk.get('similarity', 0):.4f}\n")
                
                # Metadata
                metadata = chunk.get('metadata', {})
                if metadata:
                    f.write(f"Metadata: {json.dumps(metadata, ensure_ascii=False, indent=2)}\n")
                
                f.write(f"\nText:\n")
                f.write("-" * 80 + "\n")
                text = chunk.get('text', '')
                f.write(text)
                f.write("\n" + "-" * 80 + "\n\n")
        else:
            f.write("No chunks found.\n")
        
        # Citations summary
        citations = result.get('citations', [])
        if citations:
            f.write("\n" + "=" * 80 + "\n")
            f.write("Citations Summary\n")
            f.write("=" * 80 + "\n\n")
            
            # Group by source
            by_source = {}
            for citation in citations:
                source = citation.get('source', 'Unknown')
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(citation)
            
            for source, source_citations in by_source.items():
                f.write(f"\nSource: {source}\n")
                f.write(f"  Count: {len(source_citations)}\n")
                f.write(f"  Chunk IDs: {[c.get('chunk_id') for c in source_citations]}\n")
    
    print(f"✅ Saved text summary to: {txt_file}")
    
    return json_file, txt_file


def print_summary(result: Dict[str, Any]):
    """Print a summary of the search results."""
    chunks = result.get('chunks', [])
    debug = result.get('debug', {})
    
    print(f"\n" + "=" * 80)
    print(f"Search Summary")
    print("=" * 80)
    print(f"Total Results: {len(chunks)}")
    print(f"Latency: {debug.get('latency_ms', 0)}ms")
    
    if chunks:
        # Group by source
        by_source = {}
        for chunk in chunks:
            source = chunk.get('source', 'Unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(chunk)
        
        print(f"\nResults by Source:")
        for source, source_chunks in by_source.items():
            print(f"  {source}: {len(source_chunks)} chunks")
            avg_sim = sum(c.get('similarity', 0) for c in source_chunks) / len(source_chunks)
            print(f"    Average Similarity: {avg_sim:.4f}")
        
        print(f"\nTop 3 Results:")
        for i, chunk in enumerate(chunks[:3], 1):
            source = chunk.get('source', 'Unknown')
            similarity = chunk.get('similarity', 0)
            text_preview = chunk.get('text', '')[:100].replace('\n', ' ')
            print(f"  {i}. [{source}] (sim: {similarity:.4f})")
            print(f"     {text_preview}...")
    else:
        print("No results found.")


async def main():
    """Main function."""
    # Default test query (in English)
    default_query = "What are the differences between performing a 3-card spread and a Celtic Cross spread, especially in terms of interpretation?"
    
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = default_query
        print(f"Using default test query:")
    
    print(f"\n{'=' * 80}")
    print(f"RAG Research Tool")
    print(f"{'=' * 80}")
    
    # Set output directory
    script_dir = Path(__file__).parent
    output_dir = script_dir / "research_results"
    
    print(f"\nOutput directory: {output_dir}")
    
    # Perform search
    try:
        result = await perform_rag_search(query, top_k=30, min_similarity=0.3)
        
        # Print summary
        print_summary(result)
        
        # Save results
        json_file, txt_file = save_results(query, result, output_dir)
        
        print(f"\n{'=' * 80}")
        print(f"✅ Research complete!")
        print(f"   JSON: {json_file.name}")
        print(f"   Text: {txt_file.name}")
        print(f"{'=' * 80}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

