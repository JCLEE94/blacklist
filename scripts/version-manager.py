#!/usr/bin/env python3
"""
Comprehensive Version Management System for Blacklist Project

This script manages version bumping across the entire codebase with:
- Automatic detection of commit types (fix/feat/BREAKING CHANGE)
- Updates ALL version references in the codebase
- Validates version consistency
- Creates version commits and tags

Author: Automated Version Management System
Version: 1.0.0
"""

import os
import re
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class VersionBumpType(Enum):
    """Version bump types based on conventional commits"""
    PATCH = "patch"      # fix: commits
    MINOR = "minor"      # feat: commits  
    MAJOR = "major"      # BREAKING CHANGE: commits

@dataclass
class VersionInfo:
    """Version information container"""
    major: int
    minor: int
    patch: int
    
    @classmethod
    def from_string(cls, version_str: str) -> 'VersionInfo':
        """Parse version from string like '1.0.37'"""
        parts = version_str.strip().split('.')
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version_str}")
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def bump(self, bump_type: VersionBumpType) -> 'VersionInfo':
        """Create new version with bump applied"""
        if bump_type == VersionBumpType.MAJOR:
            return VersionInfo(self.major + 1, 0, 0)
        elif bump_type == VersionBumpType.MINOR:
            return VersionInfo(self.major, self.minor + 1, 0)
        else:  # PATCH
            return VersionInfo(self.major, self.minor, self.patch + 1)

class VersionManager:
    """Main version management class"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version_file = project_root / "version.txt"
        self.current_version = self._read_current_version()
        
    def _read_current_version(self) -> VersionInfo:
        """Read current version from version.txt"""
        if not self.version_file.exists():
            # Create initial version file
            initial_version = VersionInfo(1, 0, 0)
            self._write_version_file(initial_version)
            return initial_version
        
        with open(self.version_file, 'r') as f:
            version_str = f.read().strip()
            return VersionInfo.from_string(version_str)
    
    def _write_version_file(self, version: VersionInfo) -> None:
        """Write version to version.txt"""
        with open(self.version_file, 'w') as f:
            f.write(str(version))
    
    def detect_version_bump_type(self) -> VersionBumpType:
        """Detect version bump type from git commits since last tag"""
        try:
            # Get commits since last tag
            result = subprocess.run(
                ['git', 'log', '--oneline', '--pretty=format:%s', 'HEAD', '--not', '--tags'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.returncode != 0:
                # No tags yet, check all commits from main
                result = subprocess.run(
                    ['git', 'log', '--oneline', '--pretty=format:%s', 'HEAD'],
                    capture_output=True, text=True, cwd=self.project_root
                )
            
            commit_messages = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Analyze commit messages for conventional commit patterns
            has_breaking = False
            has_feat = False
            has_fix = False
            
            for msg in commit_messages:
                if not msg.strip():
                    continue
                    
                # Check for BREAKING CHANGE
                if 'BREAKING CHANGE:' in msg or msg.startswith('!'):
                    has_breaking = True
                # Check for feat:
                elif msg.startswith('feat:') or msg.startswith('feat('):
                    has_feat = True
                # Check for fix:
                elif msg.startswith('fix:') or msg.startswith('fix('):
                    has_fix = True
            
            # Return highest priority bump type
            if has_breaking:
                return VersionBumpType.MAJOR
            elif has_feat:
                return VersionBumpType.MINOR
            elif has_fix:
                return VersionBumpType.PATCH
            else:
                # Default to patch if no conventional commits found
                return VersionBumpType.PATCH
                
        except Exception as e:
            print(f"Warning: Could not detect version bump type: {e}")
            return VersionBumpType.PATCH
    
    def find_version_references(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find all version references in the codebase"""
        version_patterns = [
            # Direct version patterns
            rf'\b{re.escape(str(self.current_version))}\b',
            # Version in quotes  
            rf'["\']v?{re.escape(str(self.current_version))}["\']',
            # Version in comments
            rf'#.*{re.escape(str(self.current_version))}',
            # Docker image tags
            rf':{re.escape(str(self.current_version))}',
        ]
        
        files_to_check = [
            # Python files
            '**/*.py',
            # Configuration files
            '**/*.json', '**/*.yml', '**/*.yaml', '**/*.toml',
            # Docker files
            '**/Dockerfile*', '**/docker-compose*.yml',
            # Documentation
            '**/*.md', '**/*.rst', '**/*.txt',
            # Scripts
            '**/*.sh', '**/*.ps1',
        ]
        
        references = {}
        
        for pattern in files_to_check:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and not self._should_skip_file(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        matching_lines = []
                        for line_num, line in enumerate(lines, 1):
                            for version_pattern in version_patterns:
                                if re.search(version_pattern, line, re.IGNORECASE):
                                    matching_lines.append((line_num, line.strip()))
                                    break
                        
                        if matching_lines:
                            references[str(file_path.relative_to(self.project_root))] = matching_lines
                            
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")
        
        return references
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during version updates"""
        skip_patterns = [
            '.git/', '__pycache__/', '.pytest_cache/', 'node_modules/',
            '.venv/', 'venv/', '.env', 'logs/', 'data/', 'instance/',
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.pdf', '.zip', '.tar', '.gz', '.bz2',
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def update_version_references(self, new_version: VersionInfo) -> int:
        """Update all version references in the codebase"""
        references = self.find_version_references()
        updated_files = 0
        
        for file_path_str, line_refs in references.items():
            file_path = self.project_root / file_path_str
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace version references
                old_version_str = str(self.current_version)
                new_version_str = str(new_version)
                
                # Multiple replacement patterns for different contexts
                replacements = [
                    (old_version_str, new_version_str),
                    (f'v{old_version_str}', f'v{new_version_str}'),
                    (f'"{old_version_str}"', f'"{new_version_str}"'),
                    (f"'{old_version_str}'", f"'{new_version_str}'"),
                    (f':{old_version_str}', f':{new_version_str}'),
                ]
                
                original_content = content
                for old, new in replacements:
                    content = content.replace(old, new)
                
                # Only write if content changed
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated_files += 1
                    print(f"✅ Updated {file_path_str}")
                
            except Exception as e:
                print(f"❌ Error updating {file_path_str}: {e}")
        
        return updated_files
    
    def validate_version_consistency(self) -> bool:
        """Validate that all version references are consistent"""
        references = self.find_version_references()
        
        if not references:
            print("✅ No version references found to validate")
            return True
        
        inconsistent_files = []
        current_version_str = str(self.current_version)
        
        for file_path, line_refs in references.items():
            for line_num, line in line_refs:
                if current_version_str not in line:
                    inconsistent_files.append(f"{file_path}:{line_num}")
        
        if inconsistent_files:
            print(f"❌ Version inconsistencies found in {len(inconsistent_files)} locations:")
            for location in inconsistent_files[:10]:  # Show first 10
                print(f"   {location}")
            if len(inconsistent_files) > 10:
                print(f"   ... and {len(inconsistent_files) - 10} more")
            return False
        
        print(f"✅ All {len(references)} files have consistent version references")
        return True
    
    def create_version_commit(self, new_version: VersionInfo, bump_type: VersionBumpType) -> bool:
        """Create git commit for version bump"""
        try:
            # Stage all changed files
            subprocess.run(['git', 'add', '.'], cwd=self.project_root, check=True)
            
            # Create commit message
            commit_msg = f"chore: bump version to {new_version} ({bump_type.value})"
            
            # Commit changes
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=self.project_root, check=True
            )
            
            # Create git tag
            tag_name = f"v{new_version}"
            subprocess.run(
                ['git', 'tag', '-a', tag_name, '-m', f"Release {new_version}"],
                cwd=self.project_root, check=True
            )
            
            print(f"✅ Created commit and tag: {tag_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error creating version commit: {e}")
            return False
    
    def bump_version(self, force_bump_type: Optional[VersionBumpType] = None) -> bool:
        """Main version bump workflow"""
        print(f"🔄 Starting version bump process...")
        print(f"📍 Current version: {self.current_version}")
        
        # Detect or use forced bump type
        bump_type = force_bump_type or self.detect_version_bump_type()
        print(f"📈 Bump type: {bump_type.value}")
        
        # Calculate new version
        new_version = self.current_version.bump(bump_type)
        print(f"🎯 New version: {new_version}")
        
        # Update version file
        self._write_version_file(new_version)
        print(f"✅ Updated {self.version_file}")
        
        # Update all version references
        updated_count = self.update_version_references(new_version)
        print(f"✅ Updated {updated_count} files with version references")
        
        # Update current version for validation
        self.current_version = new_version
        
        # Validate consistency
        if not self.validate_version_consistency():
            print("❌ Version validation failed")
            return False
        
        print(f"🎉 Version bump completed successfully: {self.current_version}")
        return True
    
    def interactive_bump(self) -> bool:
        """Interactive version bump with user input"""
        print(f"🔄 Interactive Version Bump")
        print(f"📍 Current version: {self.current_version}")
        print(f"📋 Recent commits:")
        
        # Show recent commits
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-5', '--pretty=format:%h %s'],
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    print(f"   {line}")
        except:
            print("   (Could not retrieve commit history)")
        
        print()
        print("🎯 Select bump type:")
        print("   1. patch (1.0.X) - Bug fixes")
        print("   2. minor (1.X.0) - New features")  
        print("   3. major (X.0.0) - Breaking changes")
        print("   4. auto   - Detect from commits")
        print("   5. cancel - Exit without changes")
        
        while True:
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                bump_type = VersionBumpType.PATCH
                break
            elif choice == '2':
                bump_type = VersionBumpType.MINOR
                break
            elif choice == '3':
                bump_type = VersionBumpType.MAJOR
                break
            elif choice == '4':
                bump_type = self.detect_version_bump_type()
                print(f"🔍 Auto-detected bump type: {bump_type.value}")
                break
            elif choice == '5':
                print("❌ Version bump cancelled")
                return False
            else:
                print("❌ Invalid choice. Please enter 1-5.")
        
        # Confirm bump
        new_version = self.current_version.bump(bump_type)
        confirm = input(f"\n🎯 Bump version to {new_version}? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Version bump cancelled")
            return False
        
        return self.bump_version(bump_type)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Version Management System")
    parser.add_argument('--project-root', type=Path, default=Path.cwd(),
                       help='Project root directory (default: current directory)')
    parser.add_argument('--bump-type', choices=['patch', 'minor', 'major', 'auto'],
                       help='Force specific bump type')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode with user prompts')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate version consistency')
    parser.add_argument('--show-references', action='store_true',
                       help='Show all version references in codebase')
    parser.add_argument('--no-commit', action='store_true',
                       help='Skip creating git commit and tag')
    
    args = parser.parse_args()
    
    # Initialize version manager
    vm = VersionManager(args.project_root)
    
    if args.validate_only:
        # Just validate consistency
        success = vm.validate_version_consistency()
        sys.exit(0 if success else 1)
    
    if args.show_references:
        # Show all version references
        references = vm.find_version_references()
        print(f"📋 Found version references in {len(references)} files:")
        for file_path, line_refs in references.items():
            print(f"\n📄 {file_path}:")
            for line_num, line in line_refs:
                print(f"   {line_num:4}: {line}")
        sys.exit(0)
    
    if args.interactive:
        # Interactive mode
        success = vm.interactive_bump()
    else:
        # Automatic mode
        force_bump_type = None
        if args.bump_type and args.bump_type != 'auto':
            force_bump_type = VersionBumpType(args.bump_type)
        
        success = vm.bump_version(force_bump_type)
    
    # Create git commit if requested and successful
    if success and not args.no_commit:
        bump_type = VersionBumpType(args.bump_type) if args.bump_type and args.bump_type != 'auto' else vm.detect_version_bump_type()
        commit_success = vm.create_version_commit(vm.current_version, bump_type)
        success = success and commit_success
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()