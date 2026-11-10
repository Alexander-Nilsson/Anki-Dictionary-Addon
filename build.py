#!/usr/bin/env python3
"""
Build script for the Anki Dictionary Addon

This script helps build and package the addon for distribution.
It handles dependency installation and file bundling.
"""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def get_project_config():
    """Get project configuration from pyproject.toml"""
    try:
        # Try tomllib first (Python 3.11+)
        try:
            import tomllib

            with open("pyproject.toml", "rb") as f:
                config = tomllib.load(f)
        except ImportError:
            # Fallback to toml library
            import toml

            with open("pyproject.toml") as f:
                config = toml.load(f)

        return config
    except Exception as e:
        print(f"Warning: Could not read config from pyproject.toml: {e}")
        return {"project": {"version": "0.1.0", "name": "Anki Dictionary"}}


def get_version():
    """Get version from pyproject.toml"""
    return get_project_config()["project"].get("version", "0.1.0")


def run_pip_command(args, env=None):
    """Run a pip command using 'uv pip', mapping flags correctly."""
    try:
        # User requested to always use uv pip
        # We need to map some flags because uv pip is stricter than pip
        mapped_args = []
        skip_next = False
        for _i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue

            if arg == "-t":
                mapped_args.append("--target")
            elif arg == "-r":
                mapped_args.append("--requirements")
            elif arg == "--platform":
                mapped_args.append("--python-platform")
            elif arg == "--no-compile":
                # uv doesn't have --no-compile, it's the default unless --compile-bytecode is passed
                pass
            else:
                mapped_args.append(arg)

        cmd = ["uv", "pip"] + mapped_args
        return subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    except FileNotFoundError:
        print(
            "❌ 'uv' not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        )
        raise
    except subprocess.CalledProcessError as e:
        # Re-raise to be handled by caller
        raise e


def install_curl_cffi(vendor_dir):
    """Download and extract curl_cffi per platform (DDG image search needs
    browser TLS impersonation on every OS — plain requests gets HTTP 403)."""
    print("📦 Downloading platform-specific curl_cffi (via pip --platform)...")

    # curl_cffi uses abi3, but its CFFI dependency needs Anki's Python ABI.
    # uv resolves --python-platform from Rust target triples (not wheel tags)
    # and accepts exactly one per invocation.
    platforms = [
        {"name": "mac_arm64", "platform": "aarch64-apple-darwin"},
        {"name": "mac_x86_64", "platform": "x86_64-apple-darwin"},
        {"name": "linux_x86_64", "platform": "x86_64-manylinux2014"},
        {"name": "win_amd64", "platform": "x86_64-pc-windows-msvc"},
    ]

    for p in platforms:
        dest = vendor_dir / p["name"]
        dest.mkdir(parents=True, exist_ok=True)

        print(f"   Installing curl_cffi for {p['name']}...")
        try:
            # Resolve native dependencies for Anki's Python, not the build host.
            run_pip_command(
                [
                    "install",
                    "curl_cffi==0.7.4",
                    "-t",
                    str(dest),
                    "--platform",
                    p["platform"],
                    "--python-version",
                    "3.13",
                    "--only-binary=:all:",
                    "--no-compile",
                ]
            )

            print(f"   ✓ curl_cffi for {p['name']} completed")
        except Exception as e:
            raise RuntimeError(f"Could not bundle curl_cffi for {p['name']}") from e


def install_macos_curl_cffi(vendor_dir):
    """Backward-compat wrapper (now covers all platforms)."""
    install_curl_cffi(vendor_dir)


def install_dependencies(addon_dir):
    """Install dependencies into vendor directory"""
    print("📦 Installing dependencies...")

    config = get_project_config()
    dependencies = config["project"].get("dependencies", [])

    # Filter dependencies to bundle
    # We exclude PyQt (provided by Anki), Pillow (provided by Anki),
    # and system-specific binary wheels if we can rely on Anki
    # We bundle: pynput
    # We exclude: pyqt6*, requests (Anki has it), pyobjc* (Anki has it)

    to_install = []
    for dep in dependencies:
        name = dep.split(">=")[0].split("==")[0].split(";")[0].strip()
        if name.lower() in ["pynput", "beautifulsoup4"]:
            to_install.append(dep)
        elif name.lower() in ["requests", "urllib3"]:
            # Anki provides requests, but if users experience SSL/version issues,
            # we might consider bundling it in the future.
            pass

    vendor_dir = addon_dir / "vendor"
    if vendor_dir.exists():
        shutil.rmtree(vendor_dir)
    vendor_dir.mkdir()

    if to_install:
        print(f"   Installing: {', '.join(to_install)}")

        # Create a requirements file
        req_file = addon_dir / "requirements-vendor.txt"
        with open(req_file, "w") as f:
            for dep in to_install:
                f.write(f"{dep}\n")

        try:
            run_pip_command(
                [
                    "install",
                    "-t",
                    str(vendor_dir),
                    "-r",
                    str(req_file),
                    "--no-compile",
                ]
            )
            print("   ✓ Dependencies installed successfully")

            # Cleanup requirements file
            req_file.unlink()

        except Exception as e:
            print(f"   ❌ Error installing dependencies: {e}")
            raise
    else:
        print("   No standard dependencies to bundle.")

    # Always install platform-specific curl_cffi (all OSes need it for DDG)
    install_macos_curl_cffi(vendor_dir)


def create_user_files_structure(addon_dir):
    """Create the user_files directory structure"""
    print("📂 Creating user_files structure...")

    user_files = addon_dir / "user_files"
    user_files.mkdir(exist_ok=True)

    # Create subdirectories
    dirs = [
        "db",
        "db/frequency",
        "db/hsk",
        "db/conjugation",
        "dictionaries",
        "fonts",
        "media",
        "themes",
    ]

    for d in dirs:
        (user_files / d).mkdir(exist_ok=True)

    print("   ✓ Created directory structure")


def generate_manifest():
    """Generate manifest.json from pyproject.toml data"""
    project_config = get_project_config()["project"]

    # macOS-specific requirements (extracted for manifest)
    dependencies = project_config.get("dependencies", [])

    for dep in dependencies:
        if "pyobjc" in dep and "darwin" in dep:
            pass

    manifest_data = {
        "package": project_config.get("name", "Anki Dictionary")
        .replace("-", " ")
        .title(),
        "name": project_config.get("name", "Anki Dictionary").replace("-", " ").title(),
        # "requirements": macos_requirements
    }

    manifest_path = Path("build") / "anki_dictionary_addon" / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=4)

    print("   ✓ Generated manifest.json")
    return manifest_path


