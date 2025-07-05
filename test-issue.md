# Claude Max 테스트 방법

## 1. GitHub Issue 생성
- Repository: https://github.com/JCLEE94/blacklist
- 새 Issue 생성 후 다음과 같이 작성:

```
@claude src/core/unified_service.py의 성능을 개선해주세요. 
특히 get_enhanced_blacklist 메서드에서 데이터베이스 쿼리를 최적화하고 캐싱을 강화해주세요.
```

## 2. Pull Request에서 사용
```
@claude 이 PR의 보안 취약점을 검토하고 수정해주세요.
```

## 3. 코드 리뷰 요청
```
@claude 하드코딩된 값들을 환경변수로 변경해주세요.
```

Claude Max는 멘션을 받으면:
- 코드베이스 전체 분석
- 요청된 작업 수행
- PR 생성 또는 코멘트로 결과 제공
EOF < /dev/null
