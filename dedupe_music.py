#!/usr/bin/env python3
"""
Music Deduplication Script

This script identifies duplicate music files across multiple directories,
prioritizes the highest quality version, and allows you to remove or relocate
the lower quality duplicates.

Usage:
    python dedupe_music.py [options] [directories...]

Options:
    --dry-run       Only show what would be done without making changes
    --move=DIR      Move duplicates to the specified directory instead of deleting
    --verbose       Show detailed information about each duplicate
    --threshold=N   Set similarity threshold (0.8-1.0, default 0.9)
"""

import os
import re
import sys
import shutil
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict

# File formats in order of preference (highest quality first)
FORMAT_PRIORITY = {
    '.flac': 4,  # Lossless - highest quality
    '.wav': 3,   # Lossless but larger
    '.aiff': 3,  # Lossless Apple format
    '.alac': 3,  # Apple Lossless
    '.m4a': 2,   # AAC - decent quality compressed
    '.mp3': 1,   # MP3 - compressed
    '.wma': 0,   # Windows Media - lowest priority
}

# Additional bitrate information for MP3s
MP3_BITRATE_PRIORITY = {
    320: 5,  # 320kbps is high quality
    256: 4,
    192: 3,
    160: 2,
    128: 1,
    64: 0,   # Very low quality
}

def normalize_title(filename):
    """Extract and normalize the song title and artist for comparison."""
    # Get just the filename without path or extension
    base_name = os.path.basename(filename)
    name, _ = os.path.splitext(base_name)
    
    # Remove numeric prefixes like "01 - " or "01. " or "01_"
    name = re.sub(r'^\d+[\s\.-_]+', '', name)
    
    # Remove quality indicators and other common metadata
    name = re.sub(r'\(Live.*?\)|\(Remaster(ed)?.*?\)|\(.*?Mix.*?\)|\(.*?Version.*?\)|\(From.*?\)|\{.*?\}|\[.*?\]', '', name, flags=re.IGNORECASE)
    
    # Clean up remaining spaces and special characters
    name = re.sub(r'[-_\s]{2,}', ' ', name).strip().lower()
    
    return name

def get_file_quality_score(file_path):
    """Determine a quality score for the file based on format and size."""
    ext = os.path.splitext(file_path)[1].lower()
    
    # Base score from format
    score = FORMAT_PRIORITY.get(ext, 0) * 1000
    
    # Add file size as a tiebreaker - bigger is often better quality
    score += os.path.getsize(file_path) / 1024  # Size in KB
    
    # TODO: For advanced usage, you could add code here to actually read
    # the audio file metadata to get bitrate, sample rate, etc.
    # This would require additional libraries like mutagen
    
    return score

def find_duplicates(directories, similarity_threshold=0.9):
    """Find duplicate music files across the provided directories."""
    all_files = []
    
    # Collect all music files
    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(tuple(FORMAT_PRIORITY.keys())):
                    all_files.append(os.path.join(root, file))
    
    print(f"Found {len(all_files)} music files to analyze")
    
    # Group by normalized name
    songs = defaultdict(list)
    for file_path in all_files:
        norm_name = normalize_title(file_path)
        songs[norm_name].append(file_path)
    
    # Filter to only keep groups with duplicates
    duplicates = {name: files for name, files in songs.items() if len(files) > 1}
    
    print(f"Found {len(duplicates)} songs with potential duplicates")
    
    # Sort each group by quality
    resolved_dupes = {}
    for name, files in duplicates.items():
        # Score each file
        scored_files = [(f, get_file_quality_score(f)) for f in files]
        
        # Sort by score (highest first)
        scored_files.sort(key=lambda x: x[1], reverse=True)
        
        # The highest quality file is the keeper
        keeper = scored_files[0][0]
        dupes = [f for f, _ in scored_files[1:]]
        
        resolved_dupes[name] = {
            'keeper': keeper,
            'duplicates': dupes,
            'scores': {f: score for f, score in scored_files}
        }
    
    return resolved_dupes

def print_duplicates(duplicates, verbose=False):
    """Display information about the found duplicates."""
    total_duplicates = sum(len(info['duplicates']) for info in duplicates.values())
    print(f"\nFound {len(duplicates)} songs with {total_duplicates} duplicate files")
    
    for name, info in duplicates.items():
        keeper = info['keeper']
        dupes = info['duplicates']
        
        print(f"\n{name}")
        print(f"  KEEP: {os.path.basename(keeper)} [{format_quality(keeper, info['scores'][keeper])}]")
        
        for dupe in dupes:
            print(f"  DUPE: {os.path.basename(dupe)} [{format_quality(dupe, info['scores'][dupe])}]")
            if verbose:
                print(f"        Path: {dupe}")

def format_quality(file_path, score):
    """Format the quality information for display."""
    ext = os.path.splitext(file_path)[1].lower()
    size_kb = os.path.getsize(file_path) / 1024
    
    if size_kb > 1024:
        size_str = f"{size_kb/1024:.1f} MB"
    else:
        size_str = f"{size_kb:.0f} KB"
    
    return f"{ext[1:].upper()}, {size_str}"

def process_duplicates(duplicates, dry_run=True, move_dir=None):
    """Process the duplicate files according to the selected action."""
    if move_dir and not os.path.exists(move_dir):
        os.makedirs(move_dir)
    
    total = sum(len(info['duplicates']) for info in duplicates.values())
    processed = 0
    
    print("\nProcessing duplicates:")
    for name, info in duplicates.items():
        for dupe in info['duplicates']:
            processed += 1
            rel_path = os.path.basename(dupe)
            
            if dry_run:
                if move_dir:
                    print(f"[DRY RUN] Would move: {rel_path} to {move_dir}")
                else:
                    print(f"[DRY RUN] Would delete: {rel_path}")
            else:
                try:
                    if move_dir:
                        # Create a unique filename in the target directory
                        target = os.path.join(move_dir, rel_path)
                        if os.path.exists(target):
                            base, ext = os.path.splitext(rel_path)
                            target = os.path.join(move_dir, f"{base}_{hashlib.md5(dupe.encode()).hexdigest()[:6]}{ext}")
                        
                        shutil.move(dupe, target)
                        print(f"Moved: {rel_path} -> {target}")
                    else:
                        os.remove(dupe)
                        print(f"Deleted: {rel_path}")
                except Exception as e:
                    print(f"Error processing {dupe}: {e}")
    
    if dry_run:
        print(f"\n[DRY RUN] Would process {processed} duplicate files")
    else:
        print(f"\nProcessed {processed} duplicate files")

def main():
    parser = argparse.ArgumentParser(description="Find and manage duplicate music files")
    parser.add_argument("directories", nargs="+", help="Directories to scan for music files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--move", dest="move_dir", help="Move duplicates to this directory instead of deleting")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information about duplicates")
    parser.add_argument("--threshold", type=float, default=0.9, help="Similarity threshold (0.8-1.0)")
    
    args = parser.parse_args()
    
    # Validate directories
    for directory in args.directories:
        if not os.path.isdir(directory):
            print(f"Error: {directory} is not a valid directory")
            return 1
    
    # Find duplicates
    duplicates = find_duplicates(args.directories, args.threshold)
    
    # Display results
    print_duplicates(duplicates, args.verbose)
    
    # Process duplicates if there are any
    if duplicates:
        if not args.dry_run:
            confirmation = input("\nDo you want to proceed with processing these duplicates? (y/n): ")
            if confirmation.lower() != 'y':
                print("Operation cancelled by user")
                return 0
        
        process_duplicates(duplicates, args.dry_run, args.move_dir)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
