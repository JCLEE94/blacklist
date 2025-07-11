# Blacklist Management System - 프레젠테이션

이 디렉토리에는 Blacklist Management System의 SVG 기반 프레젠테이션 자료가 포함되어 있습니다.

## 파일 구성

- `blacklist-system-presentation.svg` - 전체 프레젠테이션 SVG 파일 (5개 슬라이드)
- `index.html` - 프레젠테이션 뷰어 (네비게이션 포함)
- `README.md` - 이 문서

## 슬라이드 구성

1. **타이틀 슬라이드**
   - 시스템 소개
   - 주요 기술 스택 표시

2. **시스템 개요**
   - 4가지 핵심 기능
   - 아키텍처 다이어그램

3. **시스템 아키텍처**
   - 상세 컴포넌트 설명
   - 데이터 처리 흐름도

4. **CI/CD 파이프라인**
   - GitOps 자동화 프로세스
   - ArgoCD Image Updater 통합

5. **시스템 장점 및 활용**
   - 핵심 장점 3가지
   - 실제 활용 사례

## 사용 방법

### 웹 브라우저에서 보기
```bash
# 프레젠테이션 디렉토리로 이동
cd docs/presentation

# Python 웹 서버 실행
python3 -m http.server 8000

# 브라우저에서 열기
# http://localhost:8000
```

### 네비게이션
- **마우스**: 이전/다음 버튼 클릭
- **키보드**: 
  - `←` / `→` : 이전/다음 슬라이드
  - `1`~`5` : 특정 슬라이드로 이동
  - `F` : 전체화면 모드
  - `ESC` : 전체화면 종료
- **터치**: 좌우 스와이프 (모바일)

### 전체화면 프레젠테이션
1. 브라우저에서 `index.html` 열기
2. `F` 키 또는 "전체화면" 버튼 클릭
3. 화살표 키로 네비게이션

## SVG 파일 직접 사용

SVG 파일은 독립적으로도 사용 가능합니다:
- 이미지 뷰어에서 직접 열기
- 다른 문서에 임베드
- PDF로 변환

## 커스터마이징

### 색상 테마 변경
SVG 파일의 gradient 정의 부분에서 색상 수정:
```xml
<linearGradient id="slideGradient">
  <stop offset="0%" style="stop-color:#1a1a2e"/>
  <stop offset="100%" style="stop-color:#16213e"/>
</linearGradient>
```

### 슬라이드 추가
1. SVG 파일에 새로운 `<g id="slide6">` 그룹 추가
2. `transform="translate(0, 5400)"` 속성으로 위치 지정
3. `index.html`의 `totalSlides` 변수 업데이트

## 기술 사양

- **SVG 크기**: 1920x5400 (각 슬라이드 1920x1080)
- **호환성**: 모든 모던 브라우저 지원
- **반응형**: 화면 크기에 자동 조정
- **애니메이션**: CSS transition 효과

## 내보내기 옵션

### PDF로 변환
```bash
# Inkscape 사용
inkscape blacklist-system-presentation.svg --export-pdf=presentation.pdf

# 또는 브라우저에서 인쇄 → PDF로 저장
```

### PNG 이미지로 변환
```bash
# 각 슬라이드를 개별 PNG로 변환
inkscape blacklist-system-presentation.svg --export-area=0:0:1920:1080 --export-png=slide1.png
inkscape blacklist-system-presentation.svg --export-area=0:1080:1920:2160 --export-png=slide2.png
# ... 계속
```

## 문제 해결

### SVG가 표시되지 않는 경우
- 브라우저 캐시 삭제
- 다른 브라우저로 시도
- 개발자 도구에서 에러 확인

### 애니메이션이 작동하지 않는 경우
- JavaScript가 활성화되어 있는지 확인
- 브라우저 콘솔에서 에러 확인

## 라이선스

이 프레젠테이션은 Blacklist Management System 프로젝트의 일부로 제공됩니다.