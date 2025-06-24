import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '10s', target: 0 },     // Start with 0 users
    { duration: '5s', target: 500 },    // Spike to 500 users
    { duration: '30s', target: 500 },   // Stay at 500 users
    { duration: '5s', target: 0 },      // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests must complete below 3s during spike
    http_req_failed: ['rate<0.3'],     // Error rate must be below 30% during spike
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://registry.jclee.me:2541';

export default function() {
  // Focus on lightweight endpoints during spike
  const response = http.get(`${BASE_URL}/health`);
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 3s': (r) => r.timings.duration < 3000,
  });
}