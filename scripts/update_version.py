#!/usr/bin/env python3
"""
Update version in pyproject.toml
"""
import sys
import toml
from pathlib import Path

def update_version(new_version):
    """Update version in pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    
    # Read current config
    with open(pyproject_path, "r") as f:
        config = toml.load(f)
    
    # Update version
    config["project"]["version"] = new_version
    
    # Write back
    with open(pyproject_path, "w") as f:
        toml.dump(config, f)
    
    print(f"Updated version to {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        sys.exit(1)
    
    update_version(sys.argv[1])
