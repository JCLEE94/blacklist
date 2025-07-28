#!/usr/bin/env python3
"""
통합 테스트 실행 스크립트 - Rust 스타일 인라인 테스트
실제 데이터와 실제 API를 사용한 통합 테스트
"""

import os
import sys

sys.path.insert(0, '.')

from flask import Flask

from src.core.unified_routes import unified_bp


def test_statistics_integration():
    """통계 API 통합 테스트 - 실제 데이터 사용"""
    print("🧪 통계 API 통합 테스트 시작...")

    try:
        # Flask 테스트 앱 생성
        test_app = Flask(__name__)
        test_app.register_blueprint(unified_bp)

        with test_app.test_client() as client:
            print("  ✓ /api/stats 엔드포인트 테스트...")

            # 1. 기본 통계 API 테스트
            response = client.get('/api/stats')
            assert (
                response.status_code == 200
            ), f"Stats API failed: {response.status_code}"

            stats_data = response.get_json()
            assert 'total_ips' in stats_data, "total_ips 필드가 없습니다"
            assert 'active_ips' in stats_data, "active_ips 필드가 없습니다"
            assert 'regtech_count' in stats_data, "regtech_count 필드가 없습니다"

            total_ips = stats_data['total_ips']
            active_ips = stats_data['active_ips']
            regtech_count = stats_data['regtech_count']

            print(f"    - 총 IP 수: {total_ips}")
            print(f"    - 활성 IP 수: {active_ips}")
            print(f"    - REGTECH IP 수: {regtech_count}")

            # 2. 분석 트렌드 API 테스트
            print("  ✓ /api/v2/analytics/trends 엔드포인트 테스트...")

            response = client.get('/api/v2/analytics/trends')
            assert (
                response.status_code == 200
            ), f"Analytics API failed: {response.status_code}"

            analytics_data = response.get_json()
            assert (
                'success' in analytics_data and analytics_data['success']
            ), "분석 API 응답 실패"

            trends = analytics_data['data']
            assert 'total_ips' in trends, "trends에 total_ips 필드가 없습니다"
            assert 'active_ips' in trends, "trends에 active_ips 필드가 없습니다"
            assert 'top_countries' in trends, "trends에 top_countries 필드가 없습니다"
            assert 'daily_trends' in trends, "trends에 daily_trends 필드가 없습니다"

            # 3. 데이터 일관성 검증
            print("  ✓ 데이터 일관성 검증...")

            assert (
                trends['total_ips'] == total_ips
            ), f"총 IP 수 불일치: stats={total_ips}, trends={trends['total_ips']}"
            assert (
                trends['active_ips'] == active_ips
            ), f"활성 IP 수 불일치: stats={active_ips}, trends={trends['active_ips']}"

            # 4. 국가별 통계 검증
            top_countries = trends['top_countries']
            assert isinstance(top_countries, list), "top_countries는 리스트여야 합니다"
            assert len(top_countries) > 0, "국가별 통계가 비어있습니다"

            for country in top_countries[:3]:  # 상위 3개국만 검증
                assert 'country' in country, "국가 정보에 country 필드가 없습니다"
                assert 'count' in country, "국가 정보에 count 필드가 없습니다"
                assert isinstance(country['count'], int), "count는 정수여야 합니다"
                assert country['count'] > 0, "IP 수는 0보다 커야 합니다"

            print(
                f"    - 상위 국가: {top_countries[0]['country']} ({top_countries[0]['count']}개)"
            )

            # 5. 일별 트렌드 검증
            daily_trends = trends['daily_trends']
            assert isinstance(daily_trends, list), "daily_trends는 리스트여야 합니다"

            if len(daily_trends) > 0:
                for trend in daily_trends[:2]:  # 최근 2일만 검증
                    assert 'date' in trend, "트렌드에 date 필드가 없습니다"
                    assert 'new_ips' in trend, "트렌드에 new_ips 필드가 없습니다"
                    assert isinstance(
                        trend['new_ips'], int
                    ), "new_ips는 정수여야 합니다"

                print(
                    f"    - 최근 트렌드: {daily_trends[0]['date']} ({daily_trends[0]['new_ips']}개)"
                )

            print("  ✓ 모든 통계 데이터가 일관성 있게 반환됨")

    except Exception as e:
        print(f"❌ 통계 통합 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✅ 통계 API 통합 테스트 성공!")
    return True


