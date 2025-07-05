# CI/CD 파이프라인 통합 테스트 가이드

## 개요

이 문서는 Blacklist 프로젝트의 CI/CD 파이프라인에 대한 통합 테스트 전략과 구현 방법을 설명합니다.

## 테스트 구조

```
tests/integration/
├── conftest.py                  # pytest fixtures 및 공통 설정
├── test_cicd_pipeline.py       # 파이프라인 통합 테스트
├── test_cicd_refactoring.py    # 리팩토링 및 테스트 가능성
└── test_cicd_mocks.py          # 외부 서비스 모킹

scripts/
├── lib/
│   └── cicd_testability.py    # 테스트 가능한 파이프라인 유틸리티
└── test-cicd-pipeline.sh       # 통합 테스트 실행 스크립트
```

## 주요 테스트 영역

### 1. 파이프라인 트리거 테스트
- main/develop 브랜치 푸시 트리거
- Pull Request 트리거
- 경로 무시 (markdown, docs)
- 동시 실행 취소

### 2. 코드 품질 단계
- Python 구문 검사
- 코드 스타일 (flake8)
- 보안 스캔 (하드코딩된 시크릿)
- 의존성 검증

### 3. 테스트 단계
- pytest 실행
- 코드 커버리지 확인
- 테스트 리포트 생성

### 4. 빌드 단계
- Docker 멀티스테이지 빌드
- 빌드 캐시 활용
- 이미지 태깅 (latest, sha-*, date-*)
- 레지스트리 인증

### 5. 배포 단계
- ArgoCD 애플리케이션 동기화
- 이미지 업데이트 감지
- 헬스체크 검증
- 실패 시 롤백

### 6. End-to-End 플로우
- 커밋부터 배포까지 전체 플로우
- 각 단계별 실패 복구
- 알림 및 모니터링

## 테스트 실행 방법

### 1. 전체 테스트 실행
```bash
# 통합 테스트 스크립트 실행
./scripts/test-cicd-pipeline.sh

# 또는 pytest 직접 실행
pytest tests/integration/ -v
```

### 2. 특정 테스트만 실행
```bash
# 파이프라인 트리거 테스트만
pytest tests/integration/test_cicd_pipeline.py::TestCICDPipelineTriggers -v

# 리팩토링 테스트만
pytest tests/integration/test_cicd_refactoring.py -v
```

### 3. 드라이런 모드
```bash
# 실제 명령 실행 없이 테스트
DRY_RUN=true ./scripts/test-cicd-pipeline.sh

# Python 유틸리티 드라이런
python scripts/lib/cicd_testability.py --dry-run
```

## 테스트 가능성을 위한 리팩토링

### 1. 설정 중앙화
```python
from scripts.lib.cicd_testability import PipelineConfig

# 환경 변수 기반 설정
config = PipelineConfig(
    registry=os.getenv("REGISTRY", "registry.jclee.me"),
    image_name=os.getenv("IMAGE_NAME", "blacklist"),
    dry_run=os.getenv("DRY_RUN", "false").lower() == "true"
)
```

### 2. 파이프라인 단계 모듈화
```python
from scripts.lib.cicd_testability import (
    CodeQualityStage,
    TestStage,
    BuildStage,
    DeploymentStage,
    PipelineOrchestrator
)

# 개별 단계 실행
stage = CodeQualityStage(config)
result = stage.execute()

# 전체 파이프라인 실행
orchestrator = PipelineOrchestrator(config)
results = orchestrator.run()
```

### 3. 훅 시스템
```python
class CustomStage(PipelineStage):
    def pre_hook(self):
        """단계 시작 전 커스텀 로직"""
        super().pre_hook()
        # 추가 로직
    
    def post_hook(self):
        """단계 종료 후 커스텀 로직"""
        # 추가 로직
        super().post_hook()
```

## 모킹 전략

### 1. 외부 서비스 모킹
```python
# Docker 모킹
@patch('subprocess.run')
def test_docker_build(mock_run):
    mock_run.return_value = Mock(returncode=0)
    # 테스트 로직

# ArgoCD 모킹
@patch('subprocess.run')
def test_argocd_sync(mock_run):
    mock_run.side_effect = [
        Mock(returncode=0, stdout=b"Synced")
    ]
    # 테스트 로직
```

### 2. 파일 시스템 모킹
```python
@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        # 디렉토리 구조 생성
        yield workspace
```

## 통합 테스트 모범 사례

### 1. 격리된 테스트 환경
- 각 테스트는 독립적으로 실행 가능해야 함
- 외부 의존성은 모두 모킹
- 테스트 후 정리 작업 수행

### 2. 실제와 유사한 시나리오
- 실제 파이프라인 흐름을 따라 테스트
- 실패 시나리오도 포함
- 타이밍과 순서 고려

### 3. 성능 고려사항
- 빠른 피드백을 위해 테스트 최적화
- 필요한 경우만 통합 테스트 사용
- 단위 테스트로 가능한 부분은 분리

## 디버깅 팁

### 1. 상세 로그 활성화
```bash
VERBOSE=true pytest tests/integration/ -v -s
```

### 2. 특정 단계만 테스트
```python
python scripts/lib/cicd_testability.py --stage code-quality --verbose
```

### 3. 실패 시 상태 확인
```python
# 테스트 실패 시 상태 덤프
print(json.dumps(results, indent=2))
```

## 지속적 개선

### 1. 테스트 커버리지 모니터링
```bash
pytest tests/integration/ --cov=scripts.lib --cov-report=html
```

### 2. 테스트 실행 시간 추적
```bash
pytest tests/integration/ --durations=10
```

### 3. 플레이키 테스트 식별
- 여러 번 실행하여 안정성 확인
- 타이밍 의존성 제거
- 명확한 전제 조건 설정

## 참고 자료

- [pytest 문서](https://docs.pytest.org/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [ArgoCD 문서](https://argo-cd.readthedocs.io/)
- [Docker 문서](https://docs.docker.com/)