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

    # Some tests check for build artifacts, so ensure build exists
    build_dir = Path("build/anki_dictionary_addon")
    if not build_dir.exists():
        print("  ⚠️  Build directory missing, building addon before tests...")
        build_addon()

    try:
        result = subprocess.run([sys.executable, "tests/run_tests.py"], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False


def lint_code():
    """Run code linting"""
    print("🔍 Running code linting...")

    success = True

    # Run flake8
    try:
        print("  Running flake8...")
        result = subprocess.run(["flake8", ".", "--config=.flake8"], check=False)
        if result.returncode != 0:
            success = False
    except FileNotFoundError:
        print("  ⚠️  flake8 not found, skipping...")

    # Check black formatting
    try:
        print("  Checking code formatting with black...")
        result = subprocess.run(
            [
                "black",
                "--check",
                "--diff",
                ".",
                "--exclude",
                "vendor|build|.venv|__pycache__",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("  ⚠️  Code formatting issues found")
            if result.stdout:
                print(result.stdout)
            success = False
        else:
            print("  ✅ Code formatting looks good")
    except FileNotFoundError:
        print("  ⚠️  black not found, skipping...")

    return success


def format_code():
    """Format code with black"""
    print("🎨 Formatting code...")
    try:
        result = subprocess.run(
            ["black", ".", "--exclude", "vendor|build|.venv|__pycache__"], check=False
        )
        if result.returncode == 0:
            print("✅ Code formatted successfully")
            return True
        else:
            print("❌ Code formatting failed")
            return False
    except FileNotFoundError:
        print("❌ black not found. Install with: pip install black")
        return False


def build_addon():
    """Build the addon"""
    print("🔨 Building addon...")
    try:
        result = subprocess.run([sys.executable, "build.py", "all"], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return False


def clean_build():
    """Clean build artifacts"""
    print("🧹 Cleaning build artifacts...")
    try:
        result = subprocess.run([sys.executable, "build.py", "clean"], check=False)
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
                "flake8",
                "black",
                "mypy",
                "toml",
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
    except:
        try:
            import toml

            with open("pyproject.toml", "r") as f:
                config = toml.load(f)
            version = config["project"]["version"]
            name = config["project"]["name"]
            print(f"Name: {name}")
            print(f"Version: {version}")
        except:
            print("Version: Unable to read from pyproject.toml")

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
    except:
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
        # In GitHub Actions, we handle linting separately in the YAML if needed,
        # but here we'll still run it if requested via 'ci' command.
        lint_success = lint_code()

        print("\n3. Running tests...")
        # Ensure we don't clean build before tests if they depend on it
        test_success = run_tests()

        success = lint_success and test_success

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
