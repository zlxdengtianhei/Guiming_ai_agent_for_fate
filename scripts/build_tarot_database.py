#!/usr/bin/env python3
"""
Build Tarot Card Database from PKT Document

This script:
1. Reads the PKT (Pictorial Key to the Tarot) document
2. Uses OpenRouter LLM to extract card information
3. Generates SQL INSERT statements
4. Inserts data into Supabase tarot_cards table

Total cards: 78 (22 Major Arcana + 56 Minor Arcana)
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import openai
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.database import get_supabase_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


class TarotCardExtractor:
    """Extract tarot card information from PKT document using LLM."""
    
    def __init__(self):
        """Initialize OpenAI/OpenRouter client."""
        if settings.use_openrouter and settings.openrouter_api_key:
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/tarot_agent",
                "X-Title": "Tarot Agent Database Builder"
            }
            logger.info("Using OpenRouter for LLM extraction")
        else:
            api_key = settings.openai_api_key
            base_url = None
            default_headers = {}
            logger.info("Using OpenAI for LLM extraction")
        
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        self.model = settings.openai_chat_model
    
    def read_pkt_document(self) -> str:
        """Read the PKT document."""
        pkt_path = Path(__file__).parent.parent / "docs" / "pkt.txt"
        if not pkt_path.exists():
            raise FileNotFoundError(f"PKT document not found at {pkt_path}")
        
        logger.info(f"Reading PKT document from {pkt_path}")
        with open(pkt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Read {len(content)} characters from PKT document")
        return content
    
    def extract_major_arcana(self, pkt_content: str) -> List[Dict[str, Any]]:
        """Extract Major Arcana cards (22 cards) using LLM."""
        logger.info("Extracting Major Arcana cards...")
        
        # Find relevant sections
        # PART II section 2: descriptions (around line 322-703)
        # PART III section 3: divinatory meanings (around line 1600-1648)
        part2_start = pkt_content.find("PART II")
        part3_start = pkt_content.find("PART III")
        
        if part2_start == -1 or part3_start == -1:
            logger.warning("Could not find PART II or PART III sections, using full content")
            relevant_content = pkt_content[:50000]
        else:
            # Extract PART II section 2 (descriptions) and PART III section 3 (meanings)
            # Use larger sections to ensure complete extraction
            descriptions_section = pkt_content[part2_start:part2_start+60000]  # Increased for complete descriptions
            meanings_section = pkt_content[part3_start:part3_start+30000]  # Increased for complete meanings
            relevant_content = descriptions_section + "\n\n" + meanings_section
        
        prompt = f"""You are extracting Tarot card information from "The Pictorial Key to the Tarot" by A.E. Waite (1911).

CRITICAL: You must extract the EXACT ORIGINAL TEXT from PKT, not modern interpretations.

Extract information for all 22 Major Arcana cards (0-21):
- 0. The Fool
- 1. The Magician (The Magus, Magician, or juggler)
- 2. The High Priestess (The Pope Joan, or Female Pontiff)
- 3. The Empress
- 4. The Emperor
- 5. The Hierophant (The High Priest, called also Spiritual Father, and more commonly the Pope)
- 6. The Lovers (or Marriage)
- 7. The Chariot
- 8. Strength/Fortitude
- 9. The Hermit
- 10. Wheel of Fortune
- 11. Justice
- 12. The Hanged Man
- 13. Death
- 14. Temperance
- 15. The Devil
- 16. The Tower (struck by Lightning)
- 17. The Star (Dog-Star, or Sirius)
- 18. The Moon
- 19. The Sun
- 20. The Last Judgment
- 21. The World (the Universe, or Time)

For each card, extract EXACTLY from PKT:

1. card_name_en: English name (primary name from PKT)
2. card_number: Number (0-21)
3. suit: "major"
4. arcana: "major"
5. description: COMPLETE visual description from PART II, section 2 - include ALL details (gorgeous vestments, rose, wand, wallet, etc.). Do NOT simplify or summarize. Include the full paragraph(s) describing the card image.
6. symbolic_meaning: Deep symbolic meanings and philosophical interpretations from PART II, section 2 (the deeper meanings beyond visual description, e.g., "prince of the other world", "spirit in search of experience", mystical explanations). If the description blends visual and symbolic, extract the symbolic parts here.
7. upright_meaning: EXACT divinatory meaning from PART III, section 3 - use the ORIGINAL PKT text after the card name and "--". DO NOT use modern interpretations. Example: For The Fool, use "Folly, mania, extravagance, intoxication, delirium, frenzy, bewrayment" NOT "New beginnings, innocence, spontaneity".
8. reversed_meaning: EXACT reversed meaning from PART III, section 3 - use the ORIGINAL PKT text after "Reversed:". DO NOT use modern interpretations.

