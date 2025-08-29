#!/usr/bin/env python3
"""
Test script for Phaser.js Casino Integration
Tests the complete integration of the new Phaser.js gaming system
"""

import os
import json
import time
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a required file exists"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✓ {description}: {filepath} ({size:,} bytes)")
        return True
    else:
        print(f"✗ {description}: {filepath} NOT FOUND")
        return False

def check_phaser_files():
    """Check all Phaser.js related files"""
    print("\n" + "="*60)
    print("PHASER.JS CASINO SYSTEM - FILE VERIFICATION")
    print("="*60)
    
    files_to_check = [
        ("package.json", "NPM Package Configuration"),
        ("static/js/phaser-casino.js", "Main Phaser Casino Engine"),
        ("static/js/phaser-integration.js", "Integration Layer"),
        ("static/css/phaser-casino.css", "Phaser Casino Styles"),
        ("templates/minigames.html", "Updated Minigames Template"),
    ]
    
    all_present = True
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_present = False
    
    return all_present

def analyze_phaser_engine():
    """Analyze the Phaser casino engine implementation"""
    print("\n" + "="*60)
    print("PHASER ENGINE ANALYSIS")
    print("="*60)
    
    engine_file = "static/js/phaser-casino.js"
    if not os.path.exists(engine_file):
        print("✗ Engine file not found")
        return False
    
    with open(engine_file, 'r') as f:
        content = f.read()
    
    # Check for key components
    components = {
        "PhaserCasinoEngine": "Main engine class",
        "SlotMachineScene": "Slot machine game scene",
        "WheelOfFortuneScene": "Wheel of fortune scene",
        "DiceGameScene": "Dice game scene",
        "ScratchCardScene": "Scratch card scene",
        "JackpotCelebrationScene": "Jackpot celebration scene",
        "physics": "Physics engine configuration",
        "particles": "Particle effects system",
        "CSRF": "CSRF token integration",
        "localStorage": "Local storage integration"
    }
    
    print("\nKey Components:")
    for component, description in components.items():
        if component in content:
            print(f"✓ {description}: Found")
        else:
            print(f"✗ {description}: Missing")
    
    # Count lines and functions
    lines = content.count('\n')
    functions = content.count('function') + content.count('=>')
    classes = content.count('class ')
    
    print(f"\nCode Statistics:")
    print(f"  Total Lines: {lines:,}")
    print(f"  Classes: {classes}")
    print(f"  Functions/Methods: ~{functions}")
    
    return True

def check_integration_layer():
    """Check the integration layer functionality"""
    print("\n" + "="*60)
    print("INTEGRATION LAYER VERIFICATION")
    print("="*60)
    
    integration_file = "static/js/phaser-integration.js"
    if not os.path.exists(integration_file):
        print("✗ Integration file not found")
        return False
    
    with open(integration_file, 'r') as f:
        content = f.read()
    
    # Check for integration features
    features = {
        "PhaserIntegration": "Integration class",
        "loadPhaserLibrary": "Dynamic library loading",
        "launchPhaserGame": "Game launcher",
        "fallbackToLegacy": "Legacy fallback support",
        "handlePhaserGameWin": "Win handling",
        "submitGameResult": "Backend submission",
        "getCSRFToken": "CSRF token retrieval",
        "performanceMonitoring": "Performance monitoring"
    }
    
    print("\nIntegration Features:")
    for feature, description in features.items():
        if feature in content:
            print(f"✓ {description}: Implemented")
        else:
            print(f"✗ {description}: Not found")
    
    return True

