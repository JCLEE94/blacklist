#!/bin/bash
# Make all version management scripts executable

echo "🔧 Making version management scripts executable..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make version management scripts executable
chmod +x "$SCRIPT_DIR/version-manager.py"
chmod +x "$SCRIPT_DIR/bump-version.sh"  
chmod +x "$SCRIPT_DIR/fix-version-references.py"
chmod +x "$SCRIPT_DIR/setup-git-hooks.sh"
chmod +x "$SCRIPT_DIR/make-executable.sh"

# Make git hook executable if it exists
GIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PRE_PUSH_HOOK="$GIT_ROOT/.git/hooks/pre-push"
if [ -f "$PRE_PUSH_HOOK" ]; then
    chmod +x "$PRE_PUSH_HOOK"
    echo "✅ Made pre-push hook executable"
fi

echo "✅ All version management scripts are now executable"
echo ""
echo "📋 Available scripts:"
echo "   • version-manager.py      - Main version management system"
echo "   • bump-version.sh         - Enhanced version bumping for CI/CD"
echo "   • fix-version-references.py - Fix existing version inconsistencies"
echo "   • setup-git-hooks.sh      - Setup automated git hooks"
echo "   • make-executable.sh      - This script"
echo ""
echo "🚀 Quick start:"
echo "   bash $SCRIPT_DIR/setup-git-hooks.sh"