#!/usr/bin/env python3
"""
Release automation script for Anki Dictionary Addon

This script helps automate the release process:
1. Update version in pyproject.toml
2. Commit the version change
3. Create and push a git tag
4. GitHub Actions will then build and create the release automatically
"""

import subprocess
import sys
import re
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml"""
    try:
        # Try tomllib first (Python 3.11+)
        try:
            import tomllib

            with open("pyproject.toml", "rb") as f:
                config = tomllib.load(f)
        except ImportError:
            # Fallback to toml library
            import toml

            with open("pyproject.toml", "r") as f:
                config = toml.load(f)

        return config["project"]["version"]
    except Exception as e:
        print(f"❌ Failed to read current version: {e}")
        return None


def update_version(new_version):
    """Update version in pyproject.toml"""
    try:
        # Read the file
        with open("pyproject.toml", "r") as f:
            content = f.read()

        # Update version using regex
        pattern = r'version\s*=\s*["\'][^"\']*["\']'
        replacement = f'version = "{new_version}"'
        new_content = re.sub(pattern, replacement, content)

        # Write back to file
        with open("pyproject.toml", "w") as f:
            f.write(new_content)

        print(f"✅ Updated version in pyproject.toml to {new_version}")
        return True
    except Exception as e:
        print(f"❌ Failed to update version: {e}")
        return False


def validate_version(version):
    """Validate version format (semantic versioning)"""
    pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$"
    if not re.match(pattern, version):
        print(f"❌ Invalid version format: {version}")
        print("   Expected format: X.Y.Z or X.Y.Z-suffix (e.g., 1.2.3 or 1.2.3-beta)")
        return False
    return True


def check_git_status():
    """Check if git working directory is clean"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )

        if result.stdout.strip():
            print("⚠️  Git working directory is not clean:")
            print(result.stdout)
            return False
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to check git status")
        return False


def commit_version_change(version):
    """Commit version change to git"""
    try:
        # Add the pyproject.toml file
        subprocess.run(["git", "add", "pyproject.toml"], check=True)

        # Commit the change
        commit_message = f"Bump version to {version}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        print(f"✅ Committed version change: {commit_message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to commit version change: {e}")
        return False


def create_git_tag(version):
    """Create and push git tag"""
    tag_name = f"v{version}"

    try:
        # Create annotated tag
        tag_message = f"Release {tag_name}"
        subprocess.run(["git", "tag", "-a", tag_name, "-m", tag_message], check=True)

        print(f"✅ Created tag {tag_name}")
        return tag_name
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create tag: {e}")
        return None


def push_changes(tag_name):
    """Push commits and tags to remote"""
    try:
        # Push commits
        subprocess.run(["git", "push"], check=True)
        print("✅ Pushed commits to remote")

        # Push tag
        subprocess.run(["git", "push", "origin", tag_name], check=True)
        print(f"✅ Pushed tag {tag_name} to remote")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to push to remote: {e}")
        return False


def check_github_actions():
    """Check if GitHub Actions workflow exists"""
    workflow_file = Path(".github/workflows/ci-cd.yml")
    if not workflow_file.exists():
        print("⚠️  GitHub Actions workflow not found at .github/workflows/ci-cd.yml")
        print("   The release process may not work automatically.")
        return False
    return True


def main():
    """Main release function"""
    print("🚀 Anki Dictionary Addon - Release Script")
    print("=" * 50)

    if len(sys.argv) != 2:
        print("Usage: python scripts/release.py <version>")
        print()
        print("Examples:")
        print("  python scripts/release.py 1.2.3")
        print("  python scripts/release.py 2.0.0-beta")
        print()
        print("This script will:")
        print("  1. Update version in pyproject.toml")
        print("  2. Commit the version change")
        print("  3. Create and push a git tag")
        print("  4. GitHub Actions will build and create the release")
        return 1

    new_version = sys.argv[1]

    # Validate version format
    if not validate_version(new_version):
        return 1

    # Get current version
    current_version = get_current_version()
    if current_version is None:
        return 1

    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    print()

    # Check if we're trying to release the same version
    if current_version == new_version:
        print(f"⚠️  Version {new_version} is the same as current version")
        confirm = input("Continue anyway? (y/N): ")
        if confirm.lower() != "y":
            print("Release cancelled")
            return 0

    # Check GitHub Actions workflow
    if not check_github_actions():
        confirm = input("Continue without GitHub Actions? (y/N): ")
        if confirm.lower() != "y":
            print("Release cancelled")
            return 0

    # Check git status (allow dirty for version update)
    print("🔍 Checking git status...")

    # Confirm with user
    print("\nThis will:")
    print(f"  • Update version in pyproject.toml to {new_version}")
    print(f"  • Commit the change")
    print(f"  • Create tag v{new_version}")
    print(f"  • Push to remote repository")
    print(f"  • Trigger GitHub Actions to build and release")
    print()

    confirm = input("Continue with release? (y/N): ")
    if confirm.lower() != "y":
        print("Release cancelled")
        return 0

    print("\n🔄 Starting release process...")

    # Update version
    if not update_version(new_version):
        return 1

    # Commit version change
    if not commit_version_change(new_version):
        return 1

    # Create tag
    tag_name = create_git_tag(new_version)
    if not tag_name:
        return 1

    # Push changes
    if not push_changes(tag_name):
        return 1

    print("\n" + "=" * 50)
    print(f"🎉 Release {new_version} initiated successfully!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. GitHub Actions will now build the addon automatically")
    print("  2. Go to GitHub → Releases to create the release from the tag")
    print("  3. The built .ankiaddon and standalone.zip will be attached")
    print()
    print("Links:")
    print(
        "  • Actions: https://github.com/Alexander-Nilsson/Anki-Dictionary-Addon/actions"
    )
    print(
        "  • Releases: https://github.com/Alexander-Nilsson/Anki-Dictionary-Addon/releases"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
