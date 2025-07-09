import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// 커스텀 메트릭
const errorRate = new Rate('errors');

// 테스트 옵션
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95%는 500ms, 99%는 1초 이내
    errors: ['rate<0.05'],                           // 에러율 5% 미만
    http_req_failed: ['rate<0.05'],                  // 실패율 5% 미만
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8541';

// 테스트 시나리오
export default function () {
  // 1. 헬스 체크
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check success': (r) => r.status === 200,
    'health check fast': (r) => r.timings.duration < 100,
  }) || errorRate.add(1);

  sleep(1);

  // 2. 블랙리스트 조회
  const blacklistRes = http.get(`${BASE_URL}/api/blacklist/active`);
  check(blacklistRes, {
    'blacklist fetch success': (r) => r.status === 200,
    'blacklist response time OK': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);

  sleep(1);

  // 3. FortiGate 형식 조회
  const fortigateRes = http.get(`${BASE_URL}/api/fortigate`);
  check(fortigateRes, {
    'fortigate API success': (r) => r.status === 200,
    'fortigate response valid': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.version && body.ips;
      } catch (e) {
        return false;
      }
    },
  }) || errorRate.add(1);

  sleep(1);

  // 4. 통계 API
  const statsRes = http.get(`${BASE_URL}/api/stats`);
  check(statsRes, {
    'stats API success': (r) => r.status === 200,
    'stats response time OK': (r) => r.timings.duration < 300,
  }) || errorRate.add(1);

  sleep(1);

  // 5. IP 검색 (단일)
  const testIP = '192.168.1.1';
  const searchRes = http.get(`${BASE_URL}/api/search/${testIP}`);
  check(searchRes, {
    'IP search success': (r) => r.status === 200 || r.status === 404,
    'IP search fast': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);

  sleep(1);

  // 6. IP 검색 (배치)
  const batchSearchRes = http.post(
    `${BASE_URL}/api/search`,
    JSON.stringify({ ips: ['192.168.1.1', '10.0.0.1', '172.16.0.1'] }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(batchSearchRes, {
    'batch search success': (r) => r.status === 200,
    'batch search response valid': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.results && Array.isArray(body.results);
      } catch (e) {
        return false;
      }
    },
  }) || errorRate.add(1);

  sleep(2);
}