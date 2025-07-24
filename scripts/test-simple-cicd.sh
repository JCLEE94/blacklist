#!/bin/bash
# 간단한 CI/CD 테스트

set -e

echo "=== Simple CI/CD Test ==="

# 1. 버전 업데이트
echo "Updating version..."
sed -i "s/__version__ = .*/__version__ = '2.1.3-test'/" src/core/__init__.py || true

# 2. Commit
git add -A
git commit -m "test: Simple CI/CD test" || echo "No changes"

# 3. Push
echo "Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Test pushed. Check GitHub Actions for results."
echo "https://github.com/JCLEE94/blacklist/actions"