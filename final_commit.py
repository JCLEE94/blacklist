#!/usr/bin/env python3

import subprocess
import os

# Change to project directory
os.chdir('/home/jclee/app/blacklist')

try:
    # Check current status
    print("=== Git Status ===")
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    print(result.stdout if result.stdout else "No changes detected")
    
    # Add all changes
    print("\n=== Adding Changes ===")
    subprocess.run(['git', 'add', '.'], check=True)
    print("All changes staged")
    
    # Commit with comprehensive message
    commit_msg = """feat: Major project reorganization and security hardening

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
    
    print("\n=== Committing Changes ===")
    result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Commit successful!")
        print(result.stdout)
    else:
        print("ℹ️ Commit result:")
        print(result.stdout)
        if result.stderr:
            print("Additional info:", result.stderr)
    
    # Show final status
    print("\n=== Final Git Status ===")
    result = subprocess.run(['git', 'status'], capture_output=True, text=True)
    print(result.stdout)
    
    print("\n=== Recent Commits ===")
    result = subprocess.run(['git', 'log', '--oneline', '-3'], capture_output=True, text=True)
    print(result.stdout)
    
except subprocess.CalledProcessError as e:
    print(f"Git command failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Clean up temporary files
try:
    os.remove('commit_changes.sh')
    os.remove('run_commit.sh') 
    os.remove('execute_commit.py')
    os.remove('commit_execution_result.py')
    os.remove('run_commit_now.py')
    print("\n✅ Cleaned up temporary commit files")
except:
    pass