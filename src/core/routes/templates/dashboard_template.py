#!/usr/bin/env python3
"""
Dashboard Template Provider - Modular HTML template management
Provides the main dashboard HTML template
"""

def get_dashboard_template() -> str:
    """Get the main dashboard HTML template"""
    return DASHBOARD_HTML_TEMPLATE


# Main dashboard HTML template (extracted from original file)
DASHBOARD_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>통합 제어 대시보드 - Blacklist Management</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Base Styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f23; color: #cccccc; }
        
        /* Header */
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }
        .header h1 { color: white; font-size: 2.5em; margin-bottom: 10px; }
        .header p { color: rgba(255,255,255,0.9); font-size: 1.1em; }
        
        /* Container */
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        /* Grid System */
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }
        .grid-3 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
        .grid-4 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
        
        /* Cards */
        .card { background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
        .card h3 { color: #4a90e2; margin-bottom: 15px; font-size: 1.3em; }
        
        /* Stat Cards */
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; border-radius: 12px; padding: 20px; }
        .stat-card .value { font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }
        .stat-card .label { font-size: 0.9em; opacity: 0.9; }
        
        /* Buttons */
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .btn-primary { background: #4a90e2; color: white; }
        .btn-primary:hover { background: #357abd; }
        
        /* Status badges */
        .status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
        .status.success { background: #27ae60; color: white; }
        .status.error { background: #e74c3c; color: white; }
        .status.warning { background: #f39c12; color: white; }
        
        /* Loading animation */
        .loading { text-align: center; padding: 20px; }
        .spinner { border: 3px solid rgba(255,255,255,0.3); border-radius: 50%; border-top: 3px solid #4a90e2; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Blacklist 통합 제어 센터</h1>
        <p>실시간 모니터링, 수집 제어, 데이터 분석을 한 곳에서</p>
    </div>
    
    <div class="container">
        <!-- Dashboard Overview -->
        <div class="grid grid-4">
            <div class="stat-card">
                <div class="value" id="total-threats">-</div>
                <div class="label">총 위협 IP</div>
            </div>
            <div class="stat-card">
                <div class="value" id="active-sources">-</div>
                <div class="label">활성 소스</div>
            </div>
            <div class="stat-card">
                <div class="value" id="last-updated">-</div>
                <div class="label">최근 업데이트</div>
            </div>
            <div class="stat-card">
                <div class="value" id="system-status">✅</div>
                <div class="label">시스템 상태</div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="grid grid-2">
            <div class="card">
                <h3>📅 수집 현황</h3>
                <div class="loading">
                    <div class="spinner"></div>
                    <p>데이터 로드 중...</p>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 실시간 통계</h3>
                <div id="realtime-stats">
                    <p>데이터 로드 중...</p>
                </div>
            </div>
        </div>
        
        <!-- Quick Actions -->
        <div class="card">
            <h3>🎯 빠른 작업</h3>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="btn btn-primary" onclick="loadStatus()">상태 새로고침</button>
                <button class="btn btn-primary" onclick="window.open('/api/blacklist/active', '_blank')">블랙리스트 보기</button>
                <button class="btn btn-primary" onclick="window.open('/health', '_blank')">시스템 상태</button>
            </div>
        </div>
    </div>
    
    <script>
        // Load system status
        function loadStatus() {
            fetch('/api/unified/status')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('total-threats').textContent = data.stats?.total_threats || '-';
                        document.getElementById('active-sources').textContent = data.stats?.active_sources || '-';
                        document.getElementById('last-updated').textContent = data.stats?.last_updated || '-';
                    }
                })
                .catch(error => {
                    console.error('Status load error:', error);
                    document.getElementById('system-status').innerHTML = '<span class="status error">오류</span>';
                });
        }
        
        // Auto-refresh every 30 seconds
        setInterval(loadStatus, 30000);
        
        // Load initial status
        loadStatus();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    # Validation test for template
    import sys
    
    print("🌨️ Testing Dashboard Template...")
    
    template = get_dashboard_template()
    if not template or not isinstance(template, str):
        print("❌ VALIDATION FAILED - Template is empty or invalid")
        sys.exit(1)
    
    if len(template) < 1000:
        print("❌ VALIDATION FAILED - Template appears incomplete")
        sys.exit(1)
        
    if "<!DOCTYPE html>" not in template:
        print("❌ VALIDATION FAILED - Template missing DOCTYPE")
        sys.exit(1)
        
    print(f"✅ VALIDATION PASSED - Template loaded successfully ({len(template)} characters)")
    print("Dashboard Template is ready for use")
    sys.exit(0)