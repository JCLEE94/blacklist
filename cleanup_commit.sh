#!/bin/bash
# Repository cleanup and sync operation

cd /home/jclee/app/blacklist

echo "🔄 Starting repository cleanup operation..."
echo "Current repository state:"
git status --short | wc -l
echo "files in staging area"

echo ""
echo "📦 Staging all deleted files..."
# Stage all deleted files (the offline package cleanup)
git add -A

echo ""
echo "✅ Creating cleanup commit..."
# Create commit with conventional commit format
git commit -m "chore: clean up old offline package v2.0.0

- Remove offline-packages/blacklist-offline-package-v2.0.0/ directory
- Clean up 375 deleted files from old offline deployment package
- Repository maintenance and sync operation

Generated-by: Claude Code"

echo ""
echo "🎯 Verifying clean repository state..."
git status

echo ""
echo "📊 Cleanup operation completed!"
echo "Repository status: $(git status --porcelain | wc -l) uncommitted changes"