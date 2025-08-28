#!/usr/bin/env python3
"""
Audio Asset Optimization Script for A1 Rent-It Incentive System
Implements progressive audio loading and compression for better performance
"""

import os
import json
from pathlib import Path

def create_progressive_audio_loader():
    """Create optimized progressive audio loading system"""
    
    audio_dir = Path('/home/tim/incentDev/static/audio')
    
    # Audio loading priorities - critical sounds load first
    audio_priorities = {
        "critical": [
            "button-click.mp3",
            "coin-drop.mp3", 
            "casino-win.mp3"
        ],
        "important": [
            "jackpot.mp3",
            "reel-spin.mp3",
            "slot-pull.mp3"
        ],
        "background": [
            # All other audio files
        ]
    }
    
    # Get all audio files and categorize them
    all_audio_files = [f.name for f in audio_dir.glob('*.mp3') if f.is_file()]
    
    # Add uncategorized files to background
    for audio_file in all_audio_files:
        if not any(audio_file in priority_list for priority_list in audio_priorities.values()):
            audio_priorities["background"].append(audio_file)
    
    # Create optimized audio manifest
    audio_manifest = {
        "version": "4.0.0",
        "description": "Optimized Progressive Audio Loading System",
        "loading_strategy": "progressive",
        "priorities": audio_priorities,
        "settings": {
            "preload_critical": True,
            "lazy_load_background": True,
            "compression_enabled": True,
            "cache_duration": 3600
        }
    }
    
    # Write updated manifest
    manifest_path = audio_dir / 'audio-manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(audio_manifest, f, indent=2)
    
    print(f"✅ Created optimized audio manifest: {manifest_path}")
    
    # Create progressive loading JavaScript
    progressive_loader = '''
// Progressive Audio Loader - Version 4.0.0
// Optimized for A1 Rent-It Incentive System

class ProgressiveAudioLoader {
    constructor() {
        this.audioContext = null;
        this.loadedBuffers = new Map();
        this.loadingPromises = new Map();
        this.loadingQueue = [];
        this.isLoading = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Initialize Web Audio API
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Load audio manifest
            const manifest = await this.loadManifest();
            this.priorities = manifest.priorities;
            
            // Start progressive loading
            await this.startProgressiveLoading();
            
            console.log('✅ Progressive Audio Loader initialized');
        } catch (error) {
            console.error('❌ Progressive Audio Loader failed:', error);
        }
    }
    
    async loadManifest() {
        try {
            const response = await fetch('/static/audio/audio-manifest.json');
            return await response.json();
        } catch (error) {
            console.warn('Audio manifest not found, using defaults');
            return {
                priorities: {
                    critical: ['button-click.mp3', 'coin-drop.mp3', 'casino-win.mp3'],
                    important: ['jackpot.mp3', 'reel-spin.mp3'],
                    background: []
                }
            };
        }
    }
    
    async startProgressiveLoading() {
        // Load critical sounds immediately
        await this.loadPriorityGroup('critical');
        
        // Load important sounds after a short delay
        setTimeout(() => this.loadPriorityGroup('important'), 1000);
        
        // Load background sounds when page is idle
        if (window.requestIdleCallback) {
            window.requestIdleCallback(() => this.loadPriorityGroup('background'));
        } else {
            setTimeout(() => this.loadPriorityGroup('background'), 3000);
        }
    }
    
    async loadPriorityGroup(priority) {
        const files = this.priorities[priority] || [];
        const loadPromises = files.map(file => this.loadAudioFile(file));
        
        try {
            await Promise.all(loadPromises);
            console.log(`✅ Loaded ${priority} audio files (${files.length} files)`);
        } catch (error) {
            console.warn(`⚠️ Some ${priority} audio files failed to load:`, error);
        }
    }
    
    async loadAudioFile(filename) {
        // Avoid loading same file multiple times
        if (this.loadedBuffers.has(filename) || this.loadingPromises.has(filename)) {
            return this.loadingPromises.get(filename) || Promise.resolve();
        }
        
        const loadPromise = this.fetchAndDecodeAudio(filename);
        this.loadingPromises.set(filename, loadPromise);
        
        try {
            const buffer = await loadPromise;
            this.loadedBuffers.set(filename, buffer);
            this.loadingPromises.delete(filename);
            return buffer;
        } catch (error) {
            console.warn(`Failed to load audio: ${filename}`, error);
            this.loadingPromises.delete(filename);
            throw error;
        }
    }
    
    async fetchAndDecodeAudio(filename) {
        const response = await fetch(`/static/audio/${filename}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const arrayBuffer = await response.arrayBuffer();
        return await this.audioContext.decodeAudioData(arrayBuffer);
    }
    
    // Play audio with fallback
    async playAudio(filename, options = {}) {
        try {
            // Try to get pre-loaded buffer
            let buffer = this.loadedBuffers.get(filename);
            
            // If not loaded, load it now (blocking)
            if (!buffer) {
                console.log(`Loading audio on-demand: ${filename}`);
                buffer = await this.loadAudioFile(filename);
            }
            
            // Play the audio
            const source = this.audioContext.createBufferSource();
            const gainNode = this.audioContext.createGain();
            
            source.buffer = buffer;
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            gainNode.gain.value = options.volume || 0.5;
            source.start();
            
            return source;
        } catch (error) {
            console.warn(`Audio playback failed: ${filename}`, error);
            return null;
        }
    }
    
    // Get loading statistics
    getStats() {
        return {
            loaded: this.loadedBuffers.size,
            loading: this.loadingPromises.size,
            totalCritical: this.priorities.critical?.length || 0,
            totalImportant: this.priorities.important?.length || 0,
            totalBackground: this.priorities.background?.length || 0
        };
    }
}

// Global instance
window.progressiveAudioLoader = new ProgressiveAudioLoader();

// Export for compatibility with existing audio engine
if (window.CasinoAudioEngine) {
    window.CasinoAudioEngine.prototype.progressiveLoader = window.progressiveAudioLoader;
}
'''
    
    # Write progressive loader
    loader_path = Path('/home/tim/incentDev/static/progressive-audio-loader.js')
    with open(loader_path, 'w') as f:
        f.write(progressive_loader)
    
    print(f"✅ Created progressive audio loader: {loader_path}")
    
    return audio_manifest

