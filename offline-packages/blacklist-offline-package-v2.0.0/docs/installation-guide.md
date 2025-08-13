# 블랙리스트 시스템 설치 가이드

## 시스템 요구사항

- OS: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- CPU: x86_64
- 메모리: 4GB RAM 최소, 8GB 권장
- 디스크: 10GB 여유 공간 최소
- Docker: 20.10+
- Python: 3.9+

## 설치 단계

1. 패키지 압축 해제
2. 설치 스크립트 실행: `sudo ./scripts/install.sh`
3. 환경 변수 설정: `/opt/blacklist/.env`
4. 서비스 시작: `systemctl start blacklist`

자세한 내용은 각 스크립트의 주석을 참고하세요.
