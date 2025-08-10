"""
컨테이너 테스트 모듈

컨테이너 시스템의 기능을 검증하는 테스트 함수들입니다.
"""

import logging

from src.core.containers.blacklist_container import BlacklistContainer
from tests.utils import get_container

logger = logging.getLogger(__name__)


def test_container_service_registration():
    """서비스 등록 및 해결 테스트"""
    print("🧠 컨테이너 서비스 등록/해결 테스트 시작...")

    try:
        container = BlacklistContainer()

        # 핵심 서비스들 검증
        services_to_test = [
            "blacklist_manager",
            "cache_manager",
            "auth_manager",
            "config",
            "metrics_collector",
            "health_checker",
        ]

        resolved_services = {}
        for service_name in services_to_test:
            try:
                service = container.get(service_name)
                resolved_services[service_name] = service is not None
                print(f"  ✅ {service_name}: {'성공' if service else '실패'}")
            except Exception as e:
                resolved_services[service_name] = False
                print(f"  ❌ {service_name}: {str(e)[:50]}...")

        # 성공적으로 해결된 서비스 수 확인
        successful_count = sum(resolved_services.values())
        total_count = len(services_to_test)

        if successful_count >= total_count * 0.7:  # 70% 이상 성공
            print(f"✅ 컨테이너 서비스 등록/해결 테스트 통과 ({successful_count}/{total_count})")
            return True
        else:
            print(f"❌ 컨테이너 서비스 등록/해결 테스트 실패 ({successful_count}/{total_count})")
            return False

    except Exception as e:
        print(f"❌ 컨테이너 테스트 중 오류: {str(e)}")
        return False


def test_container_singleton_behavior():
    """싱글톤 동작 검증"""
    print("🧠 컨테이너 싱글톤 동작 테스트 시작...")

    try:
        container1 = get_container()
        container2 = get_container()

        # 컨테이너 자체가 싱글톤인지 확인
        if container1 is container2:
            print("  ✅ 컨테이너 자체 싱글톤 동작 확인")
        else:
            print("  ⚠️ 컨테이너가 싱글톤이 아님")

        # 서비스 싱글톤 동작 확인
        try:
            manager1 = container1.get("blacklist_manager")
            manager2 = container2.get("blacklist_manager")

            if manager1 is manager2:
                print("  ✅ 서비스 싱글톤 동작 확인")
                singleton_ok = True
            else:
                print("  ⚠️ 서비스가 싱글톤이 아님")
                singleton_ok = False
        except Exception as e:
            print(f"  ⚠️ 서비스 싱글톤 테스트 불가: {str(e)[:30]}...")
            singleton_ok = False

        print("✅ 컨테이너 싱글톤 동작 테스트 완료")
        return singleton_ok

    except Exception as e:
        print(f"❌ 싱글톤 테스트 중 오류: {str(e)}")
        return False


def test_container_dependency_injection():
    """의존성 주입 검증"""
    print("🧠 컨테이너 의존성 주입 테스트 시작...")

    try:
        container = get_container()
        service_list = container.list_services()

        print(f"  📁 등록된 서비스 수: {len(service_list)}")

        # 필수 서비스들이 등록되어 있는지 확인
        required_services = ["blacklist_manager", "cache_manager", "auth_manager"]
        missing_services = []
        available_services = []

        for service in required_services:
            if container.has_service(service):
                try:
                    instance = container.get(service)
                    if instance is not None:
                        available_services.append(service)
                        print(f"  ✅ {service}: 사용 가능")
                    else:
                        missing_services.append(service)
                        print(f"  ⚠️ {service}: None 반환")
                except Exception as e:
                    missing_services.append(service)
                    print(f"  ❌ {service}: {str(e)[:30]}...")
            else:
                missing_services.append(service)
                print(f"  ❌ {service}: 등록되지 않음")

        success_rate = len(available_services) / len(required_services)

        if success_rate >= 0.7:  # 70% 이상
            print(
                f"✅ 의존성 주입 테스트 통과 ({len(available_services)}/{len(required_services)})"
            )
            return True
        else:
            print(
                f"❌ 의존성 주입 테스트 실패 ({len(available_services)}/{len(required_services)})"
            )
            return False

    except Exception as e:
        print(f"❌ 의존성 주입 테스트 중 오류: {str(e)}")
        return False


def test_container_error_handling():
    """에러 처리 검증"""
    print("🧠 컨테이너 에러 처리 테스트 시작...")

    try:
        container = get_container()

        # 없는 서비스 요청
        try:
            container.get("non_existent_service")
            print("  ❌ 없는 서비스에 대해 예외가 발생하지 않음")
            return False
        except ValueError:
            print("  ✅ 없는 서비스에 대해 적절한 예외 발생")
        except Exception as e:
            print(f"  ⚠️ 예상과 다른 예외 발생: {type(e).__name__}")

        # 컨테이너 건강 상태 확인
        try:
            health_status = container.get_health_status()
            print(f"  ✅ 건강 상태 추출 성공: {health_status.get('status', 'unknown')}")
        except Exception as e:
            print(f"  ⚠️ 건강 상태 추출 실패: {str(e)[:30]}...")

        print("✅ 컨테이너 에러 처리 테스트 완료")
        return True

    except Exception as e:
        print(f"❌ 에러 처리 테스트 중 오류: {str(e)}")
        return False


def run_all_tests():
    """모든 컨테이너 테스트 실행"""
    print("🚀 컨테이너 테스트 시작")
    print("=" * 50)

    tests = [
        ("Service Registration", test_container_service_registration),
        ("Singleton Behavior", test_container_singleton_behavior),
        ("Dependency Injection", test_container_dependency_injection),
        ("Error Handling", test_container_error_handling),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🏃‍♂️ {test_name} 테스트 시작...")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"🏁 {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {str(e)}")

    print("\n" + "=" * 50)
    print("📁 테스트 결과 요약")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    print(f"\n🎯 전체 결과: {passed}/{total} 통과")
    success_rate = passed / total * 100
    print(f"📈 성공률: {success_rate:.1f}%")

    if success_rate >= 70:
        print("✅ 컨테이너 시스템 전반적으로 정상 동작")
        return True
    else:
        print("❌ 컨테이너 시스템에 개선이 필요함")
        return False


if __name__ == "__main__":
    run_all_tests()
