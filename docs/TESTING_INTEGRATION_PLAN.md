# Testing and Integration Plan for Blacklist Management System

## 🎯 Overview
This document outlines the comprehensive testing and integration plan for the blacklist management system deployed at blacklist.jclee.me.

## 📋 Current Status Analysis

### System Health Check
- **Site Status**: ✅ Online (200 OK)
- **Database**: ✅ Connected
- **Cache**: ✅ Available (Redis)
- **IP Count**: ⚠️ 0 IPs (No data collected yet)
- **Kubernetes**: ✅ Running (1/1 pods)

### Recent Changes
1. **Cookie-based Authentication** for REGTECH collector
2. **Disabled SECUDIUM** collector
3. **Refactored collection system**

## 🧪 Testing Plan

### 1. Unit Testing

#### A. Cookie Authentication Test
```python
# Test file: tests/test_regtech_cookie_auth.py
import pytest
from src.core.regtech_collector import RegtechCollector

def test_cookie_authentication():
    """Test REGTECH cookie-based authentication"""
    collector = RegtechCollector("data/test")
    
    # Test cookie configuration
    assert collector.cookies['_ga'] is not None
    assert collector.cookies['regtech-front'] is not None
    assert collector.cookies['regtech-va'] is not None
    assert collector.cookies['_ga_7WRDYHF66J'] is not None
    
    # Test session creation
    session = collector._create_session()
    assert session is not None
    
    # Test authentication
    result = collector._perform_login(session)
    assert result is True
```

#### B. Collection Manager Test
```python
# Test file: tests/test_collection_manager.py
import pytest
from src.core.collection_manager import CollectionManager

def test_regtech_collection_enabled():
    """Test REGTECH collection is enabled"""
    manager = CollectionManager()
    sources = manager.get_sources_status()
    
    assert 'regtech' in sources
    assert sources['regtech']['enabled'] is True

def test_secudium_collection_disabled():
    """Test SECUDIUM collection is disabled"""
    manager = CollectionManager()
    result = manager.trigger_secudium_collection()
    
    assert result['status'] == 'disabled'
    assert result['collected_count'] == 0
```

### 2. Integration Testing

#### A. End-to-End Collection Test
```bash
#!/bin/bash
# Test file: tests/integration/test_e2e_collection.sh

echo "🧪 Starting E2E Collection Test"

# 1. Check health endpoint
echo "1. Testing health endpoint..."
HEALTH_STATUS=$(curl -s https://blacklist.jclee.me/health | jq -r '.status')
if [ "$HEALTH_STATUS" != "healthy" ]; then
    echo "❌ Health check failed"
    exit 1
fi
echo "✅ Health check passed"

# 2. Test collection status
echo "2. Testing collection status..."
COLLECTION_STATUS=$(curl -s https://blacklist.jclee.me/api/collection/status | jq -r '.collection_enabled')
echo "Collection enabled: $COLLECTION_STATUS"

# 3. Trigger REGTECH collection
echo "3. Triggering REGTECH collection..."
TRIGGER_RESULT=$(curl -s -X POST https://blacklist.jclee.me/api/collection/regtech/trigger \
    -H "Content-Type: application/json" \
    -d '{"start_date": "20250101", "end_date": "20250117"}')
echo "Trigger result: $TRIGGER_RESULT"

# 4. Check collected IPs
echo "4. Checking collected IPs..."
sleep 10  # Wait for collection
IP_COUNT=$(curl -s https://blacklist.jclee.me/health | jq -r '.details.total_ips')
echo "Total IPs collected: $IP_COUNT"

# 5. Test FortiGate endpoint
echo "5. Testing FortiGate endpoint..."
FORTIGATE_DATA=$(curl -s https://blacklist.jclee.me/api/fortigate)
echo "FortiGate data available: $(echo $FORTIGATE_DATA | jq -r '.status')"
```

#### B. Cookie Validation Test
```python
# Test file: tests/integration/test_cookie_validation.py
import requests
from datetime import datetime

def test_cookie_expiration():
    """Test if cookies are still valid"""
    cookies = {
        '_ga': 'GA1.1.1689204774.1752555033',
        'regtech-front': '2F3B7CE1B26084FCD546BDB56CE9ABAC',
        'regtech-va': 'BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...',
        '_ga_7WRDYHF66J': 'GS2.1.s1752743223$o3$g1$t1752746099$j38$l0$h0'
    }
    
    # Test cookie validity
    response = requests.get(
        "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList",
        cookies=cookies,
        timeout=10
    )
    
    assert response.status_code == 200
    assert "로그인" not in response.text  # Should not see login page
```

### 3. Performance Testing

#### A. Load Test Script
```python
# Test file: tests/performance/test_load.py
import concurrent.futures
import requests
import time

def make_request(endpoint):
    """Make a single request to the endpoint"""
    start_time = time.time()
    response = requests.get(f"https://blacklist.jclee.me{endpoint}")
    end_time = time.time()
    
    return {
        'endpoint': endpoint,
        'status_code': response.status_code,
        'response_time': end_time - start_time
    }

def test_concurrent_load():
    """Test system under concurrent load"""
    endpoints = [
        '/health',
        '/api/blacklist/active',
        '/api/fortigate',
        '/api/stats',
        '/api/collection/status'
    ]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # Submit 100 requests
        futures = []
        for _ in range(20):
            for endpoint in endpoints:
                futures.append(executor.submit(make_request, endpoint))
        
        # Collect results
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    # Analyze results
    avg_response_time = sum(r['response_time'] for r in results) / len(results)
    error_count = sum(1 for r in results if r['status_code'] != 200)
    
    print(f"Average response time: {avg_response_time:.3f}s")
    print(f"Error count: {error_count}/{len(results)}")
    
    assert avg_response_time < 1.0  # Should respond within 1 second
    assert error_count == 0  # No errors allowed
```

