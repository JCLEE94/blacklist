# Claude Max Code Base Action 베스트 프랙티스

## 🚀 효과적인 사용법

### 1. 구체적이고 명확한 지시
```bash
# ❌ 나쁜 예
@claude 코드를 개선해주세요

# ✅ 좋은 예  
@claude src/core/unified_service.py의 get_enhanced_blacklist 메서드에서 source 필드가 "unknown"으로 나오는 버그를 수정해주세요. 데이터베이스에는 REGTECH, SECUDIUM 값이 있는데 API 응답에서는 unknown으로 표시됩니다.
```

### 2. 컨텍스트 제공
```bash
# ✅ 컨텍스트와 함께 요청
@claude 새로운 IP 검색 API를 추가해주세요. 
요구사항:
- 경로: /api/search/ip/{ip_address}
- 캐싱 적용 (TTL 300초)
- FortiGate 형식 응답 지원
- Rate limiting 적용
- 에러 핸들링 포함
```

### 3. 단계별 작업 요청
```bash
@claude 다음 순서로 작업해주세요:
1. 데이터베이스 스키마 검토
2. 버그 원인 분석  
3. 수정 코드 작성
4. 테스트 케이스 추가
5. 통합 테스트 실행
```

## 🔧 기술별 활용 팁

### Python/Flask 개발
```bash
@claude Flask 라우트에 입력 검증과 SQL 인젝션 방지를 추가해주세요
@claude 이 함수에 타입 힌트와 docstring을 추가해주세요
@claude pytest로 이 API 엔드포인트 테스트를 작성해주세요
```

### Docker/Kubernetes
```bash
@claude Dockerfile을 멀티스테이지 빌드로 최적화해주세요
@claude K8s 매니페스트에 리소스 제한과 헬스체크를 추가해주세요
@claude ArgoCD 배포를 위한 kustomization.yaml을 생성해주세요
```

### 데이터베이스 최적화
```bash
@claude 이 SQL 쿼리의 성능을 개선하고 인덱스를 추가해주세요
@claude 데이터베이스 연결 풀링을 구현해주세요
@claude SQLite에서 PostgreSQL로 마이그레이션 스크립트를 작성해주세요
```

### 보안 강화
```bash
@claude 모든 환경변수 하드코딩을 찾아서 수정해주세요
@claude API 엔드포인트에 인증과 권한 검사를 추가해주세요
@claude 입력 검증과 XSS 방지 코드를 추가해주세요
```

## 📊 성능 최적화 요청

### 캐싱 최적화
```bash
@claude Redis 캐싱 전략을 개선하고 TTL을 최적화해주세요
@claude 메모리 캐시 fallback 로직을 구현해주세요
```

### API 성능
```bash
@claude API 응답 시간을 줄이기 위해 비동기 처리를 추가해주세요
@claude 대용량 데이터 처리를 위한 페이징을 구현해주세요
```

## 🧪 테스트 자동화

### 단위 테스트
```bash
@claude 이 클래스의 모든 메서드에 대한 단위 테스트를 작성해주세요
@claude Mock을 사용해서 외부 API 호출 테스트를 작성해주세요
```

### 통합 테스트
```bash
@claude 전체 데이터 수집 프로세스의 통합 테스트를 작성해주세요
@claude API 엔드포인트의 E2E 테스트를 작성해주세요
```

## 🔄 CI/CD 자동화

### GitHub Actions 
```bash
@claude CI/CD 파이프라인에 보안 스캔을 추가해주세요
@claude 테스트 커버리지 리포팅을 설정해주세요
@claude 자동 배포 실패 시 롤백 로직을 추가해주세요
```

### ArgoCD 최적화
```bash
@claude ArgoCD Health Check를 커스터마이징해주세요
@claude Image Updater 설정을 최적화해주세요
```

## 📚 문서화 요청

### 코드 문서화
```bash
@claude 이 모듈의 사용법과 예시를 README에 추가해주세요
@claude API 문서를 OpenAPI 3.0 스펙으로 생성해주세요
```

### 아키텍처 문서
```bash
@claude 시스템 아키텍처 다이어그램을 mermaid로 작성해주세요
@claude 데이터 플로우 문서를 작성해주세요
```

## ⚠️ 주의사항

### 1. 범위 제한
- 한 번에 너무 많은 작업 요청 금지
- 명확한 완료 조건 제시

### 2. 검증 요청
```bash
@claude 변경사항을 적용하기 전에 영향도를 분석해주세요
@claude 이 수정으로 인한 부작용이 있는지 검토해주세요
```

### 3. 백업 고려
```bash
@claude 중요한 변경 전에 현재 설정을 백업해주세요
@claude 롤백 계획도 함께 제시해주세요
```

## 🎯 프로젝트별 전문 용어

### Blacklist 플랫폼 용어
- **위협 인텔리전스**: Threat Intelligence
- **IP 수집기**: IP Collector (REGTECH, SECUDIUM)
- **FortiGate 연동**: External Connector Integration
- **GitOps 배포**: ArgoCD-based Deployment

### 기술 스택 용어
- **의존성 주입**: Dependency Injection Container
- **멀티소스 수집**: Multi-source Data Collection
- **캐시 폴백**: Redis Primary + Memory Fallback
- **헬스체크**: Health Check Endpoints

## 📈 성과 측정

Claude Max 사용 후 다음을 확인하세요:

1. **코드 품질**: 테스트 커버리지, 보안 점수
2. **성능**: 응답 시간, 메모리 사용량
3. **안정성**: 에러 발생률, 가동 시간
4. **유지보수성**: 코드 복잡도, 문서화 수준

이 가이드를 참고하여 Claude Max Code Base Action을 효과적으로 활용하세요!