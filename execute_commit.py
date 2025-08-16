#!/usr/bin/env python3

import subprocess
import os

# Change to the blacklist directory
os.chdir('/home/jclee/app/blacklist')

print("=== Current Git Status ===")
result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
print(result.stdout)

print("\n=== Adding all changes ===")
result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
if result.returncode != 0:
    print(f"Error adding files: {result.stderr}")
else:
    print("All changes staged successfully")

print("\n=== Committing changes ===")
commit_message = """feat: Major project reorganization and security hardening

**Directory Reorganization:**
- Move main.py, start.sh, init_database.py from app/ to root directory
- Reorganize scripts/deployment/ with legacy/ and offline/ subdirectories  
- Move development reports to .dev-reports/ directory
- Remove duplicate configuration files and consolidate structure

**Configuration Fixes:**
- Fix database URLs from Docker format to local development format
- Update pytest.ini with correct .dev-reports/ paths for test outputs
- Update .gitignore to properly exclude .dev-reports/ directory
- Standardize application port to 2542 across all environments

**Security Improvements:** 
- Remove hardcoded credentials from 14+ configuration files
- Replace with secure environment variable placeholders
- Add security warnings in sensitive configuration files
- Implement credential rotation and validation system

**Infrastructure Updates:**
- Enhance Docker Compose configuration for production deployment
- Improve Makefile targets for development workflow
- Update deployment scripts for better automation
- Fix CI/CD pipeline configuration paths

This reorganization improves project maintainability, enhances security posture,
and creates a cleaner development workflow structure.

Powered by Claude Code (claude.ai/code)
Co-Authored-By: Claude Code <claude@anthropic.com>"""

result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)
if result.returncode != 0:
    print(f"Commit failed: {result.stderr}")
else:
    print("Commit successful!")
    print(result.stdout)

print("\n=== Post-commit Git Status ===")
result = subprocess.run(['git', 'status'], capture_output=True, text=True)
print(result.stdout)

print("\n=== Recent Commits ===")
result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print(result.stdout)