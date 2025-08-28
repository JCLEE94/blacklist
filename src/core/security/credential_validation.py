#!/usr/bin/env python3
"""
자격증명 유효성 검증 시스템

서비스별 자격증명 유효성 검증 및 만료 발알 기능을 제공합니다.
REGTECH, SECUDIUM 등 서비스별 특화된 검증 로직을 지원합니다.

관련 패키지 문서:
- re: https://docs.python.org/3/library/re.html
- datetime: https://docs.python.org/3/library/datetime.html

입력 예시:
- service: "regtech" 또는 "secudium"
- credential: CredentialInfo 객체

출력 예시:
- 검증 결과 딕셔너리 (valid, error, warning 포함)
- 상태 보고서 데이터
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List

# 조건부 임포트로 독립 실행 지원
try:
    from .credential_info import CredentialInfo
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from credential_info import CredentialInfo

logger = logging.getLogger(__name__)


class CredentialValidator:
    """자격증명 유효성 검증자 클래스"""

    def __init__(self):
        """검증자 초기화"""
        self.validation_rules = {
            "regtech": self._validate_regtech_credential,
            "secudium": self._validate_secudium_credential,
            "api": self._validate_api_credential,
        }

    def validate_credential(
        self, service: str, credential: CredentialInfo
    ) -> Dict[str, Any]:
        """자격증명 유효성 검증"""
        if not credential:
            return {"valid": False, "error": "자격증명이 없습니다."}

        validation_result = {
            "valid": True,
            "service": service,
            "username": credential.username,
            "is_expired": credential.is_expired(),
            "expires_soon": credential.expires_soon(),
            "last_used": credential.last_used,
            "created_at": credential.created_at,
            "warnings": [],
        }

        # 기본 검증
        if not credential.username or not credential.password:
            validation_result["valid"] = False
            validation_result["error"] = "사용자명 또는 패스워드가 비어있습니다."
            return validation_result

        # 만료 검증
        if credential.is_expired():
            validation_result["valid"] = False
            validation_result["error"] = "자격증명이 만료되었습니다."
            return validation_result

        # 곱 만료 경고
        if credential.expires_soon():
            validation_result["warnings"].append("자격증명이 곱 만료됩니다.")

        # 서비스별 추가 검증
        if service in self.validation_rules:
            service_validation = self.validation_rules[service](credential)
            validation_result.update(service_validation)

        return validation_result

    def _validate_regtech_credential(
        self, credential: CredentialInfo
    ) -> Dict[str, Any]:
        """REGTECH 자격증명 유효성 검증"""
        validation = {"warnings": []}

        # 사용자명 형식 검증 (이메일 또는 아이디)
        if "@" in credential.username:
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, credential.username):
                validation["warnings"].append("REGTECH 이메일 형식이 올바르지 않을 수 있습니다.")
        else:
            # 사용자 ID 형식 검증
            if len(credential.username) < 3:
                validation["warnings"].append("REGTECH 사용자 ID가 너무 짧습니다.")

        # 패스워드 복잡성 검증
        password = credential.password
        if len(password) < 8:
            validation["warnings"].append("REGTECH 패스워드가 너무 짧을 수 있습니다.")

        # 특수 문자 포함 검증
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            validation["warnings"].append("REGTECH 패스워드에 특수문자가 없습니다.")

        return validation

    def _validate_secudium_credential(
        self, credential: CredentialInfo
    ) -> Dict[str, Any]:
        """SECUDIUM 자격증명 유효성 검증"""
        validation = {"warnings": []}

        # 사용자명 형식 검증
        username = credential.username
        if len(username) < 4:
            validation["warnings"].append("SECUDIUM 사용자명이 너무 짧습니다.")

        # 한글 포함 검증
        if re.search(r"[\u3131-\u3163\uac00-\ud7a3]", username):
            validation["warnings"].append("SECUDIUM 사용자명에 한글이 포함되어 있습니다.")

        # 패스워드 복잡성 검증
        password = credential.password
        if len(password) < 8:
            validation["warnings"].append("SECUDIUM 패스워드가 너무 짧을 수 있습니다.")

        # 대소문자 복합 검증
        if not (re.search(r"[a-z]", password) and re.search(r"[A-Z]", password)):
            validation["warnings"].append("SECUDIUM 패스워드에 대소문자가 복합되어 있지 않습니다.")

        # 숫자 포함 검증
        if not re.search(r"\d", password):
            validation["warnings"].append("SECUDIUM 패스워드에 숫자가 포함되어 있지 않습니다.")

        return validation

    def _validate_api_credential(self, credential: CredentialInfo) -> Dict[str, Any]:
        """API 자격증명 유효성 검증"""
        validation = {"warnings": []}

        # API 키 형식 검증 (패스워드가 API 키인 경우)
        password = credential.password
        if password.startswith("blk_"):
            # Blacklist API 키 형식
            if len(password) < 20:
                validation["warnings"].append("API 키가 너무 짧습니다.")
        elif len(password) < 16:
            validation["warnings"].append("API 패스워드가 너무 짧습니다.")

        return validation

    def generate_status_report(
        self, credentials: Dict[str, CredentialInfo]
    ) -> Dict[str, Any]:
        """자격증명 상태 보고서 생성"""
        report = {
            "total_credentials": len(credentials),
            "services": [],
            "expired_count": 0,
            "expiring_soon_count": 0,
            "warnings": [],
            "validation_summary": {
                "valid": 0,
                "invalid": 0,
                "with_warnings": 0,
            },
        }

        for service, credential in credentials.items():
            validation_result = self.validate_credential(service, credential)

            service_info = {
                "service": service,
                "username": credential.username,
                "is_expired": credential.is_expired(),
                "expires_soon": credential.expires_soon(),
                "last_used": (
                    credential.last_used.isoformat() if credential.last_used else None
                ),
                "source": credential.additional_data.get("source", "file"),
                "validation": validation_result,
            }

            # 통계 업데이트
            if credential.is_expired():
                report["expired_count"] += 1
                report["warnings"].append(f"{service} 자격증명이 만료되었습니다.")
            elif credential.expires_soon():
                report["expiring_soon_count"] += 1
                report["warnings"].append(f"{service} 자격증명이 곱 만료됩니다.")

            if validation_result["valid"]:
                report["validation_summary"]["valid"] += 1
            else:
                report["validation_summary"]["invalid"] += 1

            if validation_result.get("warnings"):
                report["validation_summary"]["with_warnings"] += 1

            report["services"].append(service_info)

        return report

    def check_credential_strength(self, credential: CredentialInfo) -> Dict[str, Any]:
        """자격증명 강도 검사"""
        password = credential.password
        strength_score = 0
        feedback = []

        # 길이 검사
        if len(password) >= 12:
            strength_score += 25
        elif len(password) >= 8:
            strength_score += 15
        else:
            feedback.append("패스워드가 너무 짧습니다.")

        # 대소문자 검사
        if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
            strength_score += 20
        else:
            feedback.append("대소문자를 복합하여 사용하세요.")

        # 숫자 검사
        if re.search(r"\d", password):
            strength_score += 20
        else:
            feedback.append("숫자를 포함하세요.")

        # 특수문자 검사
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            strength_score += 20
        else:
            feedback.append("특수문자를 포함하세요.")

        # 연속되는 문자 검사
        if not re.search(r"(.)\1{2,}", password):
            strength_score += 15
        else:
            feedback.append("동일한 문자를 3번 이상 연속 사용하지 마세요.")

        # 강도 레벨 결정
        if strength_score >= 80:
            level = "강함"
        elif strength_score >= 60:
            level = "보통"
        elif strength_score >= 40:
            level = "약함"
        else:
            level = "매우 약함"

        return {
            "score": strength_score,
            "level": level,
            "feedback": feedback,
            "max_score": 100,
        }

    def suggest_improvements(
        self, service: str, credential: CredentialInfo
    ) -> List[str]:
        """자격증명 개선 제안"""
        suggestions = []
        validation_result = self.validate_credential(service, credential)

        # 검증 오류 개선
        if not validation_result["valid"]:
            suggestions.append(f"오류 해결: {validation_result.get('error', '')}")

        # 경고 개선
        for warning in validation_result.get("warnings", []):
            suggestions.append(f"경고 해결: {warning}")

        # 강도 개선
        strength = self.check_credential_strength(credential)
        if strength["score"] < 60:
            suggestions.extend([f"강도 개선: {fb}" for fb in strength["feedback"]])

        # 만료 가능성 개선
        if credential.expires_soon():
            suggestions.append("자격증명 갱신을 고려하세요.")

        return suggestions


if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta

    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0

    validator = CredentialValidator()

    # 테스트 1: REGTECH 자격증명 검증
    total_tests += 1
    try:
        regtech_cred = CredentialInfo(
            service="regtech",
            username="test@example.com",
            password=os.getenv("TEST_PASSWORD", "Test123!@#"),
        )
        result = validator.validate_credential("regtech", regtech_cred)

        if not result["valid"]:
            all_validation_failures.append(
                f"REGTECH 검증: 예상 valid=True, 실제 valid={result['valid']}"
            )
    except Exception as e:
        all_validation_failures.append(f"REGTECH 검증 오류: {e}")

    # 테스트 2: SECUDIUM 자격증명 검증
    total_tests += 1
    try:
        secudium_cred = CredentialInfo(
            service="secudium",
            username="testuser",
            password=os.getenv("TEST_SECUDIUM_PASSWORD", "SecurePass1"),
        )
        result = validator.validate_credential("secudium", secudium_cred)

        if not result["valid"]:
            all_validation_failures.append(
                f"SECUDIUM 검증: 예상 valid=True, 실제 valid={result['valid']}"
            )
    except Exception as e:
        all_validation_failures.append(f"SECUDIUM 검증 오류: {e}")

    # 테스트 3: 만료된 자격증명 검증
    total_tests += 1
    try:
        expired_cred = CredentialInfo(
            service="test",
            username="expired_user",
            password="password",
            expires_at=datetime.now() - timedelta(days=1),
        )
        result = validator.validate_credential("test", expired_cred)

        if result["valid"]:
            all_validation_failures.append("만료 검증: 만료된 자격증명이 valid=True로 판정됨")
    except Exception as e:
        all_validation_failures.append(f"만료 검증 오류: {e}")

    # 테스트 4: 상태 보고서 생성
    total_tests += 1
    try:
        credentials = {"regtech": regtech_cred, "secudium": secudium_cred}
        report = validator.generate_status_report(credentials)

        if report["total_credentials"] != 2:
            all_validation_failures.append(
                f"상태 보고서: 예상 total=2, 실제 total={report['total_credentials']}"
            )
    except Exception as e:
        all_validation_failures.append(f"상태 보고서 오류: {e}")

    # 테스트 5: 자격증명 강도 검사
    total_tests += 1
    try:
        strength = validator.check_credential_strength(regtech_cred)

        if "score" not in strength or "level" not in strength:
            all_validation_failures.append("강도 검사: score 또는 level 필드 누락")
    except Exception as e:
        all_validation_failures.append(f"강도 검사 오류: {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("CredentialValidator module is validated and ready for use")
        sys.exit(0)