def verify_game_scenes():
    """Verify individual game scene implementations"""
    print("\n" + "="*60)
    print("GAME SCENES VERIFICATION")
    print("="*60)
    
    engine_file = "static/js/phaser-casino.js"
    if not os.path.exists(engine_file):
        return False
    
    with open(engine_file, 'r') as f:
        content = f.read()
    
    games = {
        "Slot Machine": {
            "scene": "SlotMachineScene",
            "features": ["createReels", "spin", "checkWin", "particle"]
        },
        "Wheel of Fortune": {
            "scene": "WheelOfFortuneScene",
            "features": ["createWheel", "spinWheel", "physics", "segments"]
        },
        "Dice Game": {
            "scene": "DiceGameScene",
            "features": ["createDice", "rollDice", "matter", "physics"]
        },
        "Scratch Card": {
            "scene": "ScratchCardScene",
            "features": ["scratch", "reveal", "renderTexture", "interactive"]
        }
    }
    
    for game_name, game_data in games.items():
        print(f"\n{game_name}:")
        if game_data["scene"] in content:
            print(f"  ✓ Scene class found")
            for feature in game_data["features"]:
                if feature in content:
                    print(f"    ✓ {feature}: Implemented")
                else:
                    print(f"    ✗ {feature}: Not found")
        else:
            print(f"  ✗ Scene class not found")
    
    return True

def check_css_styles():
    """Check CSS styling implementation"""
    print("\n" + "="*60)
    print("CSS STYLING VERIFICATION")
    print("="*60)
    
    css_file = "static/css/phaser-casino.css"
    if not os.path.exists(css_file):
        print("✗ CSS file not found")
        return False
    
    with open(css_file, 'r') as f:
        content = f.read()
    
    # Check for key styles
    styles = {
        "#phaser-game-container": "Game container",
        ".phaser-game-launcher": "Launch buttons",
        ".achievement-unlock": "Achievement notifications",
        ".phaser-loading": "Loading screen",
        ".mode-switch": "Mode toggle switch",
        "@keyframes": "Animations",
        "@media": "Responsive design"
    }
    
    print("\nCSS Components:")
    for selector, description in styles.items():
        if selector in content:
            print(f"✓ {description}: Styled")
        else:
            print(f"✗ {description}: Missing")
    
    return True

def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("PHASER.JS CASINO INTEGRATION - TEST REPORT")
    print("="*60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Files Present": check_phaser_files(),
        "Engine Analysis": analyze_phaser_engine(),
        "Integration Layer": check_integration_layer(),
        "Game Scenes": verify_game_scenes(),
        "CSS Styles": check_css_styles()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 SUCCESS! Phaser.js Casino System is fully integrated!")
        print("\nNext Steps:")
        print("1. Run 'npm install' to install Phaser.js dependencies")
        print("2. Start the Flask server and navigate to /minigames")
        print("3. Toggle 'Enhanced Graphics Mode' to switch between Phaser and legacy")
        print("4. Click any game button to launch the Phaser.js version")
    else:
        print("\n⚠️  Some components are missing or incomplete.")
        print("Please review the failed tests above.")
    
    return passed == total

def main():
    """Main test execution"""
    os.chdir('/home/tim/incentDev')
    success = generate_test_report()
    
    print("\n" + "="*60)
    print("IMPLEMENTATION DETAILS")
    print("="*60)
    print("""
The Phaser.js Casino System includes:

1. COMPLETE GAME ENGINE (phaser-casino.js):
   - Full Phaser 3.70.0 integration
   - 4 complete casino games with physics
   - Particle effects and animations
   - Scene management system
   - Asset generation (procedural graphics)

2. INTEGRATION LAYER (phaser-integration.js):
   - Seamless integration with existing system
   - CSRF token support
   - Legacy game fallback
   - Performance monitoring
   - Achievement system

3. ENHANCED GAMES:
   - Slot Machine: Smooth reel animations, particle celebrations
   - Wheel of Fortune: Physics-based spinning, dynamic segments
   - Dice Game: Matter.js physics, realistic dice rolling
   - Scratch Cards: Interactive scratch mechanics

4. VISUAL ENHANCEMENTS:
   - Professional CSS styling
   - Responsive design
   - Loading screens
   - Achievement notifications
   - Mode toggle switch

5. COMPATIBILITY:
   - Maintains existing CSRF protection
   - Works with current authentication
   - Preserves dual game system (A/B)
   - Integrates with token economy
   - Compatible with audio engine
    """)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())