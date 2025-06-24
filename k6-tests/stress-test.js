import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },    // Ramp up to 100 users
    { duration: '5m', target: 100 },    // Stay at 100 users
    { duration: '2m', target: 200 },    // Ramp up to 200 users
    { duration: '5m', target: 200 },    // Stay at 200 users
    { duration: '2m', target: 300 },    // Ramp up to 300 users
    { duration: '5m', target: 300 },    // Stay at 300 users
    { duration: '10m', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(90)<2000'], // 90% of requests must complete below 2s
    http_req_failed: ['rate<0.2'],     // Error rate must be below 20%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://registry.jclee.me:2541';

export default function() {
  // Simulate real user behavior with think time
  const endpoints = [
    { url: '/health', weight: 0.1 },
    { url: '/api/stats', weight: 0.3 },
    { url: '/api/blacklist/active', weight: 0.3 },
    { url: '/api/fortigate', weight: 0.2 },
    { url: '/api/collection/status', weight: 0.1 },
  ];
  
  // Select endpoint based on weight
  const random = Math.random();
  let cumulative = 0;
  let selectedEndpoint;
  
  for (const endpoint of endpoints) {
    cumulative += endpoint.weight;
    if (random < cumulative) {
      selectedEndpoint = endpoint;
      break;
    }
  }
  
  const response = http.get(`${BASE_URL}${selectedEndpoint.url}`);
  
  check(response, {
    'status is not 5xx': (r) => r.status < 500,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });
  
  // Think time between requests
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}