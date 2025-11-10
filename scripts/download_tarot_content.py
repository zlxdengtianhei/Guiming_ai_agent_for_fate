#!/usr/bin/env python3
"""
Script to download and process Tarot content from sacred-texts.com
Downloads the Pictorial Key to the Tarot by Arthur Edward Waite
"""

import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup
from typing import List, Dict
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://sacred-texts.com/tarot/pkt/index.htm"
DOMAIN = "https://sacred-texts.com"


async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch a webpage and return its HTML content."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return ""


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text


def extract_sections(text: str, source_url: str) -> List[Dict[str, str]]:
    """Extract meaningful sections from text."""
    sections = []
    
    # Split by double newlines (paragraphs)
    paragraphs = text.split('\n\n')
    
    section_num = 1
    for para in paragraphs:
        para = para.strip()
        if len(para) < 50:  # Skip very short paragraphs
            continue
        
        # Extract title if it's in all caps or has special formatting
        lines = para.split('\n')
        title = None
        content = para
        
        if len(lines) > 1:
            first_line = lines[0].strip()
            # Check if first line looks like a title
            if first_line.isupper() or len(first_line) < 100:
                title = first_line
                content = '\n'.join(lines[1:])
        
        sections.append({
            'text': content,
            'source': source_url,
            'chunk_id': f"tarot-pkt-{section_num}",
            'metadata': {
                'title': title or 'Untitled Section',
                'section_number': section_num
            }
        })
        section_num += 1
    
    return sections


async def download_tarot_content() -> List[Dict[str, str]]:
    """
    Download and process Tarot content from sacred-texts.com.
    
    Returns:
        List of document dictionaries ready for RAG processing
    """
    logger.info(f"Starting download from {BASE_URL}")
    
    async with aiohttp.ClientSession() as session:
        # Fetch main index page
        html = await fetch_page(session, BASE_URL)
        
        if not html:
            logger.error("Failed to fetch main page")
            return []
        
        # Extract text
        text = extract_text_from_html(html)
        
        # Extract sections
        sections = extract_sections(text, BASE_URL)
        
        logger.info(f"Extracted {len(sections)} sections from main page")
        
        # Try to find and fetch linked pages
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        
        additional_docs = []
        for link in links[:20]:  # Limit to first 20 links to avoid too many requests
            href = link.get('href', '')
            if href.endswith('.htm') and 'pkt' in href:
                full_url = f"{DOMAIN}/tarot/pkt/{href}" if not href.startswith('http') else href
                logger.info(f"Fetching: {full_url}")
                
                page_html = await fetch_page(session, full_url)
                if page_html:
                    page_text = extract_text_from_html(page_html)
                    page_sections = extract_sections(page_text, full_url)
                    additional_docs.extend(page_sections)
        
        # Combine all sections
        all_docs = sections + additional_docs
        
        logger.info(f"Total documents extracted: {len(all_docs)}")
        return all_docs


async def save_to_json(documents: List[Dict[str, str]], filename: str = "tarot_content.json"):
    """Save documents to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(documents)} documents to {filename}")


async def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("Tarot Content Downloader")
    logger.info("=" * 60)
    
    # Download content
    documents = await download_tarot_content()
    
    if documents:
        # Save to JSON
        await save_to_json(documents, "tarot_content.json")
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Download Summary:")
        logger.info(f"Total documents: {len(documents)}")
        logger.info(f"Total text length: {sum(len(doc['text']) for doc in documents)} characters")
        logger.info("\nSample document:")
        if documents:
            sample = documents[0]
            logger.info(f"  Source: {sample['source']}")
            logger.info(f"  Chunk ID: {sample['chunk_id']}")
            logger.info(f"  Text preview: {sample['text'][:200]}...")
        
        logger.info("\nNext steps:")
        logger.info("1. Review tarot_content.json")
        logger.info("2. Use the RAG service to process and store these documents")
    else:
        logger.error("No documents were downloaded")


if __name__ == "__main__":
    asyncio.run(main())

