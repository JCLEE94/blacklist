#!/usr/bin/env python3
import subprocess
import os

# Change to the repository directory
os.chdir('/home/jclee/app/blacklist')

print("🔍 Checking current repository status...")

# Get git status
result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
status_lines = [line for line in result.stdout.strip().split('\n') if line]

print(f"📊 Total files with changes: {len(status_lines)}")

# Count different types of changes
deleted_files = [line for line in status_lines if line.startswith(' D')]
other_changes = [line for line in status_lines if not line.startswith(' D')]

print(f"🗑️  Deleted files: {len(deleted_files)}")
print(f"📝 Other changes: {len(other_changes)}")

if deleted_files:
    print("\n📦 Staging and committing deleted files...")
    
    # Stage all changes
    subprocess.run(['git', 'add', '-A'], check=True)
    
    # Create commit
    commit_msg = """chore: clean up old offline package v2.0.0

- Remove offline-packages/blacklist-offline-package-v2.0.0/ directory
- Clean up old offline deployment package files  
- Repository maintenance and sync operation

Generated-by: Claude Code"""
    
    result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Cleanup commit created successfully!")
        print(result.stdout)
    else:
        print("❌ Commit failed:")
        print(result.stderr)
    
    # Check final status
    print("\n🎯 Final repository status:")
    subprocess.run(['git', 'status'])
    
else:
    print("✅ No deleted files found - repository appears clean!")

# Clean up temporary files
try:
    for file in ['run_cleanup.py', 'final_cleanup.sh', 'cleanup_commit.sh', 'git_status_check.sh', 'execute_cleanup.sh']:
        if os.path.exists(file):
            os.remove(file)
except:
    pass