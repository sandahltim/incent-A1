#!/usr/bin/env python3
"""
Audio System Verification Script
Checks integrity of all audio files and validates the manifest
"""

import json
import os
import subprocess
from pathlib import Path

def check_audio_file(filepath):
    """Check if an audio file exists and is valid."""
    if not os.path.exists(filepath):
        return False, "File not found"
    
    # Check file size
    size = os.path.getsize(filepath)
    if size == 0:
        return False, "File is empty (0 bytes)"
    
    # Check if it's a valid MP3 using ffprobe
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return True, f"Valid MP3 (duration: {duration:.2f}s, size: {size/1024:.1f}KB)"
        else:
            return False, f"Invalid MP3 format: {result.stderr}"
    except Exception as e:
        return False, f"Error checking file: {str(e)}"

def verify_audio_system():
    """Verify the complete audio system."""
    base_dir = "/home/tim/incentDev/static/audio"
    manifest_path = os.path.join(base_dir, "audio-manifest.json")
    
    print("=" * 60)
    print("CASINO AUDIO SYSTEM VERIFICATION")
    print("=" * 60)
    
    # Load manifest
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"✓ Manifest loaded: v{manifest['version']}")
    except Exception as e:
        print(f"✗ Failed to load manifest: {e}")
        return
    
    # Check all priority groups
    all_files = []
    for priority in ['critical', 'important', 'background']:
        if priority in manifest['priorities']:
            all_files.extend(manifest['priorities'][priority])
    
    # Remove duplicates
    all_files = list(set(all_files))
    
    print(f"\nTotal unique files in manifest: {len(all_files)}")
    print("-" * 60)
    
    # Statistics
    stats = {
        'valid': 0,
        'missing': 0,
        'corrupted': 0,
        'total_size': 0
    }
    
    # Check each file
    errors = []
    warnings = []
    
    for filename in sorted(all_files):
        filepath = os.path.join(base_dir, filename)
        is_valid, message = check_audio_file(filepath)
        
        if is_valid:
            stats['valid'] += 1
            stats['total_size'] += os.path.getsize(filepath)
            print(f"✓ {filename}: {message}")
        else:
            if "not found" in message:
                stats['missing'] += 1
                errors.append(f"MISSING: {filename}")
            else:
                stats['corrupted'] += 1
                errors.append(f"CORRUPTED: {filename} - {message}")
            print(f"✗ {filename}: {message}")
    
    # Check for extra files not in manifest
    print("\n" + "-" * 60)
    print("Checking for extra files not in manifest...")
    
    actual_files = set([f for f in os.listdir(base_dir) if f.endswith('.mp3')])
    manifest_files = set(all_files)
    extra_files = actual_files - manifest_files
    
    if extra_files:
        print(f"\nExtra files found (not in manifest):")
        for f in sorted(extra_files):
            filepath = os.path.join(base_dir, f)
            size = os.path.getsize(filepath) / 1024
            print(f"  • {f} ({size:.1f}KB)")
    else:
        print("✓ No extra files found")
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Valid files:     {stats['valid']}/{len(all_files)}")
    print(f"Missing files:   {stats['missing']}")
    print(f"Corrupted files: {stats['corrupted']}")
    print(f"Total size:      {stats['total_size']/1024/1024:.2f} MB")
    
    if errors:
        print("\n⚠️  ERRORS FOUND:")
        for error in errors:
            print(f"  • {error}")
    
    if stats['valid'] == len(all_files):
        print("\n✅ ALL AUDIO FILES VERIFIED SUCCESSFULLY!")
        return True
    else:
        print(f"\n❌ VERIFICATION FAILED: {len(errors)} issues found")
        return False

if __name__ == "__main__":
    success = verify_audio_system()
    exit(0 if success else 1)