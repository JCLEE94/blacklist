#!/usr/bin/env python3
"""
Duplicate Code Finder for Blacklist Management System

Identifies and reports duplicate code patterns:
- Identical functions
- Similar import patterns
- Repeated code blocks
- Redundant files
"""

import ast
import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DuplicateCodeFinder:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_path = self.project_root / "src"
        self.function_hashes = defaultdict(list)
        self.import_patterns = defaultdict(list)
        self.file_similarities = []

    def find_python_files(self) -> List[Path]:
        """Find all Python files in src directory"""
        return list(self.src_path.rglob("*.py"))

    def extract_functions(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract function definitions from a Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get function signature and body
                    func_name = node.name
                    func_body = ast.unparse(node) if hasattr(ast, "unparse") else ""
                    functions.append((func_name, func_body))

            return functions

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []

    def extract_imports(self, file_path: Path) -> List[str]:
        """Extract import statements from a Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"from {module} import {alias.name}")

            return imports

        except Exception as e:
            print(f"Error extracting imports from {file_path}: {e}")
            return []

    def get_content_hash(self, content: str) -> str:
        """Generate hash for content"""
        return hashlib.md5(content.encode()).hexdigest()

    def find_duplicate_functions(self) -> Dict[str, List[str]]:
        """Find functions with identical implementations"""
        python_files = self.find_python_files()

        for file_path in python_files:
            functions = self.extract_functions(file_path)

            for func_name, func_body in functions:
                if func_body:  # Skip empty functions
                    # Normalize whitespace for comparison
                    normalized_body = " ".join(func_body.split())
                    func_hash = self.get_content_hash(normalized_body)

                    self.function_hashes[func_hash].append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "function": func_name,
                            "body_length": len(func_body),
                        }
                    )

        # Find duplicates (hash appearing in multiple files)
        duplicates = {}
        for func_hash, occurrences in self.function_hashes.items():
            if len(occurrences) > 1:
                # Group by function name
                by_name = defaultdict(list)
                for occ in occurrences:
                    by_name[occ["function"]].append(occ)

                for func_name, instances in by_name.items():
                    if len(instances) > 1:
                        duplicates[f"{func_name}_{func_hash[:8]}"] = instances

        return duplicates

    def find_import_patterns(self) -> Dict[str, List[str]]:
        """Find common import patterns across files"""
        python_files = self.find_python_files()

        for file_path in python_files:
            imports = self.extract_imports(file_path)

            for import_stmt in imports:
                self.import_patterns[import_stmt].append(
                    str(file_path.relative_to(self.project_root))
                )

        # Find frequently used imports
        common_imports = {}
        for import_stmt, files in self.import_patterns.items():
            if len(files) > 10:  # Used in more than 10 files
                common_imports[import_stmt] = files

        return common_imports

    def find_similar_files(self) -> List[Dict]:
        """Find files with similar content structure"""
        python_files = self.find_python_files()
        file_signatures = {}

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Create signature based on structure
                imports = self.extract_imports(file_path)
                functions = self.extract_functions(file_path)

                signature = {
                    "import_count": len(imports),
                    "function_count": len(functions),
                    "line_count": len(content.split("\n")),
                    "import_hash": self.get_content_hash("\n".join(sorted(imports))),
                    "function_names": sorted([f[0] for f in functions]),
                }

                file_signatures[
                    str(file_path.relative_to(self.project_root))
                ] = signature

            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")

        # Find similar files
        similarities = []
        files = list(file_signatures.keys())

        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                file1, file2 = files[i], files[j]
                sig1, sig2 = file_signatures[file1], file_signatures[file2]

                # Calculate similarity score
                score = 0

                # Import similarity
                if sig1["import_hash"] == sig2["import_hash"]:
                    score += 40

                # Function name similarity
                common_functions = set(sig1["function_names"]) & set(
                    sig2["function_names"]
                )
                if common_functions:
                    score += len(common_functions) * 10

                # Size similarity
                size_diff = abs(sig1["line_count"] - sig2["line_count"])
                if size_diff < 50:
                    score += 20

                if score > 50:  # Similarity threshold
                    similarities.append(
                        {
                            "file1": file1,
                            "file2": file2,
                            "score": score,
                            "common_functions": list(common_functions),
                            "size_diff": size_diff,
                        }
                    )

        return sorted(similarities, key=lambda x: x["score"], reverse=True)

    def check_dead_files(self) -> List[str]:
        """Find potentially unused files"""
        python_files = self.find_python_files()
        dead_files = []

        for file_path in python_files:
            file_rel = file_path.relative_to(self.project_root)

            # Check if file is imported anywhere
            is_imported = False
            module_path = str(file_rel).replace("/", ".").replace(".py", "")

            for other_file in python_files:
                if other_file == file_path:
                    continue

                try:
                    with open(other_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    if module_path in content or file_path.stem in content:
                        is_imported = True
                        break

                except Exception:
                    continue

            # Check if it's a main module
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if '__name__ == "__main__"' in content:
                    is_imported = True  # Main modules are not dead

            except Exception:
                pass

            if not is_imported:
                dead_files.append(str(file_rel))

        return dead_files

    def generate_report(self) -> Dict:
        """Generate comprehensive duplicate code report"""
        print("\U0001f50d ANALYZING DUPLICATE CODE PATTERNS")
        print("=" * 50)

        # Find duplicates
        print("\U0001f504 Finding duplicate functions...")
        duplicate_functions = self.find_duplicate_functions()

        print("\U0001f4e6 Analyzing import patterns...")
        common_imports = self.find_import_patterns()

        print("\U0001f4c4 Finding similar files...")
        similar_files = self.find_similar_files()

        print("\U0001f5d1\ufe0f Checking for dead files...")
        dead_files = self.check_dead_files()

        report = {
            "duplicate_functions": duplicate_functions,
            "common_imports": common_imports,
            "similar_files": similar_files,
            "dead_files": dead_files,
            "statistics": {
                "total_files": len(self.find_python_files()),
                "duplicate_function_groups": len(duplicate_functions),
                "similar_file_pairs": len(similar_files),
                "potentially_dead_files": len(dead_files),
            },
        }

        return report


def main():
    project_root = os.getcwd()
    finder = DuplicateCodeFinder(project_root)

    try:
        report = finder.generate_report()

        print()
        print("\U0001f4ca DUPLICATE CODE ANALYSIS REPORT")
        print("=" * 50)

        stats = report["statistics"]
        print(f"\U0001f4c1 Total Files Analyzed: {stats['total_files']}")
        print(
            f"\U0001f504 Duplicate Function Groups: {stats['duplicate_function_groups']}"
        )
        print(f"\U0001f4c4 Similar File Pairs: {stats['similar_file_pairs']}")
        print(
            f"\U0001f5d1\ufe0f Potentially Dead Files: {stats['potentially_dead_files']}"
        )

        # Show duplicate functions
        if report["duplicate_functions"]:
            print()
            print("\U0001f504 DUPLICATE FUNCTIONS:")
            for func_id, instances in list(report["duplicate_functions"].items())[:5]:
                print(f"\n  Function: {instances[0]['function']}")
                for instance in instances:
                    print(f"    - {instance['file']} ({instance['body_length']} chars)")

        # Show most similar files
        if report["similar_files"]:
            print()
            print("\U0001f4c4 MOST SIMILAR FILES:")
            for similarity in report["similar_files"][:5]:
                print(f"\n  Score: {similarity['score']}")
                print(f"    - {similarity['file1']}")
                print(f"    - {similarity['file2']}")
                if similarity["common_functions"]:
                    print(
                        f"    Common functions: {', '.join(similarity['common_functions'][:3])}"
                    )

        # Show potentially dead files
        if report["dead_files"]:
            print()
            print("\U0001f5d1\ufe0f POTENTIALLY DEAD FILES:")
            for dead_file in report["dead_files"][:10]:
                print(f"    - {dead_file}")

        # Show common imports (consolidation opportunities)
        common_imports = [
            (imp, files)
            for imp, files in report["common_imports"].items()
            if len(files) > 15
        ]
        if common_imports:
            print()
            print("\U0001f4e6 MOST COMMON IMPORTS (consolidation opportunities):")
            for import_stmt, files in sorted(
                common_imports, key=lambda x: len(x[1]), reverse=True
            )[:5]:
                print(f"    - {import_stmt} (used in {len(files)} files)")

        print()
        print("\U0001f3af RECOMMENDATIONS:")
        if stats["duplicate_function_groups"] > 0:
            print("  - Extract duplicate functions to shared utilities")
        if stats["similar_file_pairs"] > 0:
            print("  - Consider merging similar files or extracting common patterns")
        if stats["potentially_dead_files"] > 0:
            print("  - Review and remove unused files after verification")
        if common_imports:
            print("  - Create common import modules for frequently used dependencies")

    except Exception as e:
        print(f"\u274c Error during analysis: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