def build_web_ui(addon_dir: Path):
    """Build the Svelte UI and copy the bundled HTML pages into the addon.

    The Svelte apps live in ``web/`` and are compiled with Vite into single
    self-contained HTML files (inlined JS + CSS): ``web/dist/dictionary.html``
    (results shell), ``web/dist/settings.html`` (settings window) and
    ``web/dist/exporter.html`` (card exporter). They are
    copied to ``assets/web/`` inside the addon package so the Python side can
    find them at runtime. All three pages are required; failures stop the build.
    """
    print("🌐 Building Svelte web UI...")

    web_dir = Path("web")
    if not web_dir.exists():
        raise RuntimeError(
            "web/ directory is required to build the settings and exporter screens"
        )

    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError(
            "npm is required to build the dictionary, settings and exporter screens"
        )

    try:
        subprocess.run([npm, "ci"], cwd=str(web_dir), check=True, capture_output=True)
        subprocess.run(
            [npm, "run", "build"], cwd=str(web_dir), check=True, capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Web UI build failed: {e}")
        if e.stdout:
            print(f"      stdout: {e.stdout.decode(errors='replace')[:2000]}")
        if e.stderr:
            print(f"      stderr: {e.stderr.decode(errors='replace')[:2000]}")
        raise RuntimeError("Required web UI build failed") from e

    target_dir = addon_dir / "assets" / "web"
    target_dir.mkdir(parents=True, exist_ok=True)

    pages = {
        "dictionary.html": "dictionary.html",
        "settings.html": "settings.html",
        "exporter.html": "exporter.html",
    }
    copied = False
    for src_name, dst_name in pages.items():
        bundled = web_dir / "dist" / src_name
        if not bundled.exists():
            raise RuntimeError(f"Required web UI page missing after build: {bundled}")
        shutil.copy2(bundled, target_dir / dst_name)
        print(f"   ✓ Copied Svelte bundle to {target_dir / dst_name}")
        copied = True
    return copied


def build_addon():
    """Build the addon for Anki installation"""
    print("🔨 Building Anki Dictionary Addon...")

    version = get_version()
    print(f"   Version: {version}")

    # Create build directory
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()

    addon_dir = build_dir / "anki_dictionary_addon"
    addon_dir.mkdir()

    # Copy essential files for Anki addon
    # Note: user_files and vendor are handled separately
    essential_files = [
        "__init__.py",
        "config.json",
        "src/",
        "assets/",
    ]

    for item in essential_files:
        src = Path(item)
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, addon_dir / src.name)
                print(f"   ✓ Copied directory: {item}")
            else:
                shutil.copy2(src, addon_dir / src.name)
                print(f"   ✓ Copied file: {item}")
        else:
            print(f"   ⚠️  Skipped missing: {item}")

    # Clean config.json in build directory
    config_path = addon_dir / "config.json"
    if config_path.exists():
        print("   🧹 Cleaning configuration in build...")
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Reset every key that can carry a developer's local state.
        config.update(
            {
                "config_version": 2,
                "DictionaryGroups": {},
                "ExportTemplates": {},
                "ImageFields": [],
                "currentGroup": "All",
                "currentTemplate": False,
                "currentDeck": False,
                "dictSizePos": [0, 0, 800, 600],
                "exporterSizePos": None,
                "theme": "light",
                "dictOnStart": False,
                "forvo_enabled": True,
                "forvo_language": "en",
                "forvo_limit": 3,
                "ForvoFields": [],
                "ForvoAddType": "add",
                "imageSearchRegion": "United States",
                "language_defaults": {},
                "last_seen_version": "",
                "hide_release_notes": False,
                "restore_session": False,
                "session_terms": [],
                "exporterLastTags": "",
                "llm_enabled": False,
                "llm_api_key": "",
                "llm_base_url": "https://api.openai.com/v1/chat/completions",
                "llm_model": "gpt-4o-mini",
                "llm_prompt": (
                    "Provide a concise dictionary definition for the word: {term}"
                ),
                "llm_timeout": 20,
            }
        )
        for dead_key in (
            "hsk_mode",
            "jReadingCards",
            "jReadingEdit",
            "globalHotkeys",
            "openOnGlobal",
            "autoAddCards",
        ):
            config.pop(dead_key, None)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print("   ✓ Configuration reset to defaults")

    # Create user_files structure
    create_user_files_structure(addon_dir)

    # Generate manifest.json
    generate_manifest()

    # Install dependencies
    install_dependencies(addon_dir)

    # Create empty database using separate script
    db_path = addon_dir / "user_files" / "db" / "dictionaries.sqlite"
    print("   Creating empty database...")
    try:
        subprocess.run(
            [sys.executable, "scripts/create_empty_db.py", str(db_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("   ✓ Database creation completed")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error creating database: {e}")
        # Continue even if DB creation fails (user might create it at runtime).

    # Create default themes.json using separate script
    themes_path = addon_dir / "user_files" / "themes" / "themes.json"
    print("   Creating default themes.json...")
    try:
        subprocess.run(
            [sys.executable, "scripts/create_default_themes.py", str(themes_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("   ✓ Themes.json creation completed")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error creating themes.json: {e}")

    # Build and bundle the Svelte UI last (it only needs assets/ + src/ present).
    build_web_ui(addon_dir)
    validate_build(addon_dir)
    print(f"✅ Addon built in: {addon_dir}")

    return addon_dir


def validate_build(addon_dir: Path) -> None:
    """Reject incomplete packages even when packaging an existing build."""
    missing = []
    for page in ("dictionary.html", "settings.html", "exporter.html"):
        path = addon_dir / "assets" / "web" / page
        if not path.is_file() or not path.stat().st_size:
            missing.append(str(path))
    for platform in ("win_amd64", "mac_arm64", "mac_x86_64", "linux_x86_64"):
        vendor = addon_dir / "vendor" / platform
        for package in ("curl_cffi", "cffi", "certifi"):
            if not (vendor / package / "__init__.py").is_file():
                missing.append(str(vendor / package))
        if not any((vendor / "curl_cffi").glob("_wrapper*.pyd")) and not any(
            (vendor / "curl_cffi").glob("_wrapper*.so")
        ):
            missing.append(str(vendor / "curl_cffi" / "_wrapper native module"))
        if platform == "win_amd64" and not any(
            (vendor / "curl_cffi.libs").glob("*.dll")
        ):
            missing.append(str(vendor / "curl_cffi.libs"))
        suffix = "*.pyd" if platform == "win_amd64" else "*.so"
        if not any(vendor.glob("_cffi_backend" + suffix)):
            missing.append(str(vendor / "_cffi_backend native module"))
    if missing:
        raise RuntimeError(
            "Build is incomplete; missing required files: " + ", ".join(missing)
        )


def create_ankiaddon_package():
    """Create .ankiaddon package file"""
    print("📦 Creating .ankiaddon package...")

    build_dir = Path("build")
    addon_dir = build_dir / "anki_dictionary_addon"

    if not addon_dir.exists():
        print("❌ Build directory not found. Run build first.")
        return None

    validate_build(addon_dir)
    version = get_version()
    package_name = f"anki_dictionary_addon_v{version}.ankiaddon"
    package_path = build_dir / package_name

    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_dir):
            # Write directories (including empty ones)
            for d in dirs:
                dir_path = Path(root) / d
                arc_path = dir_path.relative_to(addon_dir)
                zf.write(dir_path, str(arc_path) + "/")
            # Write files
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(addon_dir)
                zf.write(file_path, arc_path)

    print(f"✅ Package created: {package_path}")
    return package_path


def clean():
    """Clean build artifacts"""
    print("🧹 Cleaning build artifacts...")

    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("   ✓ Removed build directory")

    # Clean Python cache
    for cache_dir in Path(".").rglob("__pycache__"):
        shutil.rmtree(cache_dir)

    print("✅ Clean completed")


def main():
    """Main build script"""
    if len(sys.argv) < 2:
        print("Usage: python build.py [command]")
        print("Commands:")
        print("  build    - Build addon for Anki")
        print("  package  - Create .ankiaddon package")
        print("  all      - Build addon and package")
        print("  clean    - Clean build artifacts")
        return

    command = sys.argv[1]

    if command == "clean":
        clean()
    elif command == "build":
        build_addon()
    elif command == "package":
        build_addon()
        create_ankiaddon_package()
    elif command == "all":
        clean()
        build_addon()
        create_ankiaddon_package()
        print("\n🎉 Build completed!")
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()
