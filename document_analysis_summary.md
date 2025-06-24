# Document Analysis Summary

## 분석 완료된 내용

### SECUDIUM (SK쉴더스)
- **데이터 위치**: `/document/secudium/secudium.skinfosec.co.kr/`
- **발견된 내용**:
  - 94개의 블랙리스트 항목 (2025년 3월-5월)
  - 각 항목은 Excel 파일 다운로드 링크 포함
  - 파일명 예시: "25년 05월 Blacklist 현황.xlsx"
  - 메타데이터 IP (10.200.200.2)는 내부 IP로 실제 블랙리스트가 아님

### REGTECH (금융보안원)
- **데이터 위치**: `/document/regtech/`
- **발견된 내용**:
  - Postman collection에 다운로드 엔드포인트 확인
  - `/fcti/securityAdvisory/advisoryListDownloadXlsx` - Excel 다운로드
  - 인증이 필요한 API 구조

### 실제 블랙리스트 IP 위치
- Excel 파일 내부에 실제 IP 주소가 포함되어 있음
- 현재 document 폴더에는 Excel 파일이 없음 (다운로드 필요)
- HTML/JSON 파일은 메타데이터만 포함

## 데이터베이스 상태
- 20개의 샘플 IP 추가됨 (한국/중국 악성 IP 패턴 기반)
- SECUDIUM: 15개
- REGTECH: 5개

## 다음 단계
1. Excel 파일 다운로드 자동화 구현
2. Excel 파일 파싱하여 실제 IP 추출
3. 실시간 수집 시스템 구축

## 주요 발견사항
- SECUDIUM은 매일 블랙리스트 업데이트
- SK쉴더스 SOC 센터에서 24시간 운영
- 각 블랙리스트는 날짜별로 구분되어 관리됨