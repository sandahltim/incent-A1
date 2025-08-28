#!/usr/bin/env python3
"""
Test Runner Script for Employee Incentive System
Version: 1.0.0

This script provides an easy way to run different test suites and configurations.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result"""
    if description:
        print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Success: {description}")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ Failed: {description}")
            if result.stderr:
                print("STDERR:", result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: {description}")
        return False
    except Exception as e:
        print(f"💥 Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Employee Incentive System Tests")
    
    # Test selection arguments
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--performance', action='store_true', help='Run performance tests only')
    parser.add_argument('--mobile', action='store_true', help='Run mobile tests only')
    parser.add_argument('--api', action='store_true', help='Run API tests only')
    parser.add_argument('--games', action='store_true', help='Run game tests only')
    parser.add_argument('--voting', action='store_true', help='Run voting tests only')
    parser.add_argument('--database', action='store_true', help='Run database tests only')
    parser.add_argument('--security', action='store_true', help='Run security tests only')
    
    # Coverage options
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--coverage-html', action='store_true', help='Generate HTML coverage report')
    
    # Output options
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet output')
    parser.add_argument('--junit', action='store_true', help='Generate JUnit XML report')
    parser.add_argument('--html', action='store_true', help='Generate HTML test report')
    
    # Performance options
    parser.add_argument('--benchmark', action='store_true', help='Run benchmark tests')
    parser.add_argument('--profile', action='store_true', help='Profile test execution')
    
    # Development options
    parser.add_argument('--install-deps', action='store_true', help='Install test dependencies first')
    parser.add_argument('--check-deps', action='store_true', help='Check test dependencies')
    parser.add_argument('--lint', action='store_true', help='Run linting before tests')
    
    # Specific test options
    parser.add_argument('--file', type=str, help='Run specific test file')
    parser.add_argument('--function', type=str, help='Run specific test function')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🧪 Employee Incentive System - Test Runner")
    print("=" * 50)
    
    success = True
    
    # Install dependencies if requested
    if args.install_deps:
        if not run_command(['pip', 'install', '-r', 'requirements-test.txt'], 
                          "Installing test dependencies"):
            return 1
    
    # Check dependencies if requested
    if args.check_deps:
        if not run_command(['pip', 'check'], "Checking dependencies"):
            print("⚠️ Dependency issues found, but continuing...")
    
    # Run linting if requested
    if args.lint:
        print("\n🔍 Running code quality checks...")
        
        # Check if flake8 is available
        try:
            subprocess.run(['flake8', '--version'], capture_output=True, check=True)
            run_command(['flake8', 'app.py', 'incentive_service.py', 'tests/'], 
                       "Running flake8 linting")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ flake8 not available, skipping linting")
    
    # Build pytest command
    pytest_cmd = ['pytest']
    
    # Add verbosity options
    if args.verbose:
        pytest_cmd.append('-v')
    elif args.quiet:
        pytest_cmd.append('-q')
    
    # Add parallel execution
    if args.parallel:
        pytest_cmd.extend(['-n', str(args.workers)])
    
    # Add coverage options
    if args.coverage or args.coverage_html:
        pytest_cmd.extend(['--cov=.', '--cov-report=term-missing'])
        
        if args.coverage_html:
            pytest_cmd.append('--cov-report=html')
    
    # Add report generation
    if args.junit:
        pytest_cmd.extend(['--junitxml=tests/junit.xml'])
    
    if args.html:
        pytest_cmd.extend(['--html=tests/report.html', '--self-contained-html'])
    
    # Add benchmark options
    if args.benchmark:
        pytest_cmd.extend(['--benchmark-only', '--benchmark-sort=mean'])
    
    # Add profiling
    if args.profile:
        pytest_cmd.append('--profile')
    
    # Add test selection
    test_markers = []
    test_paths = []
    
    if args.unit:
        test_markers.append('unit')
    elif args.integration:
        test_markers.append('integration')
    elif args.performance:
        test_markers.append('performance')
    elif args.mobile:
        test_markers.append('mobile')
    elif args.api:
        test_markers.append('api')
    elif args.games:
        test_markers.append('games')
    elif args.voting:
        test_markers.append('voting')
    elif args.database:
        test_markers.append('database')
    elif args.security:
        test_markers.append('security')
    
    # Add specific file or function
    if args.file:
        if args.function:
            test_paths.append(f"{args.file}::{args.function}")
        else:
            test_paths.append(args.file)
    elif args.function:
        test_paths.append(f"tests/::*::{args.function}")
    
    # Add marker selection
    if test_markers:
        pytest_cmd.extend(['-m', ' or '.join(test_markers)])
    
    # Add test paths or default to tests directory
    if test_paths:
        pytest_cmd.extend(test_paths)
    elif not args.all and not test_markers:
        # Default to running specific test categories based on what's available
        if Path('tests').exists():
            pytest_cmd.append('tests/')
    
    # Run the tests
    description = "Running tests"
    if test_markers:
        description += f" ({', '.join(test_markers)})"
    if test_paths:
        description += f" for {', '.join(test_paths)}"
    
    print(f"\n🧪 {description}")
    print("Command:", ' '.join(pytest_cmd))
    
    try:
        result = subprocess.run(pytest_cmd, timeout=600)  # 10 minute timeout
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            
            # Open coverage report if generated
            if args.coverage_html and Path('htmlcov/index.html').exists():
                print("📊 Coverage report generated: htmlcov/index.html")
            
            # Open HTML report if generated
            if args.html and Path('tests/report.html').exists():
                print("📋 Test report generated: tests/report.html")
                
        else:
            print(f"\n❌ Tests failed with exit code: {result.returncode}")
            success = False
            
    except subprocess.TimeoutExpired:
        print("\n⏰ Tests timed out after 10 minutes")
        success = False
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        success = False
    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        success = False
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("🎉 Test run completed successfully!")
        return 0
    else:
        print("💔 Test run completed with failures")
        return 1


if __name__ == '__main__':
    exit(main())