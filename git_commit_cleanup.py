#!/usr/bin/env python3
"""Git Repository Cleanup - Commit deleted files from offline package cleanup"""

import subprocess
import os

def main():
    os.chdir('/home/jclee/app/blacklist')
    
    print("🔄 REPOSITORY CLEANUP OPERATION")
    print("================================")
    
    # Stage all changes (including deletions)
    print("📦 Staging all changes...")
    subprocess.run(['git', 'add', '-A'], check=True)
    
    # Create commit for cleanup
    print("✅ Committing cleanup...")
    commit_message = """chore: clean up old offline package v2.0.0

- Remove offline-packages/blacklist-offline-package-v2.0.0/ directory
- Clean up old offline deployment package files
- Repository maintenance and sync operation

Generated-by: Claude Code"""
    
    result = subprocess.run(['git', 'commit', '-m', commit_message], 
                          capture_output=True, text=True)
    
    print("Commit result:")
    print(result.stdout if result.stdout else result.stderr)
    
    # Show final status
    print("\n🎯 Repository status after cleanup:")
    subprocess.run(['git', 'status'])
    
    print("\n✅ Cleanup operation completed!")

if __name__ == "__main__":
    main()