Return JSON array with all 22 cards. Use this format:
[
  {{
    "card_name_en": "The Fool",
    "card_number": 0,
    "suit": "major",
    "arcana": "major",
    "description": "With light step, as if earth and its trammels had little power to restrain him, a young man in gorgeous vestments pauses at the brink of a precipice... [COMPLETE ORIGINAL TEXT]",
    "symbolic_meaning": "He is a prince of the other world on his travels through this one... [DEEP SYMBOLIC MEANINGS]",
    "upright_meaning": "Folly, mania, extravagance, intoxication, delirium, frenzy, bewrayment",
    "reversed_meaning": "Negligence, absence, distribution, carelessness, apathy, nullity, vanity"
  }},
  ...
]

Document content (PART II section 2 - descriptions, PART III section 3 - meanings):
{relevant_content[:40000]}...

IMPORTANT:
- Extract COMPLETE original text, do NOT summarize or simplify
- Use PKT's original divinatory meanings, NOT modern interpretations
- Separate visual description (description) from symbolic meaning (symbolic_meaning)
- Make sure to extract all 22 cards in order
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are extracting data from 'The Pictorial Key to the Tarot' by A.E. Waite (1911). You must extract the EXACT ORIGINAL TEXT from PKT, not modern interpretations. Always return valid JSON with complete original text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            cards = json.loads(result_text)
            logger.info(f"Extracted {len(cards)} Major Arcana cards")
            return cards
            
        except Exception as e:
            logger.error(f"Failed to extract Major Arcana: {e}")
            raise
    
    def extract_minor_arcana(self, pkt_content: str) -> List[Dict[str, Any]]:
        """Extract Minor Arcana cards (56 cards) using LLM."""
        logger.info("Extracting Minor Arcana cards...")
        
        # Find relevant sections
        # PART III, section 2 contains descriptions and meanings (around line 747-1594)
        # PART III, section 4 contains additional meanings (around line 1655-1768)
        part3_start = pkt_content.find("PART III")
        section2_start = pkt_content.find("section 2", part3_start)
        section4_start = pkt_content.find("section 4", part3_start)
        
        if section2_start == -1:
            logger.warning("Could not find PART III section 2, using content from PART III")
            relevant_content = pkt_content[part3_start:part3_start+100000] if part3_start != -1 else pkt_content[50000:150000]
        else:
            # Extract section 2 (main descriptions) and section 4 (additional meanings)
            section2_content = pkt_content[section2_start:section2_start+100000]  # Increased for complete descriptions
            if section4_start != -1:
                section4_content = pkt_content[section4_start:section4_start+15000]  # Increased for complete additional meanings
                relevant_content = section2_content + "\n\n=== ADDITIONAL MEANINGS (Section 4) ===\n\n" + section4_content
            else:
                relevant_content = section2_content
        
        prompt = f"""You are extracting Tarot card information from "The Pictorial Key to the Tarot" by A.E. Waite (1911).

CRITICAL: You must extract the EXACT ORIGINAL TEXT from PKT, not modern interpretations.

Extract information for all 56 Minor Arcana cards:
- 4 suits: Wands, Cups, Swords, Pentacles
- Each suit has: King, Queen, Knight, Page, Ace, 2, 3, 4, 5, 6, 7, 8, 9, 10 (14 cards per suit)

For each card, extract EXACTLY from PKT:

1. card_name_en: Format as "King of Wands", "Ace of Cups", "Two of Swords", "Three of Pentacles", etc.
   - Use "Ace" not "One"
   - Use "Two", "Three", "Four", etc. for numbered cards
   - Use "King", "Queen", "Knight", "Page" for court cards
2. card_number: 
   - Ace = 1
   - 2-10 = 2-10
   - Page = 11
   - Knight = 12
   - Queen = 13
   - King = 14
3. suit: "wands", "cups", "swords", or "pentacles" (lowercase)
4. arcana: "minor"
5. description: COMPLETE image description from PART III, section 2 - include ALL details. Include physical/emotional nature descriptions (e.g., "dark, ardent, lithe, animated, impassioned, noble" for King of Wands). Do NOT simplify.
6. upright_meaning: EXACT divinatory meaning from PART III, section 2 - use the ORIGINAL PKT text after "Divinatory Meanings:". DO NOT use modern interpretations. Example: For King of Wands, use "Dark man, friendly, countryman, generally married, honest and conscientious. The card always signifies honesty, and may mean news concerning an unexpected heritage to fall in before very long" NOT "Leadership, vision, and the ability to inspire others".
7. reversed_meaning: EXACT reversed meaning from PART III, section 2 - use the ORIGINAL PKT text after "Reversed:". DO NOT use modern interpretations. Example: For King of Wands, use "Good, but severe; austere, yet tolerant" NOT "Impulsiveness, lack of direction, and overbearing behavior".
8. additional_meanings: Additional divinatory meanings from PART III, section 4 (if available). Format as "Upright: [text]. Reversed: [text]". Some cards may not have additional meanings.

Return JSON array with all 56 cards. Use this format:
[
  {{
    "card_name_en": "King of Wands",
    "card_number": 14,
    "suit": "wands",
    "arcana": "minor",
    "description": "The physical and emotional nature to which this card is attributed is dark, ardent, lithe, animated, impassioned, noble. The King uplifts a flowering wand... [COMPLETE ORIGINAL TEXT]",
    "upright_meaning": "Dark man, friendly, countryman, generally married, honest and conscientious. The card always signifies honesty, and may mean news concerning an unexpected heritage to fall in before very long",
    "reversed_meaning": "Good, but severe; austere, yet tolerant",
    "additional_meanings": "Upright: Generally favourable may signify a good marriage. Reversed: Advice that should be followed."
  }},
  ...
]

Document content (PART III, section 2 - descriptions and meanings, section 4 - additional meanings):
{relevant_content[:50000]}...

IMPORTANT:
- Extract COMPLETE original text, do NOT summarize or simplify
- Use PKT's original divinatory meanings, NOT modern interpretations
- Include additional_meanings from section 4 if available
- Make sure to extract all 56 cards (4 suits × 14 cards each) in this order:
  1. Wands: King, Queen, Knight, Page, Ten, Nine, Eight, Seven, Six, Five, Four, Three, Two, Ace
  2. Cups: King, Queen, Knight, Page, Ten, Nine, Eight, Seven, Six, Five, Four, Three, Two, Ace
  3. Swords: King, Queen, Knight, Page, Ten, Nine, Eight, Seven, Six, Five, Four, Three, Two, Ace
  4. Pentacles: King, Queen, Knight, Page, Ten, Nine, Eight, Seven, Six, Five, Four, Three, Two, Ace
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are extracting data from 'The Pictorial Key to the Tarot' by A.E. Waite (1911). You must extract the EXACT ORIGINAL TEXT from PKT, not modern interpretations. Always return valid JSON with complete original text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            cards = json.loads(result_text)
            logger.info(f"Extracted {len(cards)} Minor Arcana cards")
            return cards
            
        except Exception as e:
            logger.error(f"Failed to extract Minor Arcana: {e}")
            raise
    
    def generate_chinese_names(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Chinese names for cards using LLM."""
        logger.info("Generating Chinese names for cards...")
        
        # Prepare card names for translation
        card_names = [card["card_name_en"] for card in cards]
        
        prompt = f"""Translate these Tarot card names to Chinese. Return JSON array with same order.

Cards to translate:
{json.dumps(card_names, indent=2, ensure_ascii=False)}

Return format:
[
  {{"card_name_en": "The Fool", "card_name_cn": "愚人"}},
  {{"card_name_en": "The Magician", "card_name_cn": "魔术师"}},
  ...
]

Use standard Chinese Tarot card names.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that translates Tarot card names to Chinese. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            translations = json.loads(result_text)
            
            # Create mapping
            name_map = {t["card_name_en"]: t["card_name_cn"] for t in translations}
            
            # Add Chinese names to cards
            for card in cards:
                card["card_name_cn"] = name_map.get(card["card_name_en"], card["card_name_en"])
            
            logger.info("Generated Chinese names for all cards")
            return cards
            
        except Exception as e:
            logger.warning(f"Failed to generate Chinese names: {e}, using English names")
            for card in cards:
                card["card_name_cn"] = card["card_name_en"]
            return cards


class TarotDatabaseBuilder:
    """Build tarot card database in Supabase."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase = get_supabase_service()
        logger.info("Initialized Supabase service client")
    
    def insert_cards(self, cards: List[Dict[str, Any]]) -> int:
        """Insert cards into Supabase tarot_cards table."""
        logger.info(f"Inserting {len(cards)} cards into database...")
        
        # Prepare data for insertion
        card_data = []
        for card in cards:
            card_data.append({
                "card_name_en": card["card_name_en"],  # Use English name as unique identifier
                "card_name_cn": card.get("card_name_cn", ""),
                "card_number": card["card_number"],
                "suit": card["suit"],
                "arcana": card["arcana"],
                "description": card.get("description", ""),
                "upright_meaning": card.get("upright_meaning", ""),
                "reversed_meaning": card.get("reversed_meaning", ""),
                "symbolic_meaning": card.get("symbolic_meaning", ""),  # Major Arcana
                "additional_meanings": card.get("additional_meanings", ""),  # Minor Arcana
                "image_url": card.get("image_url", "")
            })
        
        try:
            # Use upsert to handle duplicates
            result = self.supabase.table("tarot_cards").upsert(
                card_data,
                on_conflict="card_name_en"
            ).execute()
            
            inserted_count = len(result.data) if result.data else 0
            logger.info(f"✅ Successfully inserted/updated {inserted_count} cards")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Failed to insert cards: {e}")
            raise
    
    def verify_insertion(self) -> Dict[str, Any]:
        """Verify card insertion and return statistics."""
        try:
            result = self.supabase.table("tarot_cards").select("*", count="exact").execute()
            
            total = result.count if hasattr(result, 'count') else len(result.data)
            
            # Count by arcana
            major_count = len([c for c in result.data if c.get("arcana") == "major"])
            minor_count = len([c for c in result.data if c.get("arcana") == "minor"])
            
            # Count by suit
            suits = {}
            for card in result.data:
                suit = card.get("suit", "unknown")
                suits[suit] = suits.get(suit, 0) + 1
            
            # Check data quality
            cards_with_description = len([c for c in result.data if c.get("description")])
            cards_with_upright = len([c for c in result.data if c.get("upright_meaning")])
            cards_with_reversed = len([c for c in result.data if c.get("reversed_meaning")])
            cards_with_cn_name = len([c for c in result.data if c.get("card_name_cn")])
            major_with_symbolic = len([c for c in result.data if c.get("arcana") == "major" and c.get("symbolic_meaning")])
            minor_with_additional = len([c for c in result.data if c.get("arcana") == "minor" and c.get("additional_meanings")])
            
            stats = {
                "total": total,
                "major_arcana": major_count,
                "minor_arcana": minor_count,
                "by_suit": suits,
                "data_quality": {
                    "cards_with_description": cards_with_description,
                    "cards_with_upright_meaning": cards_with_upright,
                    "cards_with_reversed_meaning": cards_with_reversed,
                    "cards_with_chinese_name": cards_with_cn_name,
                    "major_with_symbolic_meaning": major_with_symbolic,
                    "minor_with_additional_meanings": minor_with_additional
                }
            }
            
            logger.info(f"Database statistics: {json.dumps(stats, indent=2)}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to verify insertion: {e}")
            raise


