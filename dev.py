#!/usr/bin/env python3
"""
Development helper script for Anki Dictionary Addon

This script provides common development tasks in one place.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Run the test suite"""
    print("🧪 Running test suite...")

    is_ci = os.environ.get("GITHUB_ACTIONS") == "true"

    # Unit tests (fast, mocked, no network)
    unit_cmd = [
        "uv",
        "run",
        "pytest",
        "tests/",
        "-p",
        "no:qt",
        "-p",
        "no:xvfb",
        "-m",
        "not integration and not network",
    ]
    if is_ci:
        unit_cmd.extend(["--tb=short", "-v"])

    try:
        result = subprocess.run(unit_cmd, check=False)
        if result.returncode != 0:
            return False
    except Exception as e:
        print(f"❌ Unit tests failed: {e}")
        return False

    # Integration tests (need real anki runtime — skip if not available)
    print("\n🧪 Running integration tests...")
    int_cmd = [
        "uv",
        "run",
        "pytest",
        "tests/integration/",
        "-p",
        "no:qt",
        "-p",
        "no:xvfb",
        "--ignore=tests/integration/test_smoke_pytest_anki.py",
    ]
    if is_ci:
        int_cmd.extend(["--tb=short", "-v"])

    try:
        result = subprocess.run(int_cmd, check=False)
        if result.returncode not in (0, 5):  # 5 = all tests skipped
            return False
    except Exception as e:
        print(f"⚠️  Integration tests could not run: {e}")

    # pytest-anki2 smoketest (needs pytest-qt, forked process)
    print("\n🧪 Running pytest-anki2 smoketest...")
    smoke_cmd = [
        "uv",
        "run",
        "pytest",
        "tests/integration/test_smoke_pytest_anki.py",
    ]
    if is_ci:
        smoke_cmd.extend(["--tb=short", "-v"])

    try:
        result = subprocess.run(smoke_cmd, check=False)
        if result.returncode not in (0, 5):  # 5 = all tests skipped
            return False
    except Exception as e:
        print(f"⚠️  pytest-anki2 smoketest could not run: {e}")

    return True


def lint_code():
    """Run code linting"""
    print("🔍 Running code linting...")

    success = True

    try:
        print("  Running ruff check...")
        result = subprocess.run(["uv", "run", "ruff", "check", "."], check=False)
        if result.returncode != 0:
            success = False
    except FileNotFoundError:
        print("  ⚠️  ruff not found, skipping...")

    try:
        print("  Checking code formatting with ruff format...")
        result = subprocess.run(
            ["uv", "run", "ruff", "format", "--check", "."],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("  ⚠️  Formatting issues found")
            if result.stdout:
                print(result.stdout)
            success = False
        else:
            print("  ✅ Code formatting looks good")
    except FileNotFoundError:
        print("  ⚠️  ruff not found, skipping...")

    return success


def type_check():
    """Run type checking with ty"""
    print("🔎 Running type checker...")
    try:
        result = subprocess.run(
            ["uvx", "ty", "check", "."],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("  ✅ No type errors found")
            return True
        else:
            error_count = result.stdout.count("error[")
            print(f"  ⚠️  {error_count} type errors found")
            if error_count > 0:
                for line in result.stdout.splitlines()[-5:]:
                    print(f"     {line}")
            return False
    except FileNotFoundError:
        print("  ⚠️  ty not found. Install with: uv tool install ty")
        return False


def format_code():
    """Format code with ruff"""
    print("🎨 Formatting code...")
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "format", "."],
            check=False,
        )
        if result.returncode == 0:
            print("✅ Code formatted successfully")
            return True
        else:
            print("❌ Code formatting failed")
            return False
    except FileNotFoundError:
        print("❌ ruff not found. Install with: pip install ruff")
        return False


