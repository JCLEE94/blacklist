#!/bin/bash
# Setup Git Hooks for Automated Version Management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up Git Hooks for Automated Version Management${NC}"

# Get git root directory
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
HOOKS_DIR="$GIT_ROOT/.git/hooks"

echo -e "${BLUE}📁 Git root: $GIT_ROOT${NC}"
echo -e "${BLUE}📁 Hooks directory: $HOOKS_DIR${NC}"

# Check if we're in a git repository
if [ ! -d "$GIT_ROOT/.git" ]; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Ensure hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo -e "${RED}❌ Error: Git hooks directory not found${NC}"
    exit 1
fi

# Make sure version management scripts exist
SCRIPTS_DIR="$GIT_ROOT/scripts"
VERSION_MANAGER="$SCRIPTS_DIR/version-manager.py"
BUMP_SCRIPT="$SCRIPTS_DIR/bump-version.sh"

echo -e "${BLUE}🔍 Checking version management scripts...${NC}"

if [ ! -f "$VERSION_MANAGER" ]; then
    echo -e "${RED}❌ Error: version-manager.py not found at $VERSION_MANAGER${NC}"
    exit 1
fi

if [ ! -f "$BUMP_SCRIPT" ]; then
    echo -e "${RED}❌ Error: bump-version.sh not found at $BUMP_SCRIPT${NC}"
    exit 1
fi

# Make scripts executable
chmod +x "$VERSION_MANAGER"
chmod +x "$BUMP_SCRIPT"
echo -e "${GREEN}✅ Made version management scripts executable${NC}"

# Setup pre-push hook
PRE_PUSH_HOOK="$HOOKS_DIR/pre-push"

if [ -f "$PRE_PUSH_HOOK" ]; then
    # Backup existing hook
    BACKUP_FILE="$PRE_PUSH_HOOK.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$PRE_PUSH_HOOK" "$BACKUP_FILE"
    echo -e "${YELLOW}⚠️  Backed up existing pre-push hook to: $BACKUP_FILE${NC}"
fi

# Make pre-push hook executable
if [ -f "$PRE_PUSH_HOOK" ]; then
    chmod +x "$PRE_PUSH_HOOK"
    echo -e "${GREEN}✅ Pre-push hook is now executable${NC}"
else
    echo -e "${RED}❌ Error: Pre-push hook not found at $PRE_PUSH_HOOK${NC}"
    exit 1
fi

# Test version manager
echo -e "${BLUE}🧪 Testing version management system...${NC}"

# Test validation only (non-destructive)
if python3 "$VERSION_MANAGER" --project-root "$GIT_ROOT" --validate-only; then
    echo -e "${GREEN}✅ Version manager validation test passed${NC}"
else
    echo -e "${YELLOW}⚠️  Version manager validation test failed (may be normal if versions are inconsistent)${NC}"
fi

# Show current version
VERSION_FILE="$GIT_ROOT/version.txt"
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION=$(cat "$VERSION_FILE")
    echo -e "${GREEN}📍 Current version: $CURRENT_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  No version.txt found - will be created on first version bump${NC}"
fi

echo -e "${GREEN}🎉 Git hooks setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 What happens now:${NC}"
echo -e "   • Before each push to main, version will be automatically bumped"
echo -e "   • Version bump type is detected from commit messages:"
echo -e "     - ${GREEN}fix:${NC} commits → patch version (1.0.X)"
echo -e "     - ${GREEN}feat:${NC} commits → minor version (1.X.0)"
echo -e "     - ${GREEN}BREAKING CHANGE:${NC} → major version (X.0.0)"
echo -e "   • All version references in the codebase will be updated"
echo -e "   • A version commit and git tag will be created automatically"
echo ""
echo -e "${BLUE}💡 Manual usage:${NC}"
echo -e "   ${GREEN}python3 scripts/version-manager.py --interactive${NC}  # Interactive version bump"
echo -e "   ${GREEN}python3 scripts/version-manager.py --show-references${NC}  # Show all version references"
echo -e "   ${GREEN}python3 scripts/version-manager.py --validate-only${NC}    # Check version consistency"
echo ""
echo -e "${YELLOW}⚠️  Note: Hooks only activate on pushes to the main branch${NC}"