def main():
    """Main function to build tarot database."""
    logger.info("=" * 60)
    logger.info("Starting Tarot Card Database Builder")
    logger.info("=" * 60)
    
    try:
        # Step 1: Read PKT document
        extractor = TarotCardExtractor()
        pkt_content = extractor.read_pkt_document()
        
        # Step 2: Extract Major Arcana (22 cards)
        logger.info("\n" + "=" * 60)
        logger.info("Step 1: Extracting Major Arcana")
        logger.info("=" * 60)
        major_cards = extractor.extract_major_arcana(pkt_content)
        
        # Step 3: Extract Minor Arcana (56 cards)
        logger.info("\n" + "=" * 60)
        logger.info("Step 2: Extracting Minor Arcana")
        logger.info("=" * 60)
        minor_cards = extractor.extract_minor_arcana(pkt_content)
        
        # Step 4: Generate Chinese names
        logger.info("\n" + "=" * 60)
        logger.info("Step 3: Generating Chinese Names")
        logger.info("=" * 60)
        all_cards = major_cards + minor_cards
        all_cards = extractor.generate_chinese_names(all_cards)
        
        logger.info(f"\nTotal cards extracted: {len(all_cards)}")
        logger.info(f"  - Major Arcana: {len(major_cards)}")
        logger.info(f"  - Minor Arcana: {len(minor_cards)}")
        
        # Step 5: Insert into database
        logger.info("\n" + "=" * 60)
        logger.info("Step 4: Inserting into Supabase")
        logger.info("=" * 60)
        builder = TarotDatabaseBuilder()
        inserted_count = builder.insert_cards(all_cards)
        
        # Step 6: Verify insertion
        logger.info("\n" + "=" * 60)
        logger.info("Step 5: Verifying Insertion")
        logger.info("=" * 60)
        stats = builder.verify_insertion()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ Database Build Complete!")
        logger.info("=" * 60)
        logger.info(f"Total cards in database: {stats['total']}")
        logger.info(f"  - Major Arcana: {stats['major_arcana']}")
        logger.info(f"  - Minor Arcana: {stats['minor_arcana']}")
        logger.info(f"  - By suit: {stats['by_suit']}")
        
        # Save extracted data to JSON for reference
        output_path = Path(__file__).parent.parent / "rag" / "data" / "tarot_cards_extracted.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_cards, f, indent=2, ensure_ascii=False)
        logger.info(f"\nSaved extracted data to: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Error building database: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

