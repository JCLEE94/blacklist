# CI/CD 실패 자동 이슈 생성 가이드

## 개요

CI/CD 파이프라인 실패 시 자동으로 GitHub 이슈를 생성하여 문제를 추적하고 해결할 수 있도록 합니다.

## 기능

### 1. 자동 이슈 생성
- 워크플로우 실패 시 자동으로 이슈 생성
- 실패한 job과 step 정보 포함
- 워크플로우 실행 링크 제공

### 2. 중복 방지
- 24시간 이내 동일한 워크플로우 관련 이슈가 있으면 댓글로 추가
- 불필요한 이슈 생성 방지

### 3. 상세 로그
- 실패한 job의 로그 수집
- 실패한 step 정보 표시
- 일반적인 문제 해결 가이드 포함

## 워크플로우 구성

### create-issue-on-failure.yml
재사용 가능한 워크플로우로 다음 파라미터를 받습니다:
- `workflow_name`: 실패한 워크플로우 이름
- `run_id`: GitHub Actions 실행 ID
- `run_url`: 실행 URL
- `failed_jobs`: 실패한 job 목록 (선택사항)

### 기존 워크플로우 통합
```yaml
create-issue-on-failure:
  needs: [test, build-and-push]
  if: |
    always() && 
    (needs.test.result == 'failure' || needs.build-and-push.result == 'failure')
  uses: ./.github/workflows/create-issue-on-failure.yml
  with:
    workflow_name: "Your Workflow Name"
    run_id: ${{ github.run_id }}
    run_url: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
  secrets:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 생성되는 이슈

### 이슈 제목
`🚨 CI/CD Failure: [워크플로우 이름]`

### 이슈 라벨
- `ci-failure`
- `automated`
- `bug`
- `high-priority`

### 이슈 내용
1. 실패 요약
2. 워크플로우 링크
3. 실패한 job/step 정보
4. 일반적인 문제 해결 가이드
5. 체크리스트

## 사용 예시

### 1. 새로운 이슈 생성
- 처음 실패 시 새 이슈 생성
- 담당자 자동 할당 가능

### 2. 기존 이슈 업데이트
- 24시간 이내 동일 워크플로우 실패 시
- 기존 이슈에 댓글 추가

## 문제 해결

### 이슈가 생성되지 않는 경우
1. `GITHUB_TOKEN` 권한 확인
2. 워크플로우 파일 경로 확인
3. if 조건 확인

### 중복 이슈가 생성되는 경우
1. 라벨 설정 확인
2. 제목 형식 확인
3. 24시간 타임윈도우 조정

## 커스터마이징

### 라벨 변경
`create-issue-on-failure.yml`의 labels 배열 수정

### 이슈 템플릿 변경
issueBody 변수의 내용 수정

### 중복 체크 기간 변경
`since` 파라미터의 시간 계산 수정

## 모니터링

### 생성된 이슈 확인
```
https://github.com/[owner]/[repo]/issues?q=is:issue+label:ci-failure
```

### 자동화 통계
- 생성된 이슈 수
- 해결 시간
- 반복되는 실패 패턴

## 베스트 프랙티스

1. **빠른 대응**: 이슈 생성 시 즉시 확인
2. **근본 원인 분석**: 반복되는 실패 패턴 파악
3. **문서화**: 해결 방법을 이슈에 기록
4. **예방**: 반복되는 문제는 코드 개선으로 해결

## 향후 개선사항

1. Slack/Discord 알림 연동
2. 자동 담당자 지정
3. 실패 패턴 분석 대시보드
4. 자동 수정 제안