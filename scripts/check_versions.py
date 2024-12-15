#!/usr/bin/env python3
"""Check that versions in pyproject.toml and __init__.py match."""
import tomli
import re
from pathlib import Path

def get_pyproject_version():
    """Get version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    with open(pyproject_path, "rb") as f:
        pyproject = tomli.load(f)
    return pyproject["project"]["version"]

def get_init_version():
    """Get version from __init__.py."""
    init_path = Path("llm_dump/__init__.py")
    if not init_path.exists():
        raise FileNotFoundError("llm_dump/__init__.py not found")
    
    content = init_path.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Version not found in __init__.py")
    return match.group(1)

def main():
    """Main function."""
    try:
        pyproject_version = get_pyproject_version()
        init_version = get_init_version()
        
        if pyproject_version != init_version:
            print(f"Version mismatch:")
            print(f"  pyproject.toml: {pyproject_version}")
            print(f"  __init__.py: {init_version}")
            return 1
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 