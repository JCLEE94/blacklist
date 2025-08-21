#!/bin/bash
# Enhanced Auto-increment version script for CI/CD
# Uses Python version manager for comprehensive version management

set -e  # Exit on any error

VERSION_FILE="version.txt"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔄 Enhanced Version Management System"
echo "📁 Project root: $PROJECT_ROOT"

# Ensure Python version manager exists
PYTHON_VERSION_MANAGER="$SCRIPT_DIR/version-manager.py"
if [ ! -f "$PYTHON_VERSION_MANAGER" ]; then
    echo "❌ Error: Python version manager not found at $PYTHON_VERSION_MANAGER"
    exit 1
fi

# Make sure Python script is executable
chmod +x "$PYTHON_VERSION_MANAGER"

# Function to detect commit type for bump determination
detect_bump_type() {
    local bump_type="patch"  # default
    
    # Get commit messages since last tag (or all if no tags)
    local commits
    if git tag --list | grep -q "v"; then
        commits=$(git log --oneline --pretty=format:"%s" $(git describe --tags --abbrev=0)..HEAD 2>/dev/null || git log --oneline --pretty=format:"%s" HEAD)
    else
        commits=$(git log --oneline --pretty=format:"%s" HEAD)
    fi
    
    if echo "$commits" | grep -qi "BREAKING CHANGE\|^feat.*!"; then
        bump_type="major"
    elif echo "$commits" | grep -qi "^feat"; then
        bump_type="minor"
    elif echo "$commits" | grep -qi "^fix"; then
        bump_type="patch"
    fi
    
    echo "$bump_type"
}

# Fallback function if Python script fails
fallback_version_bump() {
    echo "⚠️  Using fallback version bump method"
    
    if [ ! -f "$VERSION_FILE" ]; then
        echo "1.0.0" > "$VERSION_FILE"
    fi

    # Read current version
    CURRENT_VERSION=$(cat "$VERSION_FILE")
    echo "📍 Current version: $CURRENT_VERSION"

    # Split version into parts
    IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
    MAJOR="${VERSION_PARTS[0]}"
    MINOR="${VERSION_PARTS[1]}"
    PATCH="${VERSION_PARTS[2]}"

    # Detect bump type
    BUMP_TYPE=$(detect_bump_type)
    echo "📈 Detected bump type: $BUMP_TYPE"

    # Apply version bump
    case "$BUMP_TYPE" in
        "major")
            MAJOR=$((MAJOR + 1))
            MINOR=0
            PATCH=0
            ;;
        "minor")
            MINOR=$((MINOR + 1))
            PATCH=0
            ;;
        "patch"|*)
            PATCH=$((PATCH + 1))
            ;;
    esac

    # Create new version
    NEW_VERSION="$MAJOR.$MINOR.$PATCH"
    echo "🎯 New version: $NEW_VERSION"

    # Write new version
    echo "$NEW_VERSION" > "$VERSION_FILE"
    
    return 0
}

# Try Python version manager first, fallback if it fails
echo "🐍 Running Python version manager..."
if python3 "$PYTHON_VERSION_MANAGER" --project-root "$PROJECT_ROOT" --no-commit; then
    echo "✅ Python version manager completed successfully"
    NEW_VERSION=$(cat "$VERSION_FILE")
else
    echo "⚠️  Python version manager failed, using fallback..."
    fallback_version_bump
    NEW_VERSION=$(cat "$VERSION_FILE")
fi

echo "🎉 Version bump completed: $NEW_VERSION"

# Export for GitHub Actions
if [ -n "$GITHUB_ENV" ]; then
    echo "VERSION=$NEW_VERSION" >> "$GITHUB_ENV"
    echo "🔄 Exported VERSION=$NEW_VERSION to GitHub Environment"
fi

# Legacy GitHub Actions output (for older workflows)
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "version=$NEW_VERSION" >> "$GITHUB_OUTPUT"
elif command -v "echo" >/dev/null 2>&1; then
    # Fallback for older GitHub Actions
    echo "::set-output name=version::$NEW_VERSION" || true
fi

echo "✅ Version management completed successfully"