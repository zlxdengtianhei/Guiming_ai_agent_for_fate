#!/usr/bin/env python3
"""
Script to reorganize tarot card images based on selection table:
1. Move selected images (with suffix matching column number) to archived subfolders
2. Remove numeric suffixes from all image files
3. Move all tarot card folders to backup folder
4. Rename archived folder to tarot_card
"""

import os
import shutil
from pathlib import Path
import re

# Base directory
BASE_DIR = Path("/Users/lexuanzhang/code/tarot_agent/database/images")

# Mapping from table: card_name -> column number (1, 2, or 3)
# Format: "Card Name": column_number
SELECTION_MAP = {
    "Ace of Cups": 1,
    "Ace of Pentacles": 2,
    "Ace of Swords": 1,
    "Ace of Wands": 1,
    "Death": 1,
    "Eight of Cups": 2,
    "Eight of Pentacles": 1,
    "Eight of Swords": 1,
    "Eight of Wands": 3,
    "Five of Cups": 1,
    "Five of Pentacles": 3,
    "Five of Swords": 1,
    "Five of Wands": 1,
    "Fortitude": 1,
    "Four of Cups": 3,
    "Four of Pentacles": 1,
    "Four of Swords": 1,
    "Four of Wands": 1,
    "Justice": 2,
    "King of Cups": 2,
    "King of Pentacles": 2,
    "King of Swords": 1,
    "King of Wands": 2,
    "Knight of Cups": 1,
    "Knight of Pentacles": 2,
    "Knight of Swords": 1,
    "Knight of Wands": 1,
    "Nine of Cups": 1,
    "Nine of Pentacles": 2,
    "Nine of Swords": 1,
    "Nine of Wands": 1,
    "Page of Cups": 1,
    "Page of Pentacles": 1,
    "Page of Swords": 2,
    "Page of Wands": 2,
    "Queen of Cups": 1,
    "Queen of Pentacles": 1,
    "Queen of Swords": 1,
    "Queen of Wands": 3,
    "Seven of Cups": 1,
    "Seven of Pentacles": 1,
    "Seven of Swords": 1,
    "Seven of Wands": 3,
    "Six of Cups": 1,
    "Six of Pentacles": 1,
    "Six of Swords": 1,
    "Six of Wands": 1,
    "Temperance": 3,
    "Ten of Cups": 3,
    "Ten of Pentacles": 2,
    "Ten of Swords": 1,
    "Ten of Wands": 1,
    "The Chariot": 3,
    "The Devil": 1,
    "The Emperor": 2,
    "The Empress": 1,
    "The Fool": 1,
    "The Hanged Man": 2,
    "The Hermit": 2,
    "The Hierophant": 2,
    "The Last Judgment": 1,
    "The Lovers": 2,
    "The Magician": 1,
    "The Moon": 2,
    "The Star": 2,
    "The Sun": 1,
    "The Tower": 3,
    "The World": 1,
    "Three of Cups": 1,
    "Three of Pentacles": 3,
    "Three of Swords": 3,
    "Three of Wands": 2,
    "Two of Cups": 1,
    "Two of Pentacles": 1,
    "Two of Swords": 2,
    "Two of Wands": 3,
    "Wheel of Fortune": 1,
}

def normalize_card_name(card_name: str) -> str:
    """Convert card name to folder name format (e.g., 'Ace of Cups' -> 'Ace_of_Cups')"""
    return card_name.replace(" ", "_").replace("'", "").replace("/", "_")

def get_all_tarot_folders():
    """Get all tarot card folders (excluding background and archived)"""
    folders = []
    for item in BASE_DIR.iterdir():
        if item.is_dir() and item.name not in ["background", "archived", "backup", "tarot_card"]:
            folders.append(item)
    return folders

