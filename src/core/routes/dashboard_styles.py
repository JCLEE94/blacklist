#!/usr/bin/env python3
"""
대시보드 CSS 스타일
통합 제어 대시보드의 모든 스타일 정의
"""

DASHBOARD_CSS = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f23; color: #cccccc; }
        
        /* 헤더 */
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }
        .header h1 { color: white; font-size: 2.5em; margin-bottom: 10px; }
        .header p { color: rgba(255,255,255,0.9); font-size: 1.1em; }
        
        /* 컨테이너 */
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        /* 탭 네비게이션 */
        .tabs { display: flex; background: #1e1e1e; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }
        .tab { flex: 1; padding: 15px; text-align: center; background: #2d2d2d; cursor: pointer; transition: all 0.3s; }
        .tab:hover { background: #3d3d3d; }
        .tab.active { background: #4a90e2; color: white; }
        
        /* 카드 스타일 */
        .card { background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
        .card h3 { color: #4a90e2; margin-bottom: 15px; font-size: 1.3em; }
        
        /* 그리드 */
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }
        .grid-3 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
        .grid-4 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
        
        /* 통계 카드 */
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; border-radius: 12px; padding: 20px; }
        .stat-card .value { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .stat-card .label { font-size: 0.9em; opacity: 0.9; }
        
        /* 캘린더 */
        .calendar { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin: 20px 0; }
        .calendar-day { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; background: #2d2d2d; border-radius: 4px; font-size: 0.8em; transition: all 0.3s; position: relative; }
        .calendar-day:hover { background: #3d3d3d; }
        .calendar-day.header { background: #4a90e2; color: white; font-weight: bold; }
        .calendar-day.collected { background: #27ae60; color: white; }
        .calendar-day.failed { background: #e74c3c; color: white; }
        .calendar-day .count { position: absolute; bottom: 2px; right: 2px; font-size: 0.7em; }
        
        /* 폼 */
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #cccccc; font-weight: 500; }
        .form-control { width: 100%; padding: 10px; background: #2d2d2d; border: 1px solid #3d3d3d; border-radius: 6px; color: #cccccc; }
        .form-control:focus { outline: none; border-color: #4a90e2; box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2); }
        
        /* 버튼 */
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .btn-primary { background: #4a90e2; color: white; }
        .btn-primary:hover { background: #357abd; }
        .btn-success { background: #27ae60; color: white; }
        .btn-success:hover { background: #219a52; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-danger:hover { background: #c0392b; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-warning:hover { background: #d68910; }
        
        /* 토글 스위치 */
        .toggle { position: relative; display: inline-block; width: 50px; height: 24px; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .toggle .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #3d3d3d; transition: .4s; border-radius: 24px; }
        .toggle .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        .toggle input:checked + .slider { background-color: #4a90e2; }
        .toggle input:checked + .slider:before { transform: translateX(26px); }
        
        /* 상태 배지 */
        .status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
        .status.success { background: #27ae60; color: white; }
        .status.error { background: #e74c3c; color: white; }
        .status.warning { background: #f39c12; color: white; }
        .status.info { background: #3498db; color: white; }
        
        /* 로그 */
        .log-container { background: #0f0f0f; border: 1px solid #3d3d3d; border-radius: 6px; max-height: 300px; overflow-y: auto; padding: 10px; font-family: monospace; font-size: 0.9em; }
        .log-entry { padding: 2px 0; }
        .log-entry.error { color: #e74c3c; }
        .log-entry.success { color: #27ae60; }
        .log-entry.info { color: #3498db; }
        
        /* 숨김/표시 */
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        /* 반응형 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .tabs { flex-direction: column; }
            .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
        }
"""


if __name__ == "__main__":
    # CSS 스타일 모듈 테스트
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: CSS 문자열 존재 확인
    total_tests += 1
    try:
        if not DASHBOARD_CSS or len(DASHBOARD_CSS) < 100:
            all_validation_failures.append("CSS 문자열이 너무 짧거나 존재하지 않음")
    except Exception as e:
        all_validation_failures.append(f"CSS 확인 테스트 실패: {e}")
    
    # Test 2: 필수 CSS 클래스 존재 확인
    total_tests += 1
    try:
        required_classes = ['.header', '.container', '.tabs', '.card', '.btn', '.status']
        for css_class in required_classes:
            if css_class not in DASHBOARD_CSS:
                all_validation_failures.append(f"필수 CSS 클래스 누락: {css_class}")
    except Exception as e:
        all_validation_failures.append(f"CSS 클래스 확인 테스트 실패: {e}")
    
    # Test 3: 반응형 미디어 쿼리 존재 확인
    total_tests += 1
    try:
        if '@media' not in DASHBOARD_CSS:
            all_validation_failures.append("반응형 미디어 쿼리 누락")
    except Exception as e:
        all_validation_failures.append(f"미디어 쿼리 확인 테스트 실패: {e}")
    
    # 최종 검증 결과
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Dashboard CSS styles module is validated and ready for use")
        sys.exit(0)
