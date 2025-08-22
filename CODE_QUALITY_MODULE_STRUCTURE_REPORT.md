================================================================================
📊 모듈 구조 분석 보고서
================================================================================

📈 전체 통계:
  - 분석된 파일: 298개
  - 전체 코드 라인: 56,995줄
  - 전체 함수: 1991개
  - 전체 클래스: 256개
  - 평균 복잡도: 21.9

⚠️ 발견된 문제점:
  - Large Files: 22개
  - Complex Files: 25개
  - High Dependency Files: 34개
  - God Objects: 5개
  - Suggested Splits: 16개

📏 큰 파일들 (상위 5개):
  - /home/jclee/app/blacklist/src/api/monitoring_routes.py (491줄, 19함수,  0클래스)
  - /home/jclee/app/blacklist/src/core/settings/auth_routes.py (491줄,  7함수,  0클래스)
  - /home/jclee/app/blacklist/src/utils/structured_logging.py (486줄, 27함수,  3클래스)
  - /home/jclee/app/blacklist/src/core/security/credential_manager.py (481줄, 21함수,  2클래스)
  - /home/jclee/app/blacklist/src/core/collectors/unified_collector.py (480줄, 32함수,  5클래스)

🔄 복잡한 파일들 (상위 5개):
  - /home/jclee/app/blacklist/src/utils/performance_optimizer.py (복잡도 94, 33함수)
  - /home/jclee/app/blacklist/src/utils/decorators/auth.py (복잡도 90,  3함수)
  - /home/jclee/app/blacklist/src/utils/security/auth.py (복잡도 86, 20함수)
  - /home/jclee/app/blacklist/src/utils/security/validation.py (복잡도 86, 18함수)
  - /home/jclee/app/blacklist/src/core/security/credential_manager.py (복잡도 82, 21함수)

💡 개선 권장사항:
  📏 22개의 큰 파일이 발견되었습니다. 기능별로 분할을 고려하세요.
  🔄 25개의 복잡한 파일이 발견되었습니다. 함수 분할과 리팩토링을 고려하세요.
  🔗 34개의 파일이 과도한 의존성을 가집니다. 의존성 주입이나 인터페이스 분리를 고려하세요.
  👹 5개의 God Object 후보가 발견되었습니다. 단일 책임 원칙에 따라 클래스를 분할하세요.
  ✂️ 16개의 파일이 분할 후보입니다. 관련 기능끼리 묶어서 별도 모듈로 분리하세요.
  🏗️ 공통 기능은 base_classes.py와 common/ 모듈을 활용하세요.
  📦 비슷한 기능끼리는 하위 패키지로 그룹화하세요.
  🔄 순환 의존성이 있다면 인터페이스나 의존성 주입으로 해결하세요.
  📏 각 모듈은 500줄 이하, 복잡도 50 이하를 유지하세요.

================================================================================