def test_database_api_consistency():
    """데이터베이스와 API 응답 일관성 테스트"""
    print("🧪 데이터베이스-API 일관성 테스트 시작...")

    try:
        import os
        import sqlite3

        # 1. 데이터베이스에서 직접 데이터 조회
        db_path = '/home/jclee/app/blacklist/instance/blacklist.db'
        if not os.path.exists(db_path):
            db_path = 'instance/blacklist.db'

        assert os.path.exists(
            db_path
        ), f"데이터베이스 파일을 찾을 수 없습니다: {db_path}"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 데이터베이스에서 통계 조회
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip WHERE is_active = 1')
        db_active_count = cursor.fetchone()[0]

        cursor.execute(
            'SELECT source, COUNT(*) FROM blacklist_ip WHERE is_active = 1 GROUP BY source'
        )
        db_sources = dict(cursor.fetchall())

        cursor.execute(
            '''
            SELECT country, COUNT(*) as count 
            FROM blacklist_ip 
            WHERE country IS NOT NULL AND country != '' AND is_active = 1
            GROUP BY country 
            ORDER BY count DESC 
            LIMIT 5
        '''
        )
        db_countries = cursor.fetchall()

        conn.close()

        print(f"  ✓ DB 활성 IP 수: {db_active_count}")
        print(f"  ✓ DB 소스별 카운트: {db_sources}")
        print(f"  ✓ DB 상위 국가: {db_countries[0] if db_countries else 'None'}")

        # 2. API 응답과 비교
        test_app = Flask(__name__)
        test_app.register_blueprint(unified_bp)

        with test_app.test_client() as client:
            # Stats API 검증
            response = client.get('/api/stats')
            assert response.status_code == 200
            stats_data = response.get_json()

            api_active_count = stats_data['active_ips']
            api_regtech_count = stats_data['regtech_count']

            print(f"  ✓ API 활성 IP 수: {api_active_count}")
            print(f"  ✓ API REGTECH 카운트: {api_regtech_count}")

            # Analytics API 검증
            response = client.get('/api/v2/analytics/trends')
            assert response.status_code == 200
            analytics_data = response.get_json()
            trends = analytics_data['data']

            # 3. 일관성 검증
            assert (
                db_active_count == api_active_count
            ), f"활성 IP 수 불일치: DB={db_active_count}, API={api_active_count}"
            assert (
                db_sources.get('REGTECH', 0) == api_regtech_count
            ), f"REGTECH 카운트 불일치: DB={db_sources.get('REGTECH', 0)}, API={api_regtech_count}"
            assert (
                trends['active_ips'] == api_active_count
            ), f"트렌드 활성 IP 불일치: Trends={trends['active_ips']}, API={api_active_count}"

            # 국가별 데이터 검증
            if db_countries and trends['top_countries']:
                db_top_country = db_countries[0]
                api_top_country = trends['top_countries'][0]

                assert (
                    db_top_country[0] == api_top_country['country']
                ), f"상위 국가 불일치: DB={db_top_country[0]}, API={api_top_country['country']}"
                assert (
                    db_top_country[1] == api_top_country['count']
                ), f"상위 국가 카운트 불일치: DB={db_top_country[1]}, API={api_top_country['count']}"

            print("  ✓ 모든 데이터가 데이터베이스와 일치함")

    except Exception as e:
        print(f"❌ 데이터베이스-API 일관성 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✅ 데이터베이스-API 일관성 테스트 성공!")
    return True


