#!/bin/bash
set -euo pipefail

# Security Verification Script
# Verifies security best practices and CNCF security standards

echo "🔒 Security Verification"
echo "========================"

SECURITY_SCORE=0
TOTAL_SECURITY_CHECKS=0

# Check for security files
echo "📋 Checking security documentation..."
SECURITY_FILES=(
    "SECURITY.md"
    "LICENSE"
)

for file in "${SECURITY_FILES[@]}"; do
    TOTAL_SECURITY_CHECKS=$((TOTAL_SECURITY_CHECKS + 1))
    if [ -f "$file" ]; then
        echo "  ✅ $file exists"
        SECURITY_SCORE=$((SECURITY_SCORE + 1))
    else
        echo "  ❌ $file missing"
    fi
done

# Check for secrets in code
echo ""
echo "🔍 Scanning for potential secrets..."
TOTAL_SECURITY_CHECKS=$((TOTAL_SECURITY_CHECKS + 1))
if command -v grep >/dev/null 2>&1; then
    SECRET_PATTERNS=(
        "password\s*=\s*['\"][^'\"]*['\"]"
        "secret\s*=\s*['\"][^'\"]*['\"]"
        "api_key\s*=\s*['\"][^'\"]*['\"]"
        "token\s*=\s*['\"][^'\"]*['\"]"
    )
    
    SECRETS_FOUND=false
    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -r -i -E "$pattern" src/ --include="*.py" 2>/dev/null | grep -v "example\|test\|placeholder" | head -1; then
            SECRETS_FOUND=true
        fi
    done
    
    if [ "$SECRETS_FOUND" = false ]; then
        echo "  ✅ No hardcoded secrets found"
        SECURITY_SCORE=$((SECURITY_SCORE + 1))
    else
        echo "  ⚠️  Potential secrets found in code"
    fi
else
    echo "  ⚠️  grep not available, skipping secret scan"
fi

# Check Dockerfile security
echo ""
echo "🐳 Checking Dockerfile security..."
TOTAL_SECURITY_CHECKS=$((TOTAL_SECURITY_CHECKS + 1))
if [ -f "build/docker/Dockerfile" ]; then
    if grep -q "USER" build/docker/Dockerfile; then
        echo "  ✅ Non-root user specified in Dockerfile"
        SECURITY_SCORE=$((SECURITY_SCORE + 1))
    else
        echo "  ⚠️  No non-root user specified in Dockerfile"
    fi
else
    echo "  ❌ Dockerfile not found"
fi

# Check for security in Helm charts
echo ""
echo "⚓ Checking Helm chart security..."
TOTAL_SECURITY_CHECKS=$((TOTAL_SECURITY_CHECKS + 1))
if [ -f "charts/blacklist/values.yaml" ]; then
    if grep -q "securityContext" charts/blacklist/values.yaml; then
        echo "  ✅ Security context defined in Helm chart"
        SECURITY_SCORE=$((SECURITY_SCORE + 1))
    else
        echo "  ⚠️  No security context in Helm chart"
    fi
else
    echo "  ❌ Helm values.yaml not found"
fi

# Check for .env files in git
echo ""
echo "🔐 Checking for environment files..."
TOTAL_SECURITY_CHECKS=$((TOTAL_SECURITY_CHECKS + 1))
if [ -f ".gitignore" ]; then
    if grep -q "\.env" .gitignore; then
        echo "  ✅ .env files excluded from git"
        SECURITY_SCORE=$((SECURITY_SCORE + 1))
    else
        echo "  ⚠️  .env files not excluded from git"
    fi
else
    echo "  ❌ .gitignore not found"
fi

# Calculate security score
SECURITY_PERCENT=$((SECURITY_SCORE * 100 / TOTAL_SECURITY_CHECKS))

echo ""
echo "🔒 Security Compliance Results"
echo "=============================="
echo "Score: $SECURITY_SCORE/$TOTAL_SECURITY_CHECKS ($SECURITY_PERCENT%)"

if [ $SECURITY_PERCENT -ge 80 ]; then
    echo "🔐 Excellent security compliance"
    exit 0
elif [ $SECURITY_PERCENT -ge 60 ]; then
    echo "🔒 Good security compliance"
    exit 0
else
    echo "⚠️  Security improvements needed"
    exit 1
fi