def move_selected_images_to_archived():
    """Move selected images (with matching suffix) to archived subfolders"""
    archived_dir = BASE_DIR / "archived"
    archived_dir.mkdir(exist_ok=True)
    
    moved_count = 0
    
    for card_name, column_num in SELECTION_MAP.items():
        folder_name = normalize_card_name(card_name)
        source_folder = BASE_DIR / folder_name
        
        if not source_folder.exists():
            print(f"⚠️  Folder not found: {folder_name}")
            continue
        
        # Find the image with the matching suffix
        target_image_name = f"{folder_name}_{column_num}.png"
        source_image = source_folder / target_image_name
        
        if not source_image.exists():
            print(f"⚠️  Image not found: {target_image_name} in {folder_name}")
            continue
        
        # Create destination folder in archived
        dest_folder = archived_dir / folder_name
        dest_folder.mkdir(exist_ok=True)
        
        # Move the image
        dest_image = dest_folder / target_image_name
        shutil.move(str(source_image), str(dest_image))
        print(f"✅ Moved: {target_image_name} -> archived/{folder_name}/")
        moved_count += 1
    
    print(f"\n📦 Moved {moved_count} images to archived/")
    return moved_count

def remove_numeric_suffixes():
    """Remove numeric suffixes from all image files in all subfolders"""
    renamed_count = 0
    
    # Process all folders
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name in ["backup", "tarot_card"]:
            continue
        
        for image_file in folder.glob("*.png"):
            # Check if file has numeric suffix pattern: Name_123.png
            name_without_ext = image_file.stem
            parent_name = folder.name
            
            # Pattern: {parent_name}_{number}.png
            pattern = rf"^{re.escape(parent_name)}_(\d+)$"
            match = re.match(pattern, name_without_ext)
            
            if match:
                # Remove the numeric suffix
                new_name = f"{parent_name}.png"
                new_path = image_file.parent / new_name
                
                # If base name already exists, skip
                if new_path.exists() and new_path != image_file:
                    print(f"⚠️  Base name already exists, skipping: {image_file.name}")
                    continue
                
                image_file.rename(new_path)
                print(f"✅ Renamed: {image_file.name} -> {new_name}")
                renamed_count += 1
    
    print(f"\n🔄 Renamed {renamed_count} images (removed numeric suffixes)")
    return renamed_count

def move_folders_to_backup():
    """Move all tarot card folders to backup folder"""
    backup_dir = BASE_DIR / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    tarot_folders = get_all_tarot_folders()
    moved_count = 0
    
    for folder in tarot_folders:
        dest = backup_dir / folder.name
        if dest.exists():
            print(f"⚠️  Destination already exists, skipping: {folder.name}")
            continue
        
        shutil.move(str(folder), str(dest))
        print(f"✅ Moved folder: {folder.name} -> backup/")
        moved_count += 1
    
    print(f"\n📁 Moved {moved_count} folders to backup/")
    return moved_count

def rename_archived_to_tarot_card():
    """Rename archived folder to tarot_card"""
    archived_dir = BASE_DIR / "archived"
    tarot_card_dir = BASE_DIR / "tarot_card"
    
    if not archived_dir.exists():
        print("⚠️  archived folder does not exist")
        return False
    
    if tarot_card_dir.exists():
        print("⚠️  tarot_card folder already exists")
        return False
    
    archived_dir.rename(tarot_card_dir)
    print(f"✅ Renamed: archived/ -> tarot_card/")
    return True

def main():
    print("=" * 60)
    print("Reorganizing Tarot Card Images")
    print("=" * 60)
    print()
    
    # Step 1: Move selected images to archived
    print("Step 1: Moving selected images to archived/")
    print("-" * 60)
    move_selected_images_to_archived()
    print()
    
    # Step 2: Remove numeric suffixes from all images
    print("Step 2: Removing numeric suffixes from all images")
    print("-" * 60)
    remove_numeric_suffixes()
    print()
    
    # Step 3: Move all folders to backup
    print("Step 3: Moving all tarot card folders to backup/")
    print("-" * 60)
    move_folders_to_backup()
    print()
    
    # Step 4: Rename archived to tarot_card
    print("Step 4: Renaming archived/ to tarot_card/")
    print("-" * 60)
    rename_archived_to_tarot_card()
    print()
    
    print("=" * 60)
    print("✅ All operations completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()