def build_addon():
    """Build the addon"""
    print("🔨 Building addon...")
    try:
        result = subprocess.run(["uv", "run", "python", "build.py", "all"], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return False


def clean_build():
    """Clean build artifacts"""
    print("🧹 Cleaning build artifacts...")
    try:
        result = subprocess.run(
            ["uv", "run", "python", "build.py", "clean"], check=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Clean failed: {e}")
        return False


def check_dependencies():
    """Check if all dependencies are installed"""
    print("📦 Checking dependencies...")

    missing_deps = []

    # Required for development
    dev_deps = ["pytest"]

    for dep in dev_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} (missing)")
            missing_deps.append(dep)

    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install " + " ".join(missing_deps))
        return False
    else:
        print("✅ All development dependencies are installed")
        return True


def install_dev_deps():
    """Install development dependencies"""
    print("📦 Installing development dependencies...")
    try:
        # Try with uv first
        result = subprocess.run(
            ["uv", "sync", "--dev"], check=False, capture_output=True
        )
        if result.returncode == 0:
            print("✅ Dependencies installed with uv")
            return True

        # Fallback to pip
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pytest",
                "pytest-cov",
                "ruff",
            ],
            check=False,
        )

        if result.returncode == 0:
            print("✅ Dependencies installed with pip")
            return True
        else:
            print("❌ Failed to install dependencies")
            return False
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False


def show_project_info():
    """Show project information"""
    print("ℹ️  Project Information")
    print("=" * 50)

    # Get version
    try:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        version = config["project"]["version"]
        name = config["project"]["name"]
        print(f"Name: {name}")
        print(f"Version: {version}")
    except ImportError:
        print("Version: Unable to read from pyproject.toml (tomllib not available)")

    # Check git status
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"Git branch: {result.stdout.strip()}")

        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            print("Git status: Working directory has changes")
        else:
            print("Git status: Working directory clean")
    except Exception:
        print("Git status: Unable to check")

    # Check build status
    build_dir = Path("build")
    if build_dir.exists():
        ankiaddon_files = list(build_dir.glob("*.ankiaddon"))
        zip_files = list(build_dir.glob("*.zip"))
        print(
            f"Built packages: {len(ankiaddon_files)} .ankiaddon, {len(zip_files)} .zip"
        )
    else:
        print("Built packages: None (run 'python dev.py build')")


def main():
    """Main development helper function"""
    if len(sys.argv) < 2:
        print("🔧 Anki Dictionary Addon - Development Helper")
        print("=" * 50)
        print("Usage: python dev.py [command]")
        print()
        print("Commands:")
        print("  test       - Run test suite")
        print("  lint       - Run code linting")
        print("  typecheck  - Run type checking")
        print("  format     - Format code with black")
        print("  build      - Build addon and standalone packages")
        print("  clean      - Clean build artifacts")
        print("  deps       - Check development dependencies")
        print("  install    - Install development dependencies")
        print("  info       - Show project information")
        print("  ci         - Run CI checks (test + lint)")
        print()
        print("Examples:")
        print("  python dev.py test         # Run tests")
        print("  python dev.py ci           # Run all CI checks")
        print("  python dev.py build        # Build everything")
        return 0

    command = sys.argv[1]
    success = True

    if command == "test":
        success = run_tests()
    elif command == "lint":
        success = lint_code()
    elif command == "typecheck":
        success = type_check()
    elif command == "format":
        success = format_code()
    elif command == "build":
        success = build_addon()
    elif command == "clean":
        success = clean_build()
    elif command == "deps":
        success = check_dependencies()
    elif command == "install":
        success = install_dev_deps()
    elif command == "info":
        show_project_info()
    elif command == "ci":
        print("🚀 Running CI checks...")
        print("=" * 30)

        is_ci = os.environ.get("GITHUB_ACTIONS") == "true"

        if not is_ci:
            print("\n1. Checking dependencies...")
            if not check_dependencies():
                print("Installing missing dependencies...")
                install_dev_deps()

        print("\n2. Running linting...")
        lint_success = lint_code()

        print("\n3. Running type checking...")
        type_success = type_check()

        print("\n4. Running tests...")
        # Ensure we don't clean build before tests if they depend on it
        test_success = run_tests()

        success = lint_success and type_success and test_success

        print("\n" + "=" * 30)
        if success:
            print("✅ All CI checks passed!")
        else:
            print("❌ Some CI checks failed")
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python dev.py' to see available commands.")
        success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
