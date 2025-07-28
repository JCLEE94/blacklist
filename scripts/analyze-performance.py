#!/usr/bin/env python3
"""
Performance test results analyzer
Analyzes k6 performance test results and determines if they meet thresholds
"""

import json
import sys
from typing import Dict, List, Tuple


def load_results(filename: str) -> Dict:
    """Load k6 test results from JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)


def analyze_metrics(results: Dict) -> Tuple[bool, List[str]]:
    """
    Analyze metrics against thresholds
    Returns: (passed, list of failure messages)
    """
    failures = []

    # Check HTTP request duration
    if 'http_req_duration' in results['metrics']:
        duration = results['metrics']['http_req_duration']

        # Check p95 < 500ms
        if duration['p(95)'] > 500:
            failures.append(
                f"p95 response time {duration['p(95)']}ms exceeds 500ms threshold"
            )

        # Check p99 < 1000ms
        if duration['p(99)'] > 1000:
            failures.append(
                f"p99 response time {duration['p(99)']}ms exceeds 1000ms threshold"
            )

    # Check error rate
    if 'errors' in results['metrics']:
        error_rate = results['metrics']['errors']['rate']
        if error_rate > 0.05:
            failures.append(f"Error rate {error_rate*100:.2f}% exceeds 5% threshold")

    # Check HTTP request failure rate
    if 'http_req_failed' in results['metrics']:
        fail_rate = results['metrics']['http_req_failed']['rate']
        if fail_rate > 0.05:
            failures.append(
                f"HTTP failure rate {fail_rate*100:.2f}% exceeds 5% threshold"
            )

    return len(failures) == 0, failures


def generate_report(results: Dict) -> str:
    """Generate a human-readable performance report"""
    report = []
    report.append("=== K6 Performance Test Report ===\n")

    # Test configuration
    report.append("Test Configuration:")
    report.append(f"  Total VUs: {results.get('vus_max', 'N/A')}")
    report.append(f"  Duration: {results.get('duration', 'N/A')}")
    report.append("")

    # Key metrics
    report.append("Key Metrics:")

    metrics = results.get('metrics', {})

    # Response times
    if 'http_req_duration' in metrics:
        duration = metrics['http_req_duration']
        report.append(f"  Response Times:")
        report.append(f"    Median: {duration.get('med', 0):.2f}ms")
        report.append(f"    p95: {duration.get('p(95)', 0):.2f}ms")
        report.append(f"    p99: {duration.get('p(99)', 0):.2f}ms")
        report.append(f"    Max: {duration.get('max', 0):.2f}ms")

    # Throughput
    if 'http_reqs' in metrics:
        reqs = metrics['http_reqs']
        report.append(f"  Throughput: {reqs.get('rate', 0):.2f} req/s")

    # Error rates
    if 'errors' in metrics:
        error_rate = metrics['errors']['rate'] * 100
        report.append(f"  Error Rate: {error_rate:.2f}%")

    if 'http_req_failed' in metrics:
        fail_rate = metrics['http_req_failed']['rate'] * 100
        report.append(f"  HTTP Failure Rate: {fail_rate:.2f}%")

    report.append("")

    # Check results
    passed, failures = analyze_metrics(results)

    report.append("Threshold Checks:")
    if passed:
        report.append("  ✓ All thresholds passed")
    else:
        for failure in failures:
            report.append(f"  ✗ {failure}")

    return "\n".join(report)


def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze-performance.py <results.json>")
        sys.exit(1)

    try:
        results = load_results(sys.argv[1])
        report = generate_report(results)
        print(report)

        # Generate HTML report
        with open('performance-report.html', 'w') as f:
            f.write(
                f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
    </style>
</head>
<body>
    <h1>Blacklist Performance Test Report</h1>
    <pre>{report}</pre>
</body>
</html>
            """
            )

        # Exit with appropriate code
        passed, _ = analyze_metrics(results)
        sys.exit(0 if passed else 1)

    except Exception as e:
        print(f"Error analyzing results: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
