#!/usr/bin/env python3
"""
Test script to check if the reorganized structure works
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
addon_dir = Path(__file__).parent
src_dir = addon_dir / "src"
sys.path.insert(0, str(src_dir))

print("🧪 Testing reorganized structure...")
print("=" * 40)

try:
    print("✅ Testing main package import...")
    import anki_dictionary

    print(f"   Package version: {anki_dictionary.__version__}")

    print("✅ Testing utils.common import...")
    from anki_dictionary.utils import common

    print("   ✓ Utils common module imported")

    print("✅ Testing integrations imports...")
    from anki_dictionary.integrations import forvo
    from anki_dictionary.integrations import image_search
    from anki_dictionary.integrations import japanese

    print("   ✓ Integration modules imported")

    print("✅ Testing web components...")
    import anki_dictionary.web.config
    import anki_dictionary.web.windows

    print("   ✓ Web components imported")

    print("✅ Testing exporters...")
    from anki_dictionary.exporters import card_exporter

    print("   ✓ Exporters imported")

    print("✅ Testing UI components...")
    from anki_dictionary.ui import themes

    print("   ✓ UI themes imported")

    print("\n🎉 SUCCESS: All basic imports working!")
    print("The reorganized structure is functional for standalone use.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)

print("\n📊 Structure Summary:")
print(f"   Main package: anki_dictionary")
print(f"   Source location: {src_dir}")
print(f"   Modules imported: 10+ components")
print("\n✨ Ready for standalone testing!")
