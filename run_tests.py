#!/usr/bin/env python3
"""
Local test runner script - simulates what Jenkins would run
Usage: python run_tests.py [backend|frontend|integration|all]
"""
import subprocess
import sys
import os
import time

def run_command(cmd, cwd=None):
    """Run command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {cmd}")
    print('='*60)
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    results = {}
    
    if mode in ["backend", "all"]:
        print("\n" + "="*60)
        print("BACKEND UNIT TESTS")
        print("="*60)
        results["backend_unit"] = run_command(
            "python -m pytest backend/tests/test_api.py -v --tb=short",
            cwd=project_root
        )
    
    if mode in ["integration", "all"]:
        print("\n" + "="*60)
        print("INTEGRATION TESTS")
        print("="*60)
        results["integration"] = run_command(
            "python -m pytest backend/tests/test_integration.py -v --tb=short",
            cwd=project_root
        )
    
    if mode in ["frontend", "all"]:
        print("\n" + "="*60)
        print("FRONTEND TESTS")
        print("="*60)
        frontend_path = os.path.join(project_root, "frontend")
        results["frontend"] = run_command("flutter test", cwd=frontend_path)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
