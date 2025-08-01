#!/usr/bin/env python3
"""
Local CI simulation script to test the complete workflow
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and check if it succeeds"""
    print(f"\n🔧 {description}...")
    print(f"   Command: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ Success")
        if result.stdout.strip():
            print(f"   📄 Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed with exit code {e.returncode}")
        if e.stdout:
            print(f"   📄 Stdout: {e.stdout}")
        if e.stderr:
            print(f"   📄 Stderr: {e.stderr}")
        return False

def main():
    """Run the complete local CI simulation"""
    print("🚀 Local CI Simulation for Anki Dictionary Addon")
    print("=" * 60)
    
    steps = [
        ("python build.py clean", "Clean previous build artifacts"),
        ("python build.py package", "Build addon package"),
        ("python tests/run_tests.py", "Run test suite"),
        ("ls -la build/", "List build artifacts")
    ]
    
    success_count = 0
    total_steps = len(steps)
    
    for cmd, description in steps:
        if run_command(cmd, description):
            success_count += 1
        else:
            print(f"\n💥 Step failed: {description}")
            break
    
    print("\n" + "=" * 60)
    print("📊 LOCAL CI SIMULATION RESULTS")
    print("=" * 60)
    print(f"✅ Steps passed: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        print("🎉 All steps completed successfully!")
        print("🚀 Your workflow is ready for CI/CD!")
        
        # Show the built package
        package_path = Path("build/anki_dictionary_addon_v0.1.0.ankiaddon")
        if package_path.exists():
            size_mb = package_path.stat().st_size / (1024 * 1024)
            print(f"📦 Package created: {package_path} ({size_mb:.2f} MB)")
        
        return 0
    else:
        print("❌ Some steps failed. Please fix the issues before pushing to CI.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
