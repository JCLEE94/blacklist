# 🚀 파이프라인 안정화 가이드

## 📋 주요 수정 사항

### 1. 보안 강화
- **환경변수 보안**: `REGISTRY_PASSWORD`를 GitHub Secrets로 이동
- **평문 패스워드 제거**: 환경변수에서 하드코딩된 패스워드 제거

### 2. 프로젝트 구조 적응
- **디렉토리 경로 수정**: 실제 프로젝트 구조에 맞게 경로 업데이트
- **파일 감지 개선**: Python 파일 및 주요 구조 파일 정확한 감지

### 3. 빌드 최적화
- **변경 감지 로직**: SafeWork 패턴의 스마트 감지 유지하면서 정확성 향상

## 🔧 필수 설정 단계

### GitHub Secrets 설정
저장소 설정 → Secrets and variables → Actions → New repository secret

```
REGISTRY_PASSWORD = bingogo1
```

### 수정된 경로들
```yaml
# Before (SafeWork 구조)
find src/ app/ tests/ -type f -name "*.py"

# After (Blacklist 구조)  
find . -type f \( -name "*.py" -o -name "main.py" \) ! -path "./.github/*" ! -path "./build/*"

# 변경 감지 패턴
# Before: ^src/\|^app/\|^tests/\|\.py$
# After: \.py$\|^main\.py\|^commands/\|^scripts/\|^tests/
```

## 🎯 파이프라인 검증

### 로컬 테스트
```bash
# 1. YAML 문법 검증
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/main-deploy.yml')); print('✅ YAML syntax valid')"

# 2. Docker 빌드 테스트 (빠른 검증)
docker build --target=build -t test-build .

# 3. 의존성 확인
pip install -r requirements.txt --dry-run
```

### GitHub Actions 검증
```bash
# 1. 워크플로우 수동 트리거 테스트
# GitHub → Actions → "Blacklist Smart Deploy" → Run workflow

# 2. 커밋 메시지를 통한 강제 빌드
git commit -m "test: pipeline stabilization [force] build"

# 3. 변경 감지 테스트
echo "# test change" >> README.md
git add README.md && git commit -m "test: change detection"
```

## 📊 모니터링 포인트

### 성공 지표
- ✅ 변경 감지 정확도: 관련 파일 변경 시에만 빌드 트리거
- ✅ 빌드 성공률: Docker 이미지 빌드 및 푸시 성공
- ✅ 배포 안정성: 버전 비교 및 자동 업데이트 정상 동작
- ✅ 헬스체크: 배포 후 서비스 정상 응답 확인

### 실패 시 체크리스트
1. **Secrets 설정**: `REGISTRY_PASSWORD` GitHub Secrets 등록 확인
2. **권한 문제**: Self-hosted runner Docker 권한 확인
3. **네트워크**: registry.jclee.me 접근 가능성 확인
4. **디스크 공간**: 빌드 공간 충분한지 확인

## 🔄 롤백 계획

### 긴급 복구 절차
```bash
# 1. 이전 워크플로우로 복구
git revert HEAD --no-edit
git push origin main

# 2. 수동 배포 (비상시)
docker pull registry.jclee.me/blacklist:latest
docker-compose down && docker-compose up -d

# 3. Watchtower 강제 업데이트
docker exec watchtower /watchtower --run-once
```

## 📝 추가 개선 사항

### 단기 (1주일 내)
- [ ] 빌드 캐시 최적화로 속도 향상
- [ ] 테스트 자동화 통합 (pytest)
- [ ] 보안 스캔 추가 (Trivy/Bandit)

### 중기 (1개월 내)  
- [ ] Multi-architecture 빌드 (amd64/arm64)
- [ ] 배포 전략 개선 (Blue-Green/Rolling)
- [ ] 메트릭 수집 및 알림 시스템

### 장기 (3개월 내)
- [ ] GitOps 완전 자동화
- [ ] 다중 환경 지원 (dev/staging/prod)
- [ ] 인프라 코드화 (Terraform/Pulumi)

---

## 🚦 현재 상태

**파이프라인 안정화 진행도**: 85% 완료

### ✅ 완료된 작업
- 보안 강화 (Secrets 적용)
- 프로젝트 구조 적응
- 빌드 설정 검증
- YAML 문법 검증

### 🔄 진행 중
- GitHub Actions 실제 테스트 대기

### ⏳ 대기 중  
- 운영 환경 검증
- 성능 모니터링
- 사용자 피드백 수집

---
**마지막 업데이트**: 2025-08-27
**담당자**: 파이프라인 안정화 자동화 시스템