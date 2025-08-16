import subprocess
import os
import sys

os.chdir('/home/jclee/app/blacklist')

# Execute git commands directly
commands = [
    ['git', 'add', '.'],
    ['git', 'commit', '-m', '''feat: Major project reorganization and security hardening

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
Co-Authored-By: Claude Code <claude@anthropic.com>''']
]

for cmd in commands:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Command: {' '.join(cmd[:2])}")
    print(f"Exit code: {result.returncode}")
    if result.stdout: print(f"Output: {result.stdout}")
    if result.stderr: print(f"Error: {result.stderr}")
    print("---")

# Show status
subprocess.run(['git', 'status'], check=False)
subprocess.run(['git', 'log', '--oneline', '-2'], check=False)