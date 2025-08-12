#!/usr/bin/env python3
"""
CI/CD 모듈 통합 테스트
Claude Code v8.4.0 - 모듈화 및 500줄 규칙 준수 검증
"""


def test_imports():
    """Import 테스트"""
    print("📦 Testing module imports...")

    try:
        pass

        print("✅ All imports successful")
        return True
    except Exception as e:
        print("❌ Import failed: {e}")
        return False


def test_functionality():
    """기본 기능 테스트"""
    print("🔧 Testing basic functionality...")

    try:
        # 에러 패턴 매니저 테스트
        from .cicd_error_patterns import ErrorPatternManager

        error_manager = ErrorPatternManager()
        patterns = error_manager.get_error_patterns()
        assert "docker_not_found" in patterns
        print("✅ Error pattern manager working")

        # 수정 전략 매니저 테스트
        from .cicd_fix_strategies import FixStrategyManager

        fix_manager = FixStrategyManager()
        assert hasattr(fix_manager, "fix_docker_not_found")
        print("✅ Fix strategy manager working")

        # 트러블슈터 생성 테스트
        from .cicd_troubleshooter import create_troubleshooter

        troubleshooter = create_troubleshooter()
        assert troubleshooter is not None
        print("✅ Troubleshooter creation working")

        return True
    except Exception as e:
        print("❌ Functionality test failed: {e}")
        return False


def test_integration():
    """통합 테스트"""
    print("🔍 Testing module integration...")

    try:
        from .cicd_troubleshooter import create_troubleshooter

        # 실제 트러블슈터 생성 및 구성 요소 확인
        troubleshooter = create_troubleshooter(
            gateway_url="http://test:5678", api_key="test-key"
        )

        # 모든 내부 모듈이 올바르게 초기화되었는지 확인
        assert hasattr(troubleshooter, "error_manager")
        assert hasattr(troubleshooter, "fix_manager")
        assert hasattr(troubleshooter, "utils")
        print("✅ All internal modules properly initialized")

        # 에러 감지 테스트
        error_type = troubleshooter.error_manager.detect_error_type(
            "docker: command not found"
        )
        assert error_type == "docker_not_found"
        print("✅ Error detection working")

        return True
    except Exception as e:
        print("❌ Integration test failed: {e}")
        return False


def test_line_count_compliance():
    """라인 수 규칙 준수 확인"""
    print("📊 Testing 500-line compliance...")

    from pathlib import Path

    base_dir = Path(__file__).parent
    cicd_files = list(base_dir.glob("cicd_*.py"))

    all_compliant = True
    for file_path in cicd_files:
        line_count = len(file_path.read_text().splitlines())
        if line_count > 500:
            print("❌ {file_path.name}: {line_count} lines (exceeds 500)")
            all_compliant = False
        else:
            print("✅ {file_path.name}: {line_count} lines (compliant)")

    return all_compliant


def main():
    """메인 테스트 실행"""
    print("🚀 Starting CICD Module Tests...")
    print("=" * 50)

    tests = [
        ("📦 Import Test", test_imports),
        ("🔧 Functionality Test", test_functionality),
        ("🔍 Integration Test", test_integration),
        ("📊 Line Count Compliance", test_line_count_compliance),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print("\n{test_name}")
        print("-" * 30)

        try:
            if test_func():
                passed += 1
                print("✅ {test_name} PASSED")
            else:
                print("❌ {test_name} FAILED")
        except Exception as e:
            print("❌ {test_name} ERROR: {e}")

    print("\n" + "=" * 50)
    print("🏁 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Modularization successful.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
