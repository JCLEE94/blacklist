# Jenkins Migration Guide - GitHub Actions to Jenkins

## 📋 목차
1. [개요](#개요)
2. [마이그레이션 전략](#마이그레이션-전략)
3. [Jenkins 설치 및 설정](#jenkins-설치-및-설정)
4. [파이프라인 구성](#파이프라인-구성)
5. [기능 매핑](#기능-매핑)
6. [운영 가이드](#운영-가이드)

## 개요

이 가이드는 Blacklist Management System의 CI/CD를 GitHub Actions에서 Jenkins로 마이그레이션하는 완전한 지침을 제공합니다.

### 마이그레이션 이점
- **완전한 제어**: 온프레미스 환경에서 완전한 파이프라인 제어
- **비용 절감**: GitHub Actions 분당 요금 없음
- **커스터마이징**: 기업 환경에 맞춘 완전한 커스터마이징
- **보안 강화**: 내부 네트워크에서만 접근 가능
- **확장성**: 필요에 따라 에이전트 추가 가능

## 마이그레이션 전략

### 단계별 접근
1. **Phase 1**: Jenkins 환경 구축 (1-2일)
2. **Phase 2**: 파이프라인 마이그레이션 (2-3일)
3. **Phase 3**: 테스트 및 검증 (1-2일)
4. **Phase 4**: 프로덕션 전환 (1일)
5. **Phase 5**: GitHub Actions 비활성화 (전환 후 1주일)

### 병렬 운영 기간
- 최소 1주일간 GitHub Actions와 Jenkins 병렬 운영
- 안정성 확인 후 GitHub Actions 비활성화

## Jenkins 설치 및 설정

### 1. Docker Compose로 Jenkins 실행

```bash
# Jenkins 디렉토리 생성
mkdir -p jenkins/jenkins-config

# Docker Compose 실행
cd jenkins
docker-compose -f docker-compose.jenkins.yml up -d

# Jenkins 상태 확인
docker-compose ps
```

### 2. 초기 설정

```bash
# 초기 관리자 비밀번호 확인
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# 브라우저에서 접속
# http://localhost:8080
```

### 3. 자동 설정 스크립트 실행

```bash
# Jenkins 설정 자동화
./jenkins/jenkins-setup.sh

# 스크립트가 수행하는 작업:
# - 필요한 플러그인 설치
# - Docker 및 Python 환경 구성
# - 자격증명 생성
# - 파이프라인 Job 생성
```

### 4. 필수 플러그인 설치

Jenkins 관리 → 플러그인 관리에서 다음 플러그인 설치:

| 플러그인 | 용도 |
|---------|------|
| Git | Git 저장소 연동 |
| GitHub | GitHub 통합 |
| Pipeline | 파이프라인 지원 |
| Docker | Docker 빌드 및 배포 |
| Blue Ocean | 현대적 UI |
| Credentials Binding | 자격증명 관리 |
| Timestamper | 타임스탬프 |
| AnsiColor | 컬러 출력 |
| HTML Publisher | 테스트 리포트 |

## 파이프라인 구성

### 1. Jenkinsfile 배치
프로젝트 루트에 생성된 `Jenkinsfile` 사용

### 2. 파이프라인 Job 생성

#### 옵션 A: UI를 통한 생성
1. Jenkins 대시보드 → "새 Item"
2. 이름: `blacklist-pipeline`
3. 타입: "Pipeline" 선택
4. Pipeline 섹션에서 "Pipeline script from SCM" 선택
5. SCM: Git
6. Repository URL: `https://github.com/qws941/blacklist.git`
7. Script Path: `Jenkinsfile`

#### 옵션 B: Job Template 사용
```bash
# Job 템플릿 import
java -jar jenkins-cli.jar -s http://localhost:8080 \
    -auth admin:password \
    create-job blacklist-pipeline < jenkins/job-templates/blacklist-multibranch.xml
```

### 3. 자격증명 설정

Jenkins 관리 → 자격증명에서 추가:

| ID | 타입 | 설명 | 값 |
|----|-----|------|-----|
| registry-jclee-credentials | Username/Password | Docker Registry | jclee94/bingogo1 |
| github-credentials | Username/Password | GitHub Access | username/token |
| github-ssh-key | SSH Private Key | GitHub SSH | SSH 키 |

### 4. 환경 변수 구성

Jenkins 관리 → 시스템 구성 → 전역 properties:

```properties
REGISTRY=registry.jclee.me
IMAGE_NAME=blacklist
PYTHON_VERSION=3.11
TEST_COVERAGE_THRESHOLD=19
API_PERFORMANCE_THRESHOLD=100
```

## 기능 매핑

### GitHub Actions vs Jenkins 매핑

| GitHub Actions | Jenkins | 설명 |
|---------------|---------|------|
| `on: push` | `triggers { githubPush() }` | Push 이벤트 트리거 |
| `runs-on: ubuntu-latest` | `agent any` | 실행 환경 |
| `env:` | `environment { }` | 환경 변수 |
| `steps:` | `steps { }` | 실행 단계 |
| `if:` | `when { }` | 조건부 실행 |
| `needs:` | `stage` 순서 | 의존성 관리 |
| `matrix:` | `parallel { }` | 병렬 실행 |
| `secrets.` | `withCredentials()` | 비밀 관리 |
| `actions/checkout` | `checkout scm` | 소스 체크아웃 |
| `actions/setup-python` | Python 설치 스크립트 | Python 환경 |
| `docker/build-push-action` | `docker.build()` | Docker 빌드 |

### 주요 기능 비교

#### 1. 품질 게이트
- **GitHub Actions**: 별도 step으로 구현
- **Jenkins**: `stage('Quality Gates')` 내 병렬 실행

#### 2. 보안 스캔
- **GitHub Actions**: Trivy Action 사용
- **Jenkins**: Trivy CLI 직접 실행

#### 3. 버전 관리
- **GitHub Actions**: 스크립트로 package.json 수정
- **Jenkins**: `readJSON`/`writeJSON` 파이프라인 함수

#### 4. Docker 빌드
- **GitHub Actions**: `docker/build-push-action`
- **Jenkins**: Docker Pipeline 플러그인

#### 5. Blue-Green 배포
- 두 플랫폼 모두 커스텀 스크립트 사용
- Jenkins는 `deploy-blue-green.sh` 호출

## 운영 가이드

### 1. 일일 운영

#### 파이프라인 모니터링
```bash
# 실행 중인 빌드 확인
curl http://localhost:8080/job/blacklist-pipeline/api/json?pretty=true

# 최근 빌드 히스토리
curl http://localhost:8080/job/blacklist-pipeline/api/json?tree=builds[number,status,timestamp,result]
```

#### 수동 빌드 트리거
```bash
# CLI로 빌드 시작
java -jar jenkins-cli.jar -s http://localhost:8080 \
    -auth admin:password \
    build blacklist-pipeline

# 파라미터와 함께 빌드
java -jar jenkins-cli.jar -s http://localhost:8080 \
    -auth admin:password \
    build blacklist-pipeline -p BRANCH=develop
```

### 2. 트러블슈팅

#### 일반적인 문제 해결

| 문제 | 원인 | 해결 방법 |
|-----|------|----------|
| Docker 권한 오류 | Jenkins가 Docker 접근 불가 | Jenkins 컨테이너를 privileged 모드로 실행 |
| Python 모듈 없음 | 가상환경 미활성화 | `venv` 활성화 확인 |
| 자격증명 오류 | 잘못된 자격증명 ID | Jenkins 자격증명 관리에서 확인 |
| 빌드 타임아웃 | 성능 이슈 | 타임아웃 설정 증가 |
| 디스크 공간 부족 | 오래된 아티팩트 | 빌드 히스토리 정리 |

#### 로그 확인
```bash
# Jenkins 시스템 로그
docker logs jenkins

# 특정 빌드 로그
curl http://localhost:8080/job/blacklist-pipeline/lastBuild/consoleText

# Pipeline 단계별 로그
curl http://localhost:8080/job/blacklist-pipeline/lastBuild/wfapi/
```

### 3. 백업 및 복구

#### Jenkins 백업
```bash
# Jenkins 홈 디렉토리 백업
docker exec jenkins tar -czf /tmp/jenkins-backup.tar.gz \
    /var/jenkins_home/jobs \
    /var/jenkins_home/credentials.xml \
    /var/jenkins_home/config.xml

# 백업 파일 복사
docker cp jenkins:/tmp/jenkins-backup.tar.gz ./backups/
```

#### 복구
```bash
# 백업 파일 복원
docker cp ./backups/jenkins-backup.tar.gz jenkins:/tmp/
docker exec jenkins tar -xzf /tmp/jenkins-backup.tar.gz -C /
docker restart jenkins
```

### 4. 성능 튜닝

#### Jenkins JVM 설정
```bash
# docker-compose.jenkins.yml에서 수정
environment:
  - JAVA_OPTS=-Xmx4g -Xms2g -XX:MaxPermSize=512m
```

#### 동시 빌드 제한
```groovy
// Jenkinsfile에서 설정
options {
    disableConcurrentBuilds()
    throttle(['blacklist-deployment'])
}
```

#### 아티팩트 보관 정책
```groovy
options {
    buildDiscarder(logRotator(
        numToKeepStr: '10',
        artifactNumToKeepStr: '5'
    ))
}
```

### 5. 모니터링 및 알림

#### Slack 통합
```groovy
post {
    success {
        slackSend(
            color: 'good',
            message: "Build Success: ${env.JOB_NAME} - ${env.BUILD_NUMBER}"
        )
    }
    failure {
        slackSend(
            color: 'danger',
            message: "Build Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}"
        )
    }
}
```

#### 이메일 알림
```groovy
post {
    failure {
        emailext(
            subject: "Build Failed: ${env.JOB_NAME}",
            body: "Check console output at ${env.BUILD_URL}",
            to: 'team@example.com'
        )
    }
}
```

## 마이그레이션 체크리스트

### Phase 1: 준비
- [ ] Jenkins 서버 프로비저닝
- [ ] Docker 및 Docker Compose 설치
- [ ] 네트워크 및 방화벽 설정
- [ ] 백업 전략 수립

### Phase 2: 설치
- [ ] Jenkins 컨테이너 실행
- [ ] 초기 설정 완료
- [ ] 필수 플러그인 설치
- [ ] 자격증명 구성

### Phase 3: 구성
- [ ] Jenkinsfile 프로젝트에 추가
- [ ] Pipeline Job 생성
- [ ] 환경 변수 설정
- [ ] 빌드 트리거 구성

### Phase 4: 테스트
- [ ] 수동 빌드 실행
- [ ] 자동 트리거 테스트
- [ ] Blue-Green 배포 검증
- [ ] 롤백 시나리오 테스트

### Phase 5: 전환
- [ ] 프로덕션 파이프라인 활성화
- [ ] 모니터링 설정
- [ ] 알림 구성
- [ ] 문서 업데이트

### Phase 6: 정리
- [ ] GitHub Actions workflow 비활성화
- [ ] 불필요한 시크릿 제거
- [ ] 팀 교육 완료
- [ ] 운영 매뉴얼 작성

## 고급 설정

### Shared Library 사용
```groovy
@Library('blacklist-shared-library') _

blacklistPipeline {
    registry = 'registry.jclee.me'
    imageName = 'blacklist'
    pythonVersion = '3.11'
}
```

### Kubernetes 통합
```groovy
pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: python
    image: python:3.11
    command: ['cat']
    tty: true
  - name: docker
    image: docker:latest
    command: ['cat']
    tty: true
    volumeMounts:
    - name: dockersock
      mountPath: /var/run/docker.sock
  volumes:
  - name: dockersock
    hostPath:
      path: /var/run/docker.sock
"""
        }
    }
}
```

## 참고 자료

### Jenkins 문서
- [Jenkins Pipeline 문법](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Blue Ocean 사용법](https://www.jenkins.io/doc/book/blueocean/)
- [Docker Pipeline 플러그인](https://plugins.jenkins.io/docker-workflow/)

### 프로젝트 파일
- `Jenkinsfile`: 메인 파이프라인 스크립트
- `jenkins/docker-compose.jenkins.yml`: Jenkins 실행 구성
- `jenkins/jenkins-setup.sh`: 자동 설정 스크립트
- `jenkins/scripts/deploy-blue-green.sh`: Blue-Green 배포 스크립트
- `jenkins/job-templates/`: Job 템플릿 파일
- `jenkins/shared-library/`: 재사용 가능한 파이프라인 컴포넌트

## 문의 및 지원

Jenkins 마이그레이션 관련 문의:
- 이메일: devops@jclee.me
- Slack: #jenkins-migration
- 문서: https://wiki.jclee.me/jenkins-migration