def optimize_audio_files():
    """Check audio file sizes and suggest optimizations"""
    audio_dir = Path('/home/tim/incentDev/static/audio')
    
    print("🎵 Audio File Analysis:")
    print("-" * 40)
    
    total_size = 0
    empty_files = []
    large_files = []
    
    for audio_file in audio_dir.glob('*.mp3'):
        size = audio_file.stat().st_size
        total_size += size
        
        if size == 0:
            empty_files.append(audio_file.name)
        elif size > 500000:  # > 500KB
            large_files.append((audio_file.name, size))
        
        print(f"📁 {audio_file.name}: {size:,} bytes")
    
    print("\n📊 Audio Summary:")
    print(f"   Total files: {len(list(audio_dir.glob('*.mp3')))}")
    print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")
    print(f"   Empty files: {len(empty_files)}")
    print(f"   Large files: {len(large_files)}")
    
    if empty_files:
        print(f"\n⚠️ Empty audio files found: {', '.join(empty_files)}")
        print("   Consider removing or replacing these files")
    
    if large_files:
        print(f"\n🔍 Large files (>500KB):")
        for filename, size in large_files:
            print(f"   {filename}: {size / 1024:.1f} KB")
        print("   Consider compressing these files")
    
    return {
        'total_size': total_size,
        'empty_files': empty_files,
        'large_files': large_files
    }

def main():
    """Main optimization function"""
    print("🎵 Audio Optimization Starting")
    print("=" * 50)
    
    # Analyze current audio files
    audio_stats = optimize_audio_files()
    
    # Create progressive loading system
    audio_manifest = create_progressive_audio_loader()
    
    print("\n🎯 Optimization Complete!")
    print("=" * 50)
    print("Next steps:")
    print("1. Add progressive-audio-loader.js to base.html template")
    print("2. Update audio-engine.js to use progressive loading")
    print("3. Test audio loading performance")
    print("4. Consider compressing large audio files")
    
    # Calculate potential savings
    if audio_stats['total_size'] > 0:
        potential_savings = len(audio_stats['empty_files']) * 0.1 + len(audio_stats['large_files']) * 0.3
        print(f"\n💡 Potential performance improvement: {potential_savings:.0f}%")

if __name__ == "__main__":
    main()