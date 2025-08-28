#!/usr/bin/env python3
"""
Asset Optimization Script for A1 Rent-It Incentive System
Minifies JavaScript and CSS files for production performance
"""

import os
import gzip
import shutil
from pathlib import Path

try:
    from cssmin import cssmin
    from jsmin import jsmin
except ImportError:
    print("Installing required packages...")
    os.system("pip install cssmin jsmin")
    from cssmin import cssmin
    from jsmin import jsmin

def minify_file(input_path, output_path, minifier_func, file_type):
    """Minify a single file"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_size = len(content)
        minified_content = minifier_func(content)
        minified_size = len(minified_content)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(minified_content)
        
        # Create gzipped version for nginx serving
        with open(str(output_path) + '.gz', 'wb') as f:
            f.write(gzip.compress(minified_content.encode('utf-8')))
        
        compression_ratio = ((original_size - minified_size) / original_size) * 100
        print(f"✅ {file_type}: {input_path}")
        print(f"   Original: {original_size:,} bytes")
        print(f"   Minified: {minified_size:,} bytes") 
        print(f"   Saved: {compression_ratio:.1f}%")
        print()
        
    except Exception as e:
        print(f"❌ Error minifying {input_path}: {e}")

def optimize_assets():
    """Main optimization function"""
    static_dir = Path('/home/tim/incentDev/static')
    
    print("🚀 Starting Asset Optimization")
    print("=" * 50)
    
    # JavaScript files to minify
    js_files = [
        'script.js',
        'audio-engine.js', 
        'audio-controls.js',
        'confetti.js'
    ]
    
    # CSS files to minify  
    css_files = [
        'style.css',
        'admin.css',
        'audio-ui.css'
    ]
    
    print("📜 Minifying JavaScript Files:")
    print("-" * 30)
    
    for js_file in js_files:
        input_path = static_dir / js_file
        output_path = static_dir / f"{js_file.replace('.js', '.min.js')}"
        
        if input_path.exists():
            minify_file(input_path, output_path, jsmin, 'JavaScript')
        else:
            print(f"⚠️  File not found: {input_path}")
    
    print("🎨 Minifying CSS Files:")
    print("-" * 30)
    
    for css_file in css_files:
        input_path = static_dir / css_file
        output_path = static_dir / f"{css_file.replace('.css', '.min.css')}"
        
        if input_path.exists():
            minify_file(input_path, output_path, cssmin, 'CSS')
        else:
            print(f"⚠️  File not found: {input_path}")
    
    print("🎯 Optimization Complete!")
    print("=" * 50)
    print("Next steps:")
    print("1. Update templates to use .min.css and .min.js files")
    print("2. Configure nginx to serve .gz files when available")
    print("3. Test the application with minified assets")

if __name__ == "__main__":
    optimize_assets()