def test_collection_data_flow():
    """수집 → 저장 → API 응답 전체 플로우 테스트"""
    print("🧪 수집 데이터 플로우 통합 테스트 시작...")

    try:
        test_app = Flask(__name__)
        test_app.register_blueprint(unified_bp)

        with test_app.test_client() as client:
            # 1. 수집 상태 확인
            print("  ✓ 수집 상태 확인...")
            response = client.get('/api/collection/status')
            assert response.status_code == 200

            status_data = response.get_json()
            # API는 'enabled' 필드를 사용함
            enabled = status_data.get(
                'enabled', status_data.get('collection_enabled', False)
            )
            assert (
                enabled is not None
            ), f"수집 상태 필드를 찾을 수 없습니다: {status_data.keys()}"
            print(f"    - 수집 상태: {'활성화' if enabled else '비활성화'}")

            # 2. 수집 전 통계 저장
            response = client.get('/api/stats')
            before_stats = response.get_json()
            before_count = before_stats['total_ips']

            print(f"  ✓ 수집 전 IP 수: {before_count}")

            # 3. 활성 IP 목록 API 테스트
            print("  ✓ 활성 IP 목록 API 테스트...")
            response = client.get('/api/blacklist/active')
            assert response.status_code == 200

            # 응답이 JSON인지 텍스트인지 확인
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                active_data = response.get_json()
                if isinstance(active_data, dict) and 'ips' in active_data:
                    active_count = len(active_data['ips'])
                elif isinstance(active_data, dict) and 'count' in active_data:
                    active_count = active_data['count']
                else:
                    active_count = (
                        len(active_data) if isinstance(active_data, list) else 0
                    )
            else:
                # 텍스트 형식인 경우
                text_data = response.get_data(as_text=True)
                active_count = len(
                    [line for line in text_data.split('\n') if line.strip()]
                )

            print(f"  ✓ 활성 IP 목록 크기: {active_count}")

            # 4. FortiGate 형식 API 테스트
            print("  ✓ FortiGate API 형식 테스트...")
            response = client.get('/api/fortigate')
            assert response.status_code == 200

            fortigate_data = response.get_json()
            assert isinstance(fortigate_data, dict)
            # FortiGate API는 'threat_feed' 필드를 사용
            assert (
                'threat_feed' in fortigate_data
                or 'entries' in fortigate_data
                or 'blacklist' in fortigate_data
            ), f"FortiGate 응답 구조가 예상과 다릅니다: {fortigate_data.keys()}"

            # 5. 데이터 일관성 검증
            print("  ✓ 전체 플로우 데이터 일관성 검증...")

            # 통계와 활성 IP 수가 일치하는지 확인
            assert (
                active_count == before_count
            ), f"통계와 활성 IP 수 불일치: 통계={before_count}, 활성목록={active_count}"

            print(f"  ✓ 모든 API가 일관된 데이터 반환: {before_count}개 IP")

    except Exception as e:
        print(f"❌ 수집 데이터 플로우 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✅ 수집 데이터 플로우 통합 테스트 성공!")
    return True


def test_api_performance():
    """API 성능 테스트"""
    print("🧪 API 성능 테스트 시작...")

    try:
        import time

        test_app = Flask(__name__)
        test_app.register_blueprint(unified_bp)

        endpoints = [
            '/api/stats',
            '/api/v2/analytics/trends',
            '/api/blacklist/active',
            '/api/fortigate',
        ]

        with test_app.test_client() as client:
            for endpoint in endpoints:
                print(f"  ✓ {endpoint} 성능 테스트...")

                # 5번 실행해서 평균 시간 측정
                times = []
                for i in range(5):
                    start = time.time()
                    response = client.get(endpoint)
                    end = time.time()

                    assert response.status_code == 200, f"{endpoint} 응답 실패"
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)

                print(f"    - 평균 응답시간: {avg_time*1000:.2f}ms")
                print(f"    - 최대 응답시간: {max_time*1000:.2f}ms")
                print(f"    - 최소 응답시간: {min_time*1000:.2f}ms")

                # 성능 기준: 평균 500ms 이하
                assert (
                    avg_time < 0.5
                ), f"{endpoint} 평균 응답시간이 너무 깁니다: {avg_time*1000:.2f}ms"

    except Exception as e:
        print(f"❌ API 성능 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✅ API 성능 테스트 성공!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 블랙리스트 시스템 통합 테스트 시작")
    print("📋 실제 데이터를 사용한 Rust 스타일 인라인 테스트")
    print("=" * 60)

    tests_passed = True

    # 각 테스트 실행
    tests_passed &= test_statistics_integration()
    print()
    tests_passed &= test_database_api_consistency()
    print()
    tests_passed &= test_collection_data_flow()
    print()
    tests_passed &= test_api_performance()

    print("\n" + "=" * 60)
    if tests_passed:
        print("🎉 모든 통합 테스트 성공!")
        print("✅ 시스템이 정상적으로 작동하고 있습니다.")
        sys.exit(0)
    else:
        print("❌ 일부 테스트가 실패했습니다!")
        print("🔧 시스템 점검이 필요합니다.")
        sys.exit(1)
