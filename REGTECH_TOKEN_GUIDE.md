# REGTECH Bearer Token 관리 가이드

## Bearer Token이란?

REGTECH는 JWT (JSON Web Token) 기반의 Bearer 인증을 사용합니다. 
- 토큰은 일정 시간 후 만료됩니다 (보통 24시간~7일)
- 만료된 토큰으로는 데이터를 수집할 수 없습니다
- 새로운 토큰을 얻으려면 브라우저에서 다시 로그인해야 합니다

## 현재 상황

- **문제**: 계정 로그인이 `error=true`로 실패 (비밀번호 변경 또는 계정 잠금)
- **해결책**: 브라우저에서 수동 로그인 후 Bearer token 추출

## Bearer Token 얻는 방법

### 1. 브라우저에서 로그인
```
1. https://regtech.fsec.or.kr 접속
2. nextrade / Sprtmxm1@3 로그인
   (로그인 실패시 계정 확인 필요)
3. 로그인 성공 확인
```

### 2. Bearer Token 추출
```
1. F12 (개발자 도구)
2. Application 탭
3. Cookies → regtech.fsec.or.kr
4. regtech-va 쿠키 찾기
5. Value 복사 (Bearer로 시작하는 긴 문자열)
```

### 3. 토큰 사용

#### 방법 1: 환경변수 설정 (Docker)
```bash
# .env 파일에 추가
REGTECH_BEARER_TOKEN=BearereyJ0eXAiOiJKV1Q...

# Docker 재시작
docker-compose down
docker-compose up -d
```

#### 방법 2: 수동 스크립트 실행
```bash
# 토큰 설정하고 스크립트 실행
export REGTECH_BEARER_TOKEN="Bearer..."
python3 scripts/regtech_excel_collector.py
```

#### 방법 3: 직접 API 호출
```bash
# Collection API로 트리거 (토큰이 환경변수에 설정된 경우)
curl -X POST http://localhost:8541/api/collection/regtech/trigger
```

## 자동화 옵션

### 1. Cron Job 설정
```bash
# 매일 오전 6시 실행
0 6 * * * REGTECH_BEARER_TOKEN="Bearer..." /usr/bin/python3 /app/scripts/regtech_excel_collector.py
```

### 2. Docker 환경변수
```yaml
# docker-compose.yml
environment:
  - REGTECH_BEARER_TOKEN=${REGTECH_BEARER_TOKEN}
```

### 3. 토큰 파일 사용
```bash
# 토큰을 파일에 저장
echo "Bearer..." > /tmp/regtech_token.txt

# 스크립트에서 읽기
export REGTECH_BEARER_TOKEN=$(cat /tmp/regtech_token.txt)
```

## 문제 해결

### 토큰이 만료된 경우
- 증상: 302 리다이렉트, 0개 IP 수집
- 해결: 브라우저에서 다시 로그인하여 새 토큰 획득

### 로그인이 실패하는 경우
- 증상: `error=true` in redirect URL
- 가능한 원인:
  1. 비밀번호 변경됨
  2. 계정 잠김 (5회 실패시 10분 잠금)
  3. OTP 등 추가 인증 필요
  4. IP 차단

### 대안: PowerShell 스크립트
Windows 환경에서는 제공된 PowerShell 스크립트 사용:
```powershell
# 토큰 설정
$session.Cookies.Add((New-Object System.Net.Cookie("regtech-va", "Bearer...", "/", "regtech.fsec.or.kr")))

# Excel 다운로드
Invoke-WebRequest -Uri "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryListDownloadXlsx" ...
```

## 장기적 해결책

1. **정기적 토큰 갱신**: 토큰 만료 전에 미리 갱신
2. **알림 설정**: 수집 실패시 알림 발송
3. **폴백 메커니즘**: REGTECH 실패시 다른 소스 우선 사용
4. **캐시 활용**: 마지막 성공한 데이터 유지

## 현재 구현 상태

✅ **완료**:
- Excel 다운로드 방식 구현
- Bearer token 환경변수 지원
- 자동 폴백 (Excel → HTML)
- 5,000개 이상 IP 수집 가능

❌ **미완료**:
- 자동 로그인 (계정 문제로 실패)
- 토큰 자동 갱신
- 만료 알림

## 권장사항

1. **단기**: 주기적으로 수동 토큰 갱신
2. **중기**: 토큰 만료 모니터링 추가
3. **장기**: REGTECH와 협의하여 API 키 방식 도입