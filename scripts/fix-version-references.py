#!/usr/bin/env python3
"""
Fix Version References Script

This script updates all existing version references in the codebase
to match the current version in version.txt (1.0.37).

It finds and replaces old version numbers (like 1.0.37) with the current version.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def read_current_version(project_root: Path) -> str:
    """Read current version from version.txt"""
    version_file = project_root / "version.txt"
    if not version_file.exists():
        print("❌ Error: version.txt not found")
        sys.exit(1)

    with open(version_file, "r") as f:
        return f.read().strip()


def find_old_version_references(
    project_root: Path, current_version: str
) -> Dict[str, List[Tuple[int, str, str]]]:
    """Find old version references that don't match current version"""

    # Common old versions to look for
    old_versions = ["1.0.37", "1.0.37", "1.0.37", "1.0.37", "1.0.37"]

    # Remove current version from search list
    if current_version in old_versions:
        old_versions.remove(current_version)

    # File patterns to check
    file_patterns = [
        "**/*.py",
        "**/*.md",
        "**/*.yml",
        "**/*.yaml",
        "**/*.json",
        "**/*.sh",
        "**/*.txt",
        "**/Dockerfile*",
        "**/*.toml",
    ]

    skip_patterns = [
        ".git/",
        "__pycache__/",
        ".pytest_cache/",
        "node_modules/",
        ".venv/",
        "venv/",
        "logs/",
        "data/",
        "instance/",
        ".pyc",
        ".pyo",
        ".jpg",
        ".png",
        ".gif",
        ".ico",
    ]

    references = {}

    for pattern in file_patterns:
        for file_path in project_root.glob(pattern):
            if file_path.is_file() and not any(
                skip in str(file_path) for skip in skip_patterns
            ):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    file_changes = []
                    for line_num, line in enumerate(lines, 1):
                        for old_version in old_versions:
                            if old_version in line and current_version not in line:
                                # Create the replacement line
                                new_line = line.replace(old_version, current_version)
                                file_changes.append(
                                    (line_num, line.strip(), new_line.strip())
                                )
                                break

                    if file_changes:
                        relative_path = str(file_path.relative_to(project_root))
                        references[relative_path] = file_changes

                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {e}")

    return references


def apply_version_fixes(
    project_root: Path,
    references: Dict[str, List[Tuple[int, str, str]]],
    current_version: str,
) -> int:
    """Apply version fixes to files"""

    fixed_files = 0
    old_versions = ["1.0.37", "1.0.37", "1.0.37", "1.0.37", "1.0.37"]

    for file_path_str, changes in references.items():
        file_path = project_root / file_path_str

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Apply all old version replacements
            for old_version in old_versions:
                if old_version != current_version:
                    content = content.replace(old_version, current_version)

            # Only write if content changed
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixed_files += 1
                print(f"✅ Fixed {file_path_str}")

        except Exception as e:
            print(f"❌ Error fixing {file_path_str}: {e}")

    return fixed_files


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix version references in codebase")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()

    print("🔧 Version Reference Fixer")
    print(f"📁 Project root: {args.project_root}")

    # Read current version
    current_version = read_current_version(args.project_root)
    print(f"📍 Current version: {current_version}")

    # Find old version references
    print("🔍 Searching for old version references...")
    references = find_old_version_references(args.project_root, current_version)

    if not references:
        print("✅ No old version references found - all versions are consistent")
        return

    print(f"📋 Found old version references in {len(references)} files:")

    total_changes = 0
    for file_path, changes in references.items():
        print(f"\n📄 {file_path}:")
        for line_num, old_line, new_line in changes:
            print(f"   {line_num:4}: {old_line}")
            print(f"   {' '*4}→ {new_line}")
            total_changes += 1

    print(f"\n📊 Total changes needed: {total_changes}")

    if args.dry_run:
        print("🔍 Dry run mode - no changes made")
        return

    # Confirm changes
    confirm = input(f"\n🎯 Apply {total_changes} version fixes? (y/N): ").strip().lower()
    if confirm != "y":
        print("❌ Version fixes cancelled")
        return

    # Apply fixes
    print("🔧 Applying version fixes...")
    fixed_files = apply_version_fixes(args.project_root, references, current_version)

    print(f"\n🎉 Version fixes completed!")
    print(f"✅ Fixed {fixed_files} files")
    print(f"📍 All versions updated to: {current_version}")

    # Suggest next steps
    print("\n💡 Next steps:")
    print("   1. Review changes: git diff")
    print("   2. Test the application")
    print(
        "   3. Commit changes: git add . && git commit -m 'fix: update version references'"
    )
    print("   4. Setup git hooks: bash scripts/setup-git-hooks.sh")


if __name__ == "__main__":
    main()
