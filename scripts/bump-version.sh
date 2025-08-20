#!/bin/bash
# Auto-increment version script for CI/CD

VERSION_FILE="version.txt"

if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0" > "$VERSION_FILE"
fi

# Read current version
CURRENT_VERSION=$(cat "$VERSION_FILE")
echo "Current version: $CURRENT_VERSION"

# Split version into parts
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

# Increment patch version
PATCH=$((PATCH + 1))

# Create new version
NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "New version: $NEW_VERSION"

# Write new version
echo "$NEW_VERSION" > "$VERSION_FILE"

# Export for GitHub Actions
echo "VERSION=$NEW_VERSION" >> $GITHUB_ENV
echo "::set-output name=version::$NEW_VERSION"