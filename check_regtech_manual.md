# REGTECH 수동 확인 방법

## 브라우저에서 직접 확인하기

1. **브라우저 열기**
   - Chrome/Edge 사용 권장

2. **REGTECH 접속**
   ```
   https://regtech.fsec.or.kr
   ```

3. **로그인**
   - ID: nextrade
   - PW: Sprtmxm1@3

4. **데이터 확인 경로들**
   - 메뉴에서 "악성IP차단" 찾기
   - 또는 직접 URL 접속:
     - https://regtech.fsec.or.kr/fcti/securityAdvisory/blackListView
     - https://regtech.fsec.or.kr/board/boardList?menuCode=HPHB0620101

5. **확인 사항**
   - 실제로 IP 데이터가 표시되는가?
   - 테이블 형태로 나오는가?
   - Excel 다운로드 버튼이 있는가?
   - 날짜 필터가 작동하는가?

## 현재 상황
- 로그인: ✅ 성공
- 쿠키 인증: ✅ 성공 
- 데이터 수집: ❌ 0개 (페이지에 데이터가 없음)
- 저장 로직: ✅ 수정 완료

## 가능한 원인
1. REGTECH 사이트에 실제로 데이터가 없음
2. 날짜 범위가 잘못됨
3. 권한 문제로 데이터가 안 보임
4. API 경로가 변경됨

## 테스트 코드
```python
# 브라우저에서 데이터를 확인한 후, 
# 실제 데이터가 있다면 HTML 구조를 분석해서
# 올바른 파싱 방법을 찾아야 합니다.
```