### 4. Security Testing

#### A. Cookie Security Test
```python
# Test file: tests/security/test_cookie_security.py
def test_no_credentials_in_logs():
    """Ensure no passwords or sensitive cookies in logs"""
    log_files = [
        'logs/app.log',
        'logs/collection.log',
        'logs/error.log'
    ]
    
    sensitive_patterns = [
        'password',
        'regtech-va',
        'Bearer',
        'Sprtmxm1@3'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                for pattern in sensitive_patterns:
                    assert pattern not in content, f"Sensitive data '{pattern}' found in {log_file}"
```

## 🚀 Deployment Testing

### 1. Local Testing
```bash
# Run locally with test configuration
export COLLECTION_ENABLED=true
export REGTECH_COOKIES_ENABLED=true
python3 main.py --debug --port 8541
```

### 2. Docker Testing
```bash
# Build and test Docker image
docker build -f deployment/Dockerfile -t blacklist:test .
docker run -d --name blacklist-test \
    -p 8541:8541 \
    -e COLLECTION_ENABLED=true \
    blacklist:test

# Test endpoints
curl http://localhost:8541/health
curl http://localhost:8541/api/collection/status
```

### 3. Kubernetes Testing
```bash
# Deploy to test namespace
kubectl create namespace blacklist-test
kubectl apply -k k8s/ -n blacklist-test

# Port forward for testing
kubectl port-forward -n blacklist-test svc/blacklist 8541:80

# Run tests
pytest tests/integration/
```

## 📊 Monitoring & Validation

### 1. Health Checks
```bash
# Monitor application health
watch -n 5 'curl -s https://blacklist.jclee.me/health | jq .'
```

### 2. Collection Monitoring
```bash
# Monitor collection progress
while true; do
    echo "=== Collection Status $(date) ==="
    curl -s https://blacklist.jclee.me/api/collection/status | jq .
    echo ""
    sleep 30
done
```

### 3. Log Monitoring
```bash
# Watch application logs
kubectl logs -f deployment/blacklist -n blacklist

# Watch collection logs
kubectl logs -f deployment/blacklist -n blacklist | grep -E "(REGTECH|수집)"
```

## 🔧 Troubleshooting Guide

### Issue 1: No IPs Collected
```bash
# Check collection is enabled
curl https://blacklist.jclee.me/api/collection/status

# Enable collection if needed
curl -X POST https://blacklist.jclee.me/api/collection/enable

# Trigger manual collection
curl -X POST https://blacklist.jclee.me/api/collection/regtech/trigger
```

### Issue 2: Cookie Authentication Failed
```bash
# Check cookie validity
curl -v https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList \
    -H "Cookie: regtech-va=Bearer..."

# Update cookies in regtech_collector.py if expired
```

### Issue 3: Database Issues
```bash
# Check database inside pod
kubectl exec -it deployment/blacklist -n blacklist -- sqlite3 /app/instance/blacklist.db "SELECT COUNT(*) FROM blacklist_ip;"

# Reset database if needed
kubectl exec -it deployment/blacklist -n blacklist -- python3 init_database.py
```

## ✅ Testing Checklist

- [ ] Cookie authentication working
- [ ] REGTECH collection successful
- [ ] SECUDIUM properly disabled
- [ ] Health endpoint returning correct data
- [ ] FortiGate endpoint serving data
- [ ] Database persistence working
- [ ] Redis cache functioning
- [ ] No sensitive data in logs
- [ ] Performance within acceptable limits
- [ ] Kubernetes deployment stable

## 🎯 Success Criteria

1. **Functional**: All endpoints respond correctly
2. **Performance**: Average response time < 500ms
3. **Security**: No credentials exposed
4. **Stability**: No crashes in 24-hour test
5. **Data**: Successfully collects and stores IPs

## 📅 Testing Schedule

1. **Daily**: Automated health checks
2. **Weekly**: Full integration test suite
3. **Monthly**: Performance and security audit
4. **On Deploy**: Complete test suite execution

## 🔄 Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: pytest tests/unit/
      - name: Run Integration Tests
        run: pytest tests/integration/
      - name: Security Scan
        run: bandit -r src/
```

## 📝 Test Results Template

```markdown
## Test Execution Report - [DATE]

### Environment
- **Version**: v3.0.0
- **Environment**: Production
- **URL**: https://blacklist.jclee.me

### Test Results
| Test Suite | Passed | Failed | Skipped | Duration |
|------------|--------|--------|---------|----------|
| Unit Tests | 45 | 0 | 2 | 12s |
| Integration | 23 | 0 | 0 | 45s |
| Performance | 5 | 0 | 0 | 120s |
| Security | 8 | 0 | 0 | 8s |

### Issues Found
- None

### Recommendations
- Monitor cookie expiration dates
- Set up automated collection schedule
```

---

This testing plan ensures comprehensive validation of the blacklist management system with focus on the recent cookie-based authentication changes.