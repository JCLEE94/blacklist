#!/usr/bin/env python3
"""
REGTECH 인증 문제 해결 가이드
"""
import os
import sys

def main():
    print("🔧 REGTECH 인증 문제 해결 가이드\n")
    
    print("현재 상황:")
    print("- REGTECH 로그인이 실패함 (error=true)")
    print("- Bearer Token이 만료됨")
    print("- 데이터베이스에는 2일 전 데이터가 있음 (1000개 IP)")
    print("- 그 이후로 수집이 실패하고 있음")
    
    print("\n해결 방법:")
    print("\n1. 수동으로 새 Bearer Token 얻기:")
    print("   a) 브라우저에서 https://regtech.fsec.or.kr 접속")
    print("   b) nextrade / Sprtmxm1@3 로 로그인")
    print("   c) F12 개발자 도구 → Application → Cookies")
    print("   d) 'regtech-va' 쿠키 값 복사 (Bearer로 시작하는 긴 문자열)")
    
    print("\n2. Docker 환경변수에 Bearer Token 추가:")
    print("   deployment/docker-compose.yml 수정:")
    print("   ```")
    print("   environment:")
    print("     - REGTECH_BEARER_TOKEN=BearereyJ0eXA...")
    print("   ```")
    
    print("\n3. regtech_collector.py 수정:")
    print("   Bearer Token을 환경변수에서 읽도록 수정")
    print("   ```python")
    print("   bearer_token = os.getenv('REGTECH_BEARER_TOKEN')")
    print("   if bearer_token:")
    print("       session.cookies.set('regtech-va', bearer_token, ...)")
    print("   ```")
    
    print("\n4. 대안 - 로그인 문제 확인:")
    print("   - 계정이 잠겼을 수 있음 (5회 실패시 10분 잠금)")
    print("   - 비밀번호가 변경되었을 수 있음")
    print("   - OTP나 추가 인증이 필요할 수 있음")
    
    print("\n5. 임시 해결책:")
    print("   - 기존 데이터베이스의 REGTECH 데이터 유지")
    print("   - SECUDIUM 등 다른 소스는 정상 작동")
    print("   - 수동으로 Bearer Token 업데이트 필요시마다 갱신")
    
    print("\n권장사항:")
    print("1. 브라우저에서 수동으로 로그인 테스트")
    print("2. 성공하면 Bearer Token 추출")
    print("3. Docker 환경변수로 설정")
    print("4. 주기적으로 Token 갱신 필요")

if __name__ == "__main__":
    main()