================================================================================
📊 __init__ 패턴 분석 보고서
================================================================================

📈 전체 통계:
  - 전체 Python 파일: 286개
  - 패턴이 발견된 파일: 125개
  - 분석 비율: 43.7%

📋 카테고리별 패턴 빈도:
  - configuration: 520개
  - inheritance :  52개
  - service     :  18개
  - database    :  14개
  - threading   :   6개
  - timestamp   :   2개

🔍 패턴별 상세 빈도:
  - config_assignment         (configuration): 520개
  - super_init_call           (inheritance):  52개
  - logger_creation           (service   ):  15개
  - db_path_assignment        (database  ):  14개
  - thread_lock_creation      (threading ):   6개
  - service_name_assignment   (service   ):   3개
  - timestamp_creation        (timestamp ):   2개

🎯 중복도가 높은 파일들 (3개 이상 패턴):
  - common/base_classes.py                             (6개 패턴, 26회 출현)
  - core/services/unified_statistics_service_backup.py (3개 패턴, 14회 출현)
  - core/exceptions/service_exceptions.py              (3개 패턴, 13회 출현)
  - core/services/unified_statistics_service.py        (3개 패턴, 10회 출현)
  - core/exceptions/config_exceptions.py               (3개 패턴, 8회 출현)
  - utils/structured_logging.py                        (3개 패턴, 8회 출현)
  - utils/database_stability.py                        (3개 패턴, 6회 출현)
  - core/services/collection_operations.py             (3개 패턴, 5회 출현)
  - core/services/collection_status.py                 (3개 패턴, 3회 출현)
  - core/services/database_operations.py               (3개 패턴, 3회 출현)

💡 리팩토링 권장사항:
  ✅ DatabaseMixin 도입 권장 (현재 14개 중복)
  ✅ BaseService 클래스 도입 권장 (현재 18개 중복)
  ✅ 13개 파일이 중복 리팩토링 대상

================================================================================