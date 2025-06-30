# Blacklist Management System - Architecture Presentation

## 🎯 Overview

Blacklist Management System의 아키텍처를 시각적으로 보여주는 인터랙티브 프레젠테이션입니다.

## 📑 슬라이드 구성

1. **타이틀 슬라이드**
   - 시스템 이름과 주요 특징
   - Enterprise Security, 100만+ IP 처리, 실시간 업데이트

2. **시스템 아키텍처**
   - Kubernetes 클러스터 구조
   - Application Pods, Data Layer, Networking

3. **데이터 수집 플로우**
   - REGTECH/SECUDIUM → Blacklist System → FortiGate
   - 데이터 처리 및 검증 과정

4. **기술 스택**
   - Python 3.9, Kubernetes, Docker, Redis
   - 엔터프라이즈급 보안 강조

5. **CI/CD 파이프라인**
   - Git Push → GitHub Actions → Registry → Watchtower
   - 자동 배포 프로세스

6. **성능 메트릭**
   - 처리 용량: 100만+ IP
   - 응답 시간: <10ms (캐시 히트)
   - 리소스 사용량 및 가용성

## 🚀 사용 방법

### 방법 1: 로컬에서 직접 열기
```bash
# 브라우저에서 직접 열기
open presentation/index.html
# 또는
xdg-open presentation/index.html  # Linux
start presentation/index.html      # Windows
```

### 방법 2: 로컬 웹 서버 사용
```bash
# Python 3
cd presentation
python3 -m http.server 8000

# Node.js
npx http-server presentation -p 8000

# 브라우저에서 접속
http://localhost:8000
```

### 방법 3: Flask 앱에 통합
```python
# src/core/app_compact.py에 추가
@app.route('/presentation')
def presentation():
    return send_from_directory('presentation', 'index.html')
```

## 🎮 조작 방법

- **다음 슬라이드**: 오른쪽 화살표 버튼 클릭 또는 키보드 → 키
- **이전 슬라이드**: 왼쪽 화살표 버튼 클릭 또는 키보드 ← 키
- **특정 슬라이드로 이동**: 하단 인디케이터 점 클릭
- **전체 화면**: F11 키 (권장)

## 🎨 디자인 특징

- **그라디언트 배경**: 각 슬라이드마다 독특한 색상 조합
- **애니메이션**: 부드러운 전환 효과와 hover 인터랙션
- **반응형 디자인**: 다양한 화면 크기에 최적화
- **모던 UI**: Tailwind CSS와 Lucide 아이콘 사용

## 📱 호환성

- Chrome, Firefox, Safari, Edge 최신 버전
- 1920x1080 이상 해상도 권장
- 모바일 기기에서도 동작 (터치 지원)

## 🛠️ 커스터마이징

### 슬라이드 추가
```javascript
const slides = [
    // 기존 슬라이드들...
    
    // 새 슬라이드 추가
    <div key="newslide" className="h-full bg-gradient-to-br from-teal-900 to-cyan-900 p-12">
        <h2 className="text-5xl font-bold text-white mb-12 text-center">새로운 슬라이드</h2>
        {/* 컨텐츠 */}
    </div>
];
```

### 색상 테마 변경
- 각 슬라이드의 `bg-gradient-to-br` 클래스 수정
- from-색상-숫자 to-색상-숫자 형식

### 애니메이션 속도 조정
- CSS의 animation duration 값 변경
- transition-all duration-300 → duration-500 등

## 📸 스크린샷 캡처

프레젠테이션 모드에서 스크린샷을 찍으면 고품질 이미지를 얻을 수 있습니다.

1. F11로 전체 화면 진입
2. 원하는 슬라이드로 이동
3. 스크린샷 도구 사용 (Windows: Win+Shift+S, Mac: Cmd+Shift+4)

## 🎥 프레젠테이션 팁

1. **사전 로딩**: 모든 슬라이드를 한 번씩 미리 보기
2. **네트워크 불필요**: 모든 리소스가 CDN에서 로드
3. **백업 준비**: PDF 버전도 준비 권장
4. **테스트**: 실제 환경에서 미리 테스트

---

Built with React, Tailwind CSS, and Lucide Icons