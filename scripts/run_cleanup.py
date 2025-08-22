#!/usr/bin/env python3
import subprocess
import os
import sys


def run_cleanup():
    """Execute repository cleanup and sync operation"""

    # Change to blacklist directory
    os.chdir("/home/jclee/app/blacklist")

    print("🔄 Starting repository cleanup operation...")

    # Check current status
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    deleted_files = [
        line for line in result.stdout.split("\n") if line.startswith(" D ")
    ]
    print(f"📊 Found {len(deleted_files)} deleted files to commit")

    if len(deleted_files) == 0:
        print("✅ Repository is already clean!")
        return

    # Stage all changes (including deletions)
    print("📦 Staging all deleted files...")
    subprocess.run(["git", "add", "-A"], check=True)

    # Create commit
    print("✅ Creating cleanup commit...")
    commit_message = """chore: clean up old offline package v2.0.0

- Remove offline-packages/blacklist-offline-package-v2.0.0/ directory
- Clean up old offline deployment package files
- Repository maintenance and sync operation

Generated-by: Claude Code"""

    subprocess.run(["git", "commit", "-m", commit_message], check=True)

    # Verify clean state
    print("🎯 Verifying clean repository state...")
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    remaining_files = len([line for line in result.stdout.split("\n") if line.strip()])

    print(f"📊 Cleanup operation completed!")
    print(f"Repository status: {remaining_files} uncommitted changes")

    if remaining_files == 0:
        print("✅ Repository is now in clean state!")
    else:
        print("⚠️  Some files still remain uncommitted")
        subprocess.run(["git", "status"])


if __name__ == "__main__":
    try:
        run_cleanup()
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Cleanup operation failed: {e}")
        sys.exit(1)
