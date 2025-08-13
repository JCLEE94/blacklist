#!/usr/bin/env python3
"""
Repository Cleanup Script
Handles staging and committing deleted files from offline package cleanup
"""
import subprocess
import os
import sys

def main():
    # Ensure we're in the right directory
    repo_path = '/home/jclee/app/blacklist'
    os.chdir(repo_path)
    
    print("🔄 Repository Cleanup and Sync Operation")
    print("=" * 50)
    
    try:
        # Check git status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        status_lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
        deleted_files = [line for line in status_lines if line.strip().startswith('D ')]
        
        print(f"📊 Current repository state:")
        print(f"   Total changes: {len(status_lines)}")
        print(f"   Deleted files: {len(deleted_files)}")
        
        if not status_lines:
            print("✅ Repository is already clean!")
            return True
            
        # Stage all changes (including deletions)
        print(f"\n📦 Staging all changes...")
        subprocess.run(['git', 'add', '-A'], check=True)
        
        # Create commit with proper message
        commit_message = """chore: clean up old offline package v2.0.0

- Remove offline-packages/blacklist-offline-package-v2.0.0/ directory
- Clean up old offline deployment package files
- Repository maintenance and sync operation

Generated-by: Claude Code"""
        
        print("✅ Creating cleanup commit...")
        result = subprocess.run(['git', 'commit', '-m', commit_message], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Commit created successfully!")
            print(f"   {result.stdout.strip()}")
        else:
            print(f"⚠️  Commit result: {result.stderr.strip()}")
        
        # Verify final status
        print(f"\n🎯 Verifying final repository state...")
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        remaining_changes = len([line for line in result.stdout.strip().split('\n') if line.strip()])
        
        print(f"📊 Cleanup completed!")
        print(f"   Remaining uncommitted changes: {remaining_changes}")
        
        if remaining_changes == 0:
            print("✅ Repository is now in clean state!")
        else:
            print("ℹ️  Repository status:")
            subprocess.run(['git', 'status', '--short'])
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False
    finally:
        # Clean up this script
        try:
            os.remove(__file__)
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)