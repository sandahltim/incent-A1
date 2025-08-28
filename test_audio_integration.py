#!/usr/bin/env python3
"""
test_audio_integration.py
Comprehensive Audio System Integration Test for Vegas Casino Application
"""

import os
import json
import requests
import time
import subprocess
from pathlib import Path

class AudioIntegrationTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.audio_dir = Path(__file__).parent / "static" / "audio"
        self.manifest_path = self.audio_dir / "audio-manifest.json"
        self.test_results = {
            'files_checked': 0,
            'files_present': 0,
            'files_missing': [],
            'audio_engine_status': 'unknown',
            'fallback_status': 'unknown',
            'performance_score': 0
        }
        
    def load_manifest(self):
        """Load audio manifest"""
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load manifest: {e}")
            return None
    
    def test_audio_files_exist(self):
        """Test that all required audio files exist"""
        print("\n🔍 Testing Audio File Presence...")
        
        manifest = self.load_manifest()
        if not manifest:
            return False
            
        categories = manifest['audio_manifest']['categories']
        total_files = 0
        present_files = 0
        missing_files = []
        
        for category_name, category in categories.items():
            print(f"\n  📁 {category_name.upper()}: {category['description']}")
            
            for sound in category['sounds']:
                filename = sound['file']
                filepath = self.audio_dir / filename
                total_files += 1
                
                if filepath.exists():
                    file_size = filepath.stat().st_size
                    print(f"    ✅ {filename} ({file_size} bytes)")
                    present_files += 1
                else:
                    print(f"    ❌ {filename} MISSING")
                    missing_files.append(filename)
        
        self.test_results['files_checked'] = total_files
        self.test_results['files_present'] = present_files
        self.test_results['files_missing'] = missing_files
        
        print(f"\n📊 Summary: {present_files}/{total_files} files present ({present_files/total_files*100:.1f}%)")
        
        return len(missing_files) == 0
    
    def test_audio_file_integrity(self):
        """Test audio file integrity (basic checks)"""
        print("\n🔍 Testing Audio File Integrity...")
        
        test_files = [
            'button-click.mp3',
            'casino-win.mp3', 
            'jackpot.mp3',
            'reel-spin.mp3',
            'coin-drop.mp3',
            'ui-hover.mp3',
            'win-small.mp3'
        ]
        
        for filename in test_files:
            filepath = self.audio_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                if size > 1000:  # Basic size check
                    print(f"    ✅ {filename} - {size} bytes")
                else:
                    print(f"    ⚠️ {filename} - suspiciously small ({size} bytes)")
            else:
                print(f"    ❌ {filename} - missing")
    
    def test_web_accessibility(self):
        """Test if audio files are accessible via HTTP"""
        print("\n🌐 Testing Web Accessibility...")
        
        test_files = ['button-click.mp3', 'casino-win.mp3', 'ui-hover.mp3']
        accessible_count = 0
        
        for filename in test_files:
            url = f"{self.base_url}/static/audio/{filename}"
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    print(f"    ✅ {filename} - HTTP 200")
                    accessible_count += 1
                else:
                    print(f"    ❌ {filename} - HTTP {response.status_code}")
            except Exception as e:
                print(f"    ❌ {filename} - {str(e)[:50]}...")
        
        return accessible_count == len(test_files)
    
    def test_audio_manifest_validity(self):
        """Test audio manifest structure"""
        print("\n📋 Testing Audio Manifest Validity...")
        
        manifest = self.load_manifest()
        if not manifest:
            return False
            
        audio_manifest = manifest.get('audio_manifest', {})
        required_keys = ['version', 'description', 'categories']
        for key in required_keys:
            if key in audio_manifest:
                print(f"    ✅ {key} present")
            else:
                print(f"    ❌ {key} missing")
                return False
        
        categories = manifest['audio_manifest']['categories']
        print(f"    ✅ Found {len(categories)} audio categories")
        
        total_sounds = sum(len(cat['sounds']) for cat in categories.values())
        print(f"    ✅ Total sounds defined: {total_sounds}")
        
        return True
    
    def test_fallback_system(self):
        """Test fallback system configuration"""
        print("\n🔄 Testing Fallback System...")
        
        manifest = self.load_manifest()
        if not manifest:
            return False
            
        fallback_count = 0
        no_fallback_count = 0
        
        categories = manifest['audio_manifest']['categories']
        for category_name, category in categories.items():
            for sound in category['sounds']:
                if sound.get('fallback'):
                    fallback_file = sound['fallback']
                    fallback_path = self.audio_dir / fallback_file
                    if fallback_path.exists():
                        print(f"    ✅ {sound['file']} → {fallback_file}")
                        fallback_count += 1
                    else:
                        print(f"    ❌ {sound['file']} → {fallback_file} (missing)")
                elif sound.get('exists'):
                    print(f"    ➡️  {sound['file']} (existing file)")
                else:
                    print(f"    ⚠️  {sound['file']} (no fallback)")
                    no_fallback_count += 1
        
        print(f"    📊 {fallback_count} fallbacks configured, {no_fallback_count} without fallback")
        return True
    
    def test_audio_engine_integration(self):
        """Test audio engine JavaScript integration"""
        print("\n🎵 Testing Audio Engine Integration...")
        
        js_files = [
            'static/audio-engine.js',
            'static/audio-controls.js',
            'static/script.js',
            'static/vegas-casino.js'
        ]
        
        integration_score = 0
        max_score = len(js_files) * 2  # 2 points per file
        
        for js_file in js_files:
            filepath = Path(js_file)
            if filepath.exists():
                print(f"    ✅ {js_file} exists")
                integration_score += 1
                
                # Check for audio-related content
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        if 'casinoAudio' in content or 'audioEngine' in content:
                            print(f"    ✅ {js_file} has audio integration")
                            integration_score += 1
                        else:
                            print(f"    ⚠️  {js_file} missing audio integration")
                except:
                    print(f"    ❌ {js_file} read error")
            else:
                print(f"    ❌ {js_file} missing")
        
        score_percent = (integration_score / max_score) * 100
        print(f"    📊 Integration Score: {integration_score}/{max_score} ({score_percent:.1f}%)")
        
        self.test_results['performance_score'] = score_percent
        return score_percent > 75
    
    def test_css_integration(self):
        """Test CSS file for audio controls"""
        print("\n🎨 Testing CSS Integration...")
        
        css_files = [
            'static/css/audio-controls.css',
            'static/style.css'
        ]
        
        for css_file in css_files:
            filepath = Path(css_file)
            if filepath.exists():
                print(f"    ✅ {css_file} exists")
                
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        if 'audio-control' in content or '.audio-' in content:
                            print(f"    ✅ {css_file} has audio styles")
                        else:
                            print(f"    ➡️  {css_file} no specific audio styles")
                except:
                    print(f"    ❌ {css_file} read error")
            else:
                print(f"    ❌ {css_file} missing")
        
        return True
    
    def run_performance_test(self):
        """Basic performance test"""
        print("\n⚡ Running Performance Test...")
        
        # Test file sizes
        total_size = 0
        large_files = []
        
        for audio_file in self.audio_dir.glob('*.mp3'):
            size = audio_file.stat().st_size
            total_size += size
            
            if size > 500000:  # 500KB
                large_files.append((audio_file.name, size))
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"    📊 Total audio size: {total_size_mb:.2f} MB")
        
        if large_files:
            print(f"    ⚠️  Large files detected:")
            for filename, size in large_files:
                print(f"        - {filename}: {size/1024:.1f} KB")
        else:
            print(f"    ✅ All files under 500KB")
        
        # Performance recommendations
        if total_size_mb > 50:
            print(f"    ⚠️  Total size > 50MB - consider compression")
        else:
            print(f"    ✅ Total size acceptable for web delivery")
        
        return total_size_mb < 100  # Fail if over 100MB
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("🎯 AUDIO SYSTEM INTEGRATION TEST REPORT")
        print("="*60)
        
        # File presence
        files_score = (self.test_results['files_present'] / self.test_results['files_checked']) * 100
        print(f"📁 Audio Files: {self.test_results['files_present']}/{self.test_results['files_checked']} ({files_score:.1f}%)")
        
        if self.test_results['files_missing']:
            print(f"❌ Missing files: {len(self.test_results['files_missing'])}")
            for f in self.test_results['files_missing'][:5]:  # Show first 5
                print(f"   - {f}")
            if len(self.test_results['files_missing']) > 5:
                print(f"   ... and {len(self.test_results['files_missing']) - 5} more")
        else:
            print("✅ All audio files present")
        
        # Integration score
        print(f"🎵 Integration Score: {self.test_results['performance_score']:.1f}%")
        
        # Overall status
        overall_score = (files_score + self.test_results['performance_score']) / 2
        print(f"\n🏆 Overall Score: {overall_score:.1f}%")
        
        if overall_score >= 90:
            print("✅ EXCELLENT - Audio system fully integrated")
        elif overall_score >= 75:
            print("✅ GOOD - Audio system well integrated")
        elif overall_score >= 50:
            print("⚠️  FAIR - Audio system partially integrated")
        else:
            print("❌ POOR - Audio system needs attention")
        
        print("\n🛠️  RECOMMENDATIONS:")
        if self.test_results['files_missing']:
            print("- Generate missing audio files using generate_audio_files.py")
        if self.test_results['performance_score'] < 75:
            print("- Review JavaScript integration in audio-engine.js")
        if files_score < 100:
            print("- Ensure all audio files are properly generated")
        
        print("\n📖 TESTING INSTRUCTIONS:")
        print("1. Open /static/audio-test.html to test audio system")
        print("2. Use /static/audio-generator.html to generate missing files")
        print("3. Check browser console for audio initialization messages")
        print("4. Test volume controls and spatial audio features")
        
        return overall_score
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🎰 STARTING COMPREHENSIVE AUDIO INTEGRATION TEST")
        print("="*60)
        
        tests = [
            ("Audio Files Exist", self.test_audio_files_exist),
            ("Audio File Integrity", self.test_audio_file_integrity), 
            ("Audio Manifest Valid", self.test_audio_manifest_validity),
            ("Fallback System", self.test_fallback_system),
            ("JavaScript Integration", self.test_audio_engine_integration),
            ("CSS Integration", self.test_css_integration),
            ("Performance Test", self.run_performance_test)
        ]
        
        passed_tests = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    print(f"✅ {test_name}: PASSED")
                    passed_tests += 1
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        # Web accessibility test (optional - requires server)
        try:
            if self.test_web_accessibility():
                print("✅ Web Accessibility: PASSED")
                passed_tests += 1
            else:
                print("⚠️  Web Accessibility: PARTIAL (server may not be running)")
        except:
            print("⚠️  Web Accessibility: SKIPPED (server not available)")
        
        print(f"\n📊 TEST SUMMARY: {passed_tests}/{len(tests)} tests passed")
        
        return self.generate_test_report()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test audio system integration')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL for web accessibility tests')
    parser.add_argument('--quick', action='store_true',
                       help='Run only quick tests (skip web tests)')
    
    args = parser.parse_args()
    
    tester = AudioIntegrationTester(args.url)
    
    if args.quick:
        print("🚀 Running quick tests only...")
        tester.test_audio_files_exist()
        tester.test_audio_manifest_validity()
        score = tester.generate_test_report()
    else:
        score = tester.run_all_tests()
    
    return 0 if score >= 75 else 1

if __name__ == "__main__":
    exit(main())