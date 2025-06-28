# REGTECH Excel Download Update

## Summary

REGTECH 수집기를 Excel 다운로드 방식으로 업데이트했습니다. PowerShell 스크립트를 기반으로 Python 구현을 완성했습니다.

## Key Changes

### 1. Updated `src/core/regtech_collector.py`

#### Added Excel Download Support
- pandas import 추가 (optional dependency)
- `_download_excel_data()` 메서드 추가
- Excel 다운로드 엔드포인트: `/fcti/securityAdvisory/advisoryListDownloadXlsx`
- Excel 파일을 메모리에서 직접 처리 (파일 저장 불필요)

#### Collection Flow
1. Bearer Token 인증 시도 (환경변수 우선)
2. Excel 다운로드 방식으로 데이터 수집
3. 실패시 HTML 파싱 방식으로 폴백
4. BlacklistEntry 객체로 변환 및 중복 제거

#### Excel Data Processing
```python
# Excel 컬럼 매핑
- IP → ip
- 국가 → country  
- 등록사유 → attack_type
- 등록일 → detection_date
- 해제일 → extra_data['release_date']
```

### 2. Environment Variable Support
- `REGTECH_BEARER_TOKEN`: Bearer 토큰 설정
- Docker-compose.yml 업데이트

### 3. Test Results
- Excel 다운로드로 5,587개 IP 수집 성공
- 기존 HTML 파싱: 0개 (인증 실패)
- 데이터베이스의 기존 데이터: 1,000개 (2일 전)

## Usage

### Local Testing
```bash
export REGTECH_BEARER_TOKEN="Bearer..."
python3 main.py
```

### Docker Deployment
```bash
# .env 파일에 추가
echo 'REGTECH_BEARER_TOKEN=Bearer...' >> .env

# Docker 실행
docker-compose up -d
```

### Manual Collection Trigger
```bash
# 수집 상태 확인
curl http://localhost:8541/api/collection/status

# REGTECH 수집 트리거
curl -X POST http://localhost:8541/api/collection/regtech/trigger
```

## Benefits

1. **더 많은 데이터**: HTML 파싱보다 Excel에서 전체 데이터 수집 가능
2. **안정성**: 페이지네이션 불필요, 단일 요청으로 전체 데이터
3. **성능**: 빠른 다운로드 및 처리
4. **호환성**: pandas 없어도 HTML 파싱으로 폴백

## Next Steps

1. 프로덕션 환경에서 새 Bearer Token 획득
2. Docker 이미지 빌드 및 배포
3. Watchtower가 자동으로 업데이트 감지 및 배포
4. 5,000개 이상의 REGTECH IP 수집 확인