#!/bin/bash
echo "=== GitHub Workflows 디렉토리 구조 ==="
find .github -type f -name "*.yml" -o -name "*.yaml" 2>/dev/null || echo "No .github directory found"

echo -e "\n=== 프로젝트 루트 파일들 ==="
ls -la | grep -E '\.(yml|yaml|json|md)$'

echo -e "\n=== Docker 관련 파일들 ==="
ls -la | grep -E '(docker|compose)'

echo -e "\n=== 현재 레지스트리 설정 확인 ==="
grep -r "registry" . --include="*.yml" --include="*.yaml" --include="*.json" 2>/dev/null | head -10