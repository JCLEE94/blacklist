#!/bin/bash

cd /home/jclee/app/blacklist

echo "=== Current Git Status ==="
git status --short

echo ""
echo "=== Adding all changes ==="
git add .

echo ""
echo "=== Committing changes ==="
git commit -m "feat: Major project reorganization and security hardening

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
Co-Authored-By: Claude Code <claude@anthropic.com>"

echo ""
echo "=== Cleaning up temporary files ==="
rm -f commit_*.py commit_*.sh execute_*.sh run_*.py final_*.py cleanup_*.sh

echo ""
echo "=== Final Git Status ==="
git status

echo ""
echo "=== Recent Commits ==="
git log --oneline -3