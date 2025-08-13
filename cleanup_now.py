#!/usr/bin/env python3
import subprocess
import os

# Change to repository directory
os.chdir('/home/jclee/app/blacklist')

print("🔄 REPOSITORY CLEANUP AND SYNC OPERATION")
print("=" * 50)

# Check current git status
print("📊 Checking repository status...")
result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
changes = [line for line in result.stdout.strip().split('\n') if line.strip()]
print(f"Found {len(changes)} files with changes")

if changes:
    # Stage all changes including deletions
    print("📦 Staging all changes...")
    subprocess.run(['git', 'add', '-A'])
    
    # Create commit
    print("✅ Creating cleanup commit...")
    commit_msg = """chore: clean up old offline package v2.0.0

- Remove offline-packages/blacklist-offline-package-v2.0.0/ directory
- Clean up old offline deployment package files
- Repository maintenance and sync operation

Generated-by: Claude Code"""
    
    result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
    print(result.stdout if result.stdout else result.stderr)
    
    # Check final status
    print("🎯 Final repository status:")
    subprocess.run(['git', 'status'])
else:
    print("✅ Repository is already clean!")

# Clean up temporary files
for f in ['git_cleanup.py', 'execute.sh', 'cleanup_now.py', 'run_final.sh', 'check_and_commit.py', 'final_cleanup.sh']:
    try:
        if os.path.exists(f):
            os.remove(f)
    except:
        pass