#!/bin/bash

# 🚀 GitHub 마이그레이션: jclee94 → qws941
echo "🔄 GitHub 사용자명 마이그레이션 시작: jclee94 → qws941"

# 백업 생성
echo "📦 변경 전 백업 생성..."
mkdir -p migration-backup-$(date +%Y%m%d)

# 주요 파일들 백업
cp README.md migration-backup-$(date +%Y%m%d)/
cp CLAUDE.md migration-backup-$(date +%Y%m%d)/
cp docker-compose.yml migration-backup-$(date +%Y%m%d)/
cp -r .github/ migration-backup-$(date +%Y%m%d)/
cp -r docs/ migration-backup-$(date +%Y%m%d)/

echo "✅ 백업 완료"

# 1. GitHub Pages URL 업데이트 (jclee94.github.io → qws941.github.io)
echo "🔧 GitHub Pages URL 업데이트 중..."
find . -type f \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) \
    -not -path "./.git/*" -not -path "./.venv/*" -not -path "./migration-backup-*/*" \
    -exec sed -i 's/jclee94\.github\.io\/blacklist/qws941.github.io\/blacklist/g' {} \;

# 2. Docker Registry 네임스페이스 업데이트 (jclee94 → qws941)
echo "🐳 Docker Registry 네임스페이스 업데이트 중..."
find . -type f \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) \
    -not -path "./.git/*" -not -path "./.venv/*" -not -path "./migration-backup-*/*" \
    -exec sed -i 's/registry\.jclee\.me\/jclee94\/blacklist/registry.jclee.me\/qws941\/blacklist/g' {} \;

# 3. GitHub Repository URL 업데이트
echo "📋 GitHub Repository URL 업데이트 중..."
find . -type f \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" \) \
    -not -path "./.git/*" -not -path "./.venv/*" -not -path "./migration-backup-*/*" \
    -exec sed -i 's/github\.com\/jclee94\/blacklist/github.com\/qws941\/blacklist/g' {} \;

# 4. 환경 변수 및 설정 파일 업데이트
echo "⚙️ 환경 설정 파일 업데이트 중..."
find . -name ".env*" -o -name "*.env" -o -name "config.py" -o -name "settings.py" \
    -not -path "./.git/*" -not -path "./.venv/*" -not -path "./migration-backup-*/*" \
    -exec sed -i 's/REGISTRY_USERNAME=jclee94/REGISTRY_USERNAME=qws941/g' {} \;

# 5. 차트 및 Helm 설정 업데이트
echo "⛵ Helm Charts 업데이트 중..."
find charts/ -type f \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null \
    -exec sed -i 's/jclee94@example\.com/qws941@example.com/g' {} \; || true

# 6. 업데이트된 파일 목록 생성
echo "📊 변경된 파일 목록 생성..."
echo "=== jclee94 → qws941 마이그레이션 변경 파일 목록 ===" > migration-changes-$(date +%Y%m%d).log
echo "변경 시간: $(date)" >> migration-changes-$(date +%Y%m%d).log
echo "" >> migration-changes-$(date +%Y%m%d).log

# GitHub Pages URL 변경된 파일들
echo "1. GitHub Pages URL 변경 파일들:" >> migration-changes-$(date +%Y%m%d).log
grep -r "qws941.github.io/blacklist" . --include="*.md" --include="*.yml" --include="*.yaml" --include="*.json" \
    --exclude-dir=".git" --exclude-dir=".venv" --exclude-dir="migration-backup-*" \
    | cut -d: -f1 | sort | uniq >> migration-changes-$(date +%Y%m%d).log
echo "" >> migration-changes-$(date +%Y%m%d).log

# Docker Registry 변경된 파일들
echo "2. Docker Registry 네임스페이스 변경 파일들:" >> migration-changes-$(date +%Y%m%d).log
grep -r "registry.jclee.me/qws941/blacklist" . --include="*.md" --include="*.yml" --include="*.yaml" --include="*.json" \
    --exclude-dir=".git" --exclude-dir=".venv" --exclude-dir="migration-backup-*" \
    | cut -d: -f1 | sort | uniq >> migration-changes-$(date +%Y%m%d).log

echo "🎉 마이그레이션 완료!"
echo "📂 백업 위치: migration-backup-$(date +%Y%m%d)/"
echo "📋 변경 로그: migration-changes-$(date +%Y%m%d).log"
echo ""
echo "다음 단계:"
echo "1. git add -A"
echo "2. git commit -m 'migrate: jclee94 → qws941 완전 마이그레이션'"
echo "3. git push origin main"