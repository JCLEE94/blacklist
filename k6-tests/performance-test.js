import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export let options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp up to 20 users
    { duration: '2m', target: 50 },    // Stay at 50 users
    { duration: '1m', target: 100 },   // Spike to 100 users
    { duration: '2m', target: 50 },    // Back to normal
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% under 500ms, 99% under 1s
    http_req_failed: ['rate<0.1'],                   // Error rate under 10%
    errors: ['rate<0.05'],                           // Custom error rate under 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://registry.jclee.me:2541';

export default function() {
  // Test different endpoints with weights
  const scenario = Math.random();
  
  if (scenario < 0.4) {
    // 40% - Health check
    testHealthEndpoint();
  } else if (scenario < 0.7) {
    // 30% - Stats endpoint
    testStatsEndpoint();
  } else if (scenario < 0.85) {
    // 15% - Collection status
    testCollectionStatus();
  } else if (scenario < 0.95) {
    // 10% - Blacklist data
    testBlacklistEndpoint();
  } else {
    // 5% - FortiGate endpoint
    testFortiGateEndpoint();
  }
  
  sleep(1);
}

function testHealthEndpoint() {
  const response = http.get(`${BASE_URL}/health`);
  
  const success = check(response, {
    'health status is 200': (r) => r.status === 200,
    'health response time < 100ms': (r) => r.timings.duration < 100,
    'health returns JSON': (r) => r.headers['Content-Type'] && r.headers['Content-Type'].includes('application/json'),
  });
  
  errorRate.add(!success);
}

function testStatsEndpoint() {
  const response = http.get(`${BASE_URL}/api/stats`);
  
  const success = check(response, {
    'stats status is 200': (r) => r.status === 200,
    'stats response time < 300ms': (r) => r.timings.duration < 300,
    'stats has total_ips': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.hasOwnProperty('total_ips');
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(!success);
}

function testCollectionStatus() {
  const response = http.get(`${BASE_URL}/api/collection/status`);
  
  const success = check(response, {
    'collection status is 200': (r) => r.status === 200,
    'collection response time < 200ms': (r) => r.timings.duration < 200,
    'collection returns valid data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.hasOwnProperty('enabled') && body.hasOwnProperty('sources');
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(!success);
}

function testBlacklistEndpoint() {
  const response = http.get(`${BASE_URL}/api/blacklist/active`);
  
  const success = check(response, {
    'blacklist status is 200': (r) => r.status === 200,
    'blacklist response time < 500ms': (r) => r.timings.duration < 500,
    'blacklist returns text': (r) => r.headers['Content-Type'] && r.headers['Content-Type'].includes('text/plain'),
  });
  
  errorRate.add(!success);
}

function testFortiGateEndpoint() {
  const response = http.get(`${BASE_URL}/api/fortigate`);
  
  const success = check(response, {
    'fortigate status is 200': (r) => r.status === 200,
    'fortigate response time < 400ms': (r) => r.timings.duration < 400,
    'fortigate returns JSON array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body);
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(!success);
}

// Lifecycle hooks
export function setup() {
  console.log('🚀 Starting performance test...');
  console.log(`📍 Target: ${BASE_URL}`);
  
  // Warm up with a single request
  const warmup = http.get(`${BASE_URL}/health`);
  if (warmup.status !== 200) {
    throw new Error(`Warmup failed: ${warmup.status}`);
  }
}

export function teardown(data) {
  console.log('✅ Performance test completed');
}