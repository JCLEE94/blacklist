#!/bin/bash
set -euo pipefail

# CNCF Structure Verification Script
# Verifies that the project follows CNCF Cloud Native standards

echo "🔍 CNCF Structure Verification"
echo "================================"

SCORE=0
TOTAL_CHECKS=0
REQUIRED_DIRS=(
    ".github/workflows"
    "api"
    "build" 
    "charts"
    "cmd"
    "config"
    "deployments"
    "docs"
    "hack"
    "internal"
    "pkg"
    "test"
)

REQUIRED_FILES=(
    "README.md"
    "LICENSE"
    "Makefile"
    ".gitignore"
)

RECOMMENDED_FILES=(
    "CONTRIBUTING.md"
    "CODE_OF_CONDUCT.md"
    "SECURITY.md"
    "charts/blacklist/Chart.yaml"
    "api/openapi/blacklist-api.yaml"
)

# Check required directories
echo "📁 Checking required directories..."
for dir in "${REQUIRED_DIRS[@]}"; do
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
        SCORE=$((SCORE + 1))
    else
        echo "  ❌ $dir (missing)"
    fi
done

# Check required files
echo ""
echo "📄 Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$file" ]; then
        echo "  ✅ $file"
        SCORE=$((SCORE + 1))
    else
        echo "  ❌ $file (missing)"
    fi
done

# Check recommended files
echo ""
echo "📋 Checking recommended files..."
for file in "${RECOMMENDED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
        SCORE=$((SCORE + 1))
    else
        echo "  ⚠️  $file (recommended)"
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
done

# Calculate compliance score
COMPLIANCE_PERCENT=$((SCORE * 100 / TOTAL_CHECKS))

echo ""
echo "📊 CNCF Compliance Results"
echo "=========================="
echo "Score: $SCORE/$TOTAL_CHECKS ($COMPLIANCE_PERCENT%)"

if [ $COMPLIANCE_PERCENT -ge 90 ]; then
    echo "🏆 Excellent - CNCF Graduated Level"
    exit 0
elif [ $COMPLIANCE_PERCENT -ge 70 ]; then
    echo "✅ Good - CNCF Incubating Level"
    exit 0
elif [ $COMPLIANCE_PERCENT -ge 50 ]; then
    echo "📊 Fair - CNCF Sandbox Level"
    exit 0
else
    echo "⚠️  Poor - Needs Improvement"
    exit 1
fi