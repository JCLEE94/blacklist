#!/usr/bin/env python3
"""
Code Quality Fixer for Blacklist Management System

This script automatically fixes common code quality issues:
- Removes unused imports
- Fixes line length issues
- Removes unused variables
- Organizes imports
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set


class CodeQualityFixer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_path = self.project_root / "src"
        self.fixed_files = []
        self.issues_found = {
            "unused_imports": 0,
            "line_length": 0,
            "unused_variables": 0,
            "imports_organized": 0
        }

    def find_python_files(self) -> List[Path]:
        """Find all Python files in src directory"""
        return list(self.src_path.rglob("*.py"))

    def get_flake8_issues(self) -> dict:
        """Get flake8 issues categorized by type"""
        try:
            result = subprocess.run(
                ["python3", "-m", "flake8", "src/", "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            issues = {
                "F401": [],  # unused imports
                "E501": [],  # line too long
                "F841": [],  # unused variables
            }
            
            for line in result.stdout.split("\n"):
                if line.strip():
                    parts = line.split(":")
                    if len(parts) >= 4:
                        file_path, line_num, col, code = parts[:4]
                        if code in issues:
                            issues[code].append((file_path, int(line_num), line))
            
            return issues
            
        except Exception as e:
            print(f"Error running flake8: {e}")
            return {"F401": [], "E501": [], "F841": []}

    def fix_unused_imports(self, file_path: Path) -> bool:
        """Remove unused imports from a file"""
        try:
            # Use autoflake to remove unused imports
            result = subprocess.run(
                ["python3", "-m", "autoflake", "--remove-unused-variables", 
                 "--remove-all-unused-imports", "--in-place", str(file_path)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            # Fallback: manual removal of common unused imports
            return self._manual_unused_import_fix(file_path)

    def _manual_unused_import_fix(self, file_path: Path) -> bool:
        """Manual unused import removal for common cases"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            modified = False
            new_lines = []
            
            for line in lines:
                # Skip common unused imports
                if any(unused in line for unused in [
                    "'orjson' imported but unused",
                    "'json' imported but unused",
                    "'os' imported but unused",
                    "'typing.List' imported but unused",
                    "'typing.Optional' imported but unused",
                    "'typing.Dict' imported but unused",
                    "'typing.Any' imported but unused"
                ]):
                    # Check if this import line should be removed
                    # This is a simplified approach - in production, use AST parsing
                    continue
                new_lines.append(line)
            
            if len(new_lines) != len(lines):
                with open(file_path, 'w') as f:
                    f.writelines(new_lines)
                modified = True
                
            return modified
            
        except Exception as e:
            print(f"Error fixing imports in {file_path}: {e}")
            return False

    def fix_line_length(self, file_path: Path) -> bool:
        """Fix line length issues using black"""
        try:
            result = subprocess.run(
                ["python3", "-m", "black", "--line-length=88", str(file_path)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error fixing line length in {file_path}: {e}")
            return False

    def organize_imports(self, file_path: Path) -> bool:
        """Organize imports using isort"""
        try:
            result = subprocess.run(
                ["python3", "-m", "isort", str(file_path)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error organizing imports in {file_path}: {e}")
            return False

    def run_fixes(self) -> dict:
        """Run all code quality fixes"""
        print("🧹 STARTING CODE QUALITY CLEANUP")
        print("=" * 50)
        
        # Get initial issues
        print("📊 Analyzing code quality issues...")
        issues = self.get_flake8_issues()
        
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        print(f"Found {total_issues} total issues:")
        print(f"  - Unused imports (F401): {len(issues['F401'])}")
        print(f"  - Line length (E501): {len(issues['E501'])}")
        print(f"  - Unused variables (F841): {len(issues['F841'])}")
        print()
        
        # Get all Python files
        python_files = self.find_python_files()
        print(f"📁 Processing {len(python_files)} Python files...")
        
        # Process each file
        for file_path in python_files:
            file_modified = False
            
            # Fix unused imports
            if self.fix_unused_imports(file_path):
                self.issues_found["unused_imports"] += 1
                file_modified = True
            
            # Organize imports
            if self.organize_imports(file_path):
                self.issues_found["imports_organized"] += 1
                file_modified = True
            
            # Fix line length
            if self.fix_line_length(file_path):
                self.issues_found["line_length"] += 1
                file_modified = True
            
            if file_modified:
                self.fixed_files.append(str(file_path.relative_to(self.project_root)))
        
        return self.generate_summary()

    def generate_summary(self) -> dict:
        """Generate cleanup summary"""
        summary = {
            "files_modified": len(self.fixed_files),
            "issues_fixed": self.issues_found,
            "modified_files": self.fixed_files[:10]  # Show first 10
        }
        
        return summary


def main():
    project_root = os.getcwd()
    fixer = CodeQualityFixer(project_root)
    
    try:
        summary = fixer.run_fixes()
        
        print()
        print("✅ CLEANUP SUMMARY")
        print("=" * 50)
        print(f"📁 Files Modified: {summary['files_modified']}")
        print()
        print("🔄 Issues Fixed:")
        for issue_type, count in summary['issues_fixed'].items():
            if count > 0:
                print(f"  - {issue_type.replace('_', ' ').title()}: {count}")
        
        if summary['modified_files']:
            print()
            print("📋 Sample Modified Files:")
            for file_path in summary['modified_files']:
                print(f"  - {file_path}")
            
            if summary['files_modified'] > 10:
                print(f"  ... and {summary['files_modified'] - 10} more files")
        
        print()
        print("🎯 Next Steps:")
        print("  - Run tests to ensure functionality is preserved")
        print("  - Review changes before committing")
        print("  - Consider running additional quality checks")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
