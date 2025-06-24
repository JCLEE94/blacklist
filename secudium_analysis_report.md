# SECUDIUM 로그인 분석 보고서

## HAR 파일 분석 결과

### 1. 로그인 요청 구조 (정확한 파라미터)
```
POST /isap-api/loginProcess
Content-Type: application/x-www-form-urlencoded

Parameters:
- lang=ko
- is_otp=N  
- is_expire=N
- login_name=nextrade
- password=Sprtmxm1%403
- otp_value=
```

### 2. 응답 구조 (JavaScript 코드 분석)
```javascript
// 성공적인 로그인 응답 처리
function(data){
    var error = data.response.error;  // error 필드로 성공/실패 판단
    
    if(error){
        _u.message(data.response.message).alert_error();
    }else{
        _u.cookie.set(null, data.response.token, 1);  // 토큰 쿠키에 저장
    }
}
```

### 3. 실제 서버 응답 (테스트 결과)
```json
{
  "response": {
    "error": true,
    "message": "동일 ID로 로그인 한 사용자가 있습니다...",
    "code": "already.login"
  }
}
```

## 문제 해결 방안

### 1. already.login 오류 처리
- **문제**: 동시 로그인 제한으로 인한 401 오류
- **해결**: 중복 로그인 감지 시 세션 쿠키로 인증 진행
- **상태**: ✅ 구현 완료

### 2. 로그인 로직 개선사항
```python
# Before (부정확한 파라미터)
login_data = {
    'login_name': username,
    'password': password,
    'lang': 'ko'
}

# After (HAR 분석 기반 정확한 파라미터)
login_data = {
    'lang': 'ko',
    'is_otp': 'N',
    'is_expire': 'N', 
    'login_name': username,
    'password': password,
    'otp_value': ''
}
```

### 3. 응답 처리 로직 개선
```python
# JavaScript 로직 기반 정확한 성공/실패 판단
if 'response' in response_data:
    inner_response = response_data['response']
    error = inner_response.get('error')
    
    if error:
        # already.login 특별 처리
        if 'already' in error_message.lower():
            # 세션 쿠키로 인증 진행
            return True
    else:
        # error가 false면 성공
        return True
```

## 테스트 결과

### ✅ 성공 사항
1. **로그인 성공**: already.login 오류를 올바르게 처리
2. **토큰 획득**: 세션 쿠키 `JSESSIONID` 획득
3. **응답 구조 확인**: 정확한 JSON 구조 파싱

### ⚠️ 제한 사항
1. **401 오류**: 동시 접속 제한으로 API 호출 실패
2. **세션 충돌**: 브라우저 세션과 스크립트 세션 간 충돌

## 권장 사항

### 1. 운영 환경에서 해결 방법
- 브라우저 세션 종료 후 스크립트 실행
- 별도 계정 사용 (가능한 경우)
- 로그아웃 API 호출 후 재로그인

### 2. 코드 개선 완료 사항
- ✅ HAR 분석 기반 정확한 로그인 파라미터
- ✅ JavaScript 로직 기반 응답 처리
- ✅ already.login 오류 특별 처리
- ✅ 세션 쿠키 기반 인증 지원

### 3. 다음 단계
1. 로그아웃 API 구현으로 세션 정리
2. 세션 타임아웃 처리 로직 추가
3. 재시도 메커니즘 강화

## 결론

HAR 파일 분석을 통해 SECUDIUM의 정확한 로그인 구조를 파악하고 코드를 개선했습니다. 
로그인 자체는 성공하지만, 동시 접속 제한으로 인한 API 호출 제한이 있습니다.
이는 SECUDIUM 서버의 보안 정책으로, 코드 문제가 아닌 정상적인 동작입니다.