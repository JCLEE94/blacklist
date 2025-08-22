#!/usr/bin/env python3
"""
Deployment Verification Script for Blacklist Management System
Verifies deployment status using blacklist.jclee.me version endpoint
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DeploymentVerifier:
    """Comprehensive deployment verification for blacklist.jclee.me"""
    
    def __init__(self, target_url: str = "https://blacklist.jclee.me", timeout: int = 300):
        self.target_url = target_url.rstrip('/')
        self.timeout = timeout
        self.session = self._create_session()
        self.start_time = datetime.now()
        self.expected_version = self._get_expected_version()
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_expected_version(self) -> str:
        """Get expected version from version.txt"""
        try:
            version_file = Path("version.txt")
            if version_file.exists():
                return version_file.read_text().strip()
            return "unknown"
        except Exception as e:
            print(f"⚠️ Warning: Could not read version.txt: {e}")
            return "unknown"
    
    def check_endpoint(self, endpoint: str, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Check specific endpoint with detailed response analysis"""
        url = f"{self.target_url}{endpoint}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            result = {
                "url": url,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": response.status_code == expected_status,
                "headers": dict(response.headers),
                "timestamp": datetime.now().isoformat()
            }
            
            # Parse JSON response if possible
            try:
                result["data"] = response.json()
            except:
                result["data"] = response.text[:500] if response.text else ""
            
            return result["success"], result
            
        except Exception as e:
            return False, {
                "url": url,
                "status_code": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def verify_version_deployment(self) -> Tuple[bool, Dict]:
        """Verify that the expected version is deployed"""
        print(f"🔍 Verifying deployment version: {self.expected_version}")
        
        # Check multiple endpoints for version information
        version_endpoints = [
            "/health",
            "/api/health", 
            "/",
            "/api",
            "/api/v2/health"
        ]
        
        version_found = False
        deployment_info = {
            "expected_version": self.expected_version,
            "endpoints_checked": [],
            "version_matches": [],
            "deployment_status": "unknown"
        }
        
        for endpoint in version_endpoints:
            success, result = self.check_endpoint(endpoint)
            deployment_info["endpoints_checked"].append(result)
            
            if success and "data" in result and isinstance(result["data"], dict):
                # Look for version in response data
                response_data = result["data"]
                found_version = None
                
                # Check various possible version keys
                version_keys = ["version", "app_version", "api_version", "service_version"]
                for key in version_keys:
                    if key in response_data:
                        found_version = response_data[key]
                        break
                
                if found_version:
                    version_match = {
                        "endpoint": endpoint,
                        "found_version": found_version,
                        "expected_version": self.expected_version,
                        "matches": str(found_version) == str(self.expected_version)
                    }
                    deployment_info["version_matches"].append(version_match)
                    
                    if version_match["matches"]:
                        version_found = True
                        print(f"✅ Version match found at {endpoint}: {found_version}")
                    else:
                        print(f"⚠️ Version mismatch at {endpoint}: found {found_version}, expected {self.expected_version}")
        
        deployment_info["deployment_status"] = "success" if version_found else "version_mismatch"
        return version_found, deployment_info
    
    def run_comprehensive_health_check(self) -> Tuple[bool, Dict]:
        """Run comprehensive health checks"""
        print("🏥 Running comprehensive health checks...")
        
        health_results = {
            "overall_health": True,
            "checks": {},
            "summary": {}
        }
        
        # Essential endpoints to check
        critical_endpoints = {
            "/health": 200,
            "/api/health": 200,
            "/api/blacklist/active": 200,
            "/api/collection/status": [200, 503]  # Allow degraded state
        }
        
        # Optional endpoints (non-critical)
        optional_endpoints = {
            "/api/fortigate": 200,
            "/api/v2/health": 200,
            "/dashboard": 200,
            "/": 200
        }
        
        # Check critical endpoints
        critical_failures = 0
        for endpoint, expected in critical_endpoints.items():
            expected_codes = expected if isinstance(expected, list) else [expected]
            success, result = self.check_endpoint(endpoint)
            
            # Check if status code is in expected codes
            actual_success = result.get("status_code") in expected_codes
            health_results["checks"][endpoint] = {
                **result,
                "critical": True,
                "success": actual_success
            }
            
            if not actual_success:
                critical_failures += 1
                health_results["overall_health"] = False
                print(f"❌ Critical endpoint failed: {endpoint} (status: {result.get('status_code')})")
            else:
                print(f"✅ Critical endpoint OK: {endpoint}")
        
        # Check optional endpoints
        optional_failures = 0
        for endpoint, expected in optional_endpoints.items():
            success, result = self.check_endpoint(endpoint, expected)
            health_results["checks"][endpoint] = {
                **result,
                "critical": False
            }
            
            if not success:
                optional_failures += 1
                print(f"⚠️ Optional endpoint degraded: {endpoint}")
            else:
                print(f"✅ Optional endpoint OK: {endpoint}")
        
        # Generate summary
        health_results["summary"] = {
            "critical_endpoints": len(critical_endpoints),
            "critical_failures": critical_failures,
            "optional_endpoints": len(optional_endpoints),
            "optional_failures": optional_failures,
            "overall_status": "healthy" if health_results["overall_health"] else "unhealthy",
            "health_score": round(((len(critical_endpoints) - critical_failures) / len(critical_endpoints)) * 100, 1)
        }
        
        return health_results["overall_health"], health_results
    
    def wait_for_deployment(self, max_wait: int = None) -> Tuple[bool, Dict]:
        """Wait for deployment to complete with version verification"""
        max_wait = max_wait or self.timeout
        print(f"⏳ Waiting for deployment (max {max_wait}s)...")
        
        wait_results = {
            "wait_started": self.start_time.isoformat(),
            "expected_version": self.expected_version,
            "attempts": [],
            "final_status": "timeout"
        }
        
        attempt = 0
        while (datetime.now() - self.start_time).total_seconds() < max_wait:
            attempt += 1
            attempt_start = datetime.now()
            
            print(f"🔄 Attempt {attempt}: Checking deployment status...")
            
            # Check if basic health endpoint is responding
            health_success, health_result = self.check_endpoint("/health")
            
            attempt_result = {
                "attempt": attempt,
                "timestamp": attempt_start.isoformat(),
                "health_check": health_result,
                "elapsed_time": (datetime.now() - self.start_time).total_seconds()
            }
            
            if health_success:
                # If health check passes, verify version
                version_success, version_info = self.verify_version_deployment()
                attempt_result["version_check"] = version_info
                
                if version_success:
                    wait_results["final_status"] = "success"
                    wait_results["attempts"].append(attempt_result)
                    print(f"🎉 Deployment successful after {attempt} attempts!")
                    return True, wait_results
                else:
                    print(f"⚠️ Service is up but version not yet updated (attempt {attempt})")
            else:
                print(f"❌ Service not responding (attempt {attempt})")
            
            wait_results["attempts"].append(attempt_result)
            
            if (datetime.now() - self.start_time).total_seconds() < max_wait - 30:
                print("   Waiting 30s before next attempt...")
                time.sleep(30)
            else:
                break
        
        wait_results["final_status"] = "timeout"
        print(f"⏰ Deployment verification timed out after {max_wait}s")
        return False, wait_results
    
    def generate_report(self, results: Dict) -> str:
        """Generate comprehensive deployment report"""
        report = f"""
# Deployment Verification Report

## 📊 Summary
- **Target URL**: {self.target_url}
- **Expected Version**: {self.expected_version}
- **Verification Time**: {datetime.now().isoformat()}
- **Duration**: {(datetime.now() - self.start_time).total_seconds():.1f}s

## 🎯 Results
"""
        
        if "version_check" in results:
            version_info = results["version_check"]
            report += f"""
### Version Verification
- **Status**: {'✅ SUCCESS' if version_info.get('deployment_status') == 'success' else '❌ FAILED'}
- **Expected**: {version_info.get('expected_version', 'unknown')}
- **Matches Found**: {len(version_info.get('version_matches', []))}
"""
        
        if "health_check" in results:
            health_info = results["health_check"]
            summary = health_info.get("summary", {})
            report += f"""
### Health Check
- **Overall Status**: {'✅ HEALTHY' if health_info.get('overall_health') else '❌ UNHEALTHY'}
- **Health Score**: {summary.get('health_score', 0)}%
- **Critical Endpoints**: {summary.get('critical_endpoints', 0) - summary.get('critical_failures', 0)}/{summary.get('critical_endpoints', 0)} OK
- **Optional Endpoints**: {summary.get('optional_endpoints', 0) - summary.get('optional_failures', 0)}/{summary.get('optional_endpoints', 0)} OK
"""
        
        if "wait_results" in results:
            wait_info = results["wait_results"]
            report += f"""
### Deployment Wait
- **Final Status**: {wait_info.get('final_status', 'unknown').upper()}
- **Attempts**: {len(wait_info.get('attempts', []))}
- **Duration**: {(datetime.now() - self.start_time).total_seconds():.1f}s
"""
        
        report += f"""
## 🔗 Validation URLs
- Health Check: {self.target_url}/health
- API Health: {self.target_url}/api/health
- Blacklist API: {self.target_url}/api/blacklist/active
- Dashboard: {self.target_url}/dashboard

## 📋 Next Steps
1. Monitor system for 24 hours
2. Check error logs if any issues
3. Validate functionality with real data
4. Update monitoring alerts if needed

---
*Generated by Deployment Verification Script v2.0*
*Target: {self.target_url}*
"""
        return report


def main():
    """Main deployment verification function"""
    parser = argparse.ArgumentParser(description="Verify blacklist.jclee.me deployment")
    parser.add_argument("--url", default="https://blacklist.jclee.me", 
                       help="Target URL (default: https://blacklist.jclee.me)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Maximum wait time in seconds (default: 300)")
    parser.add_argument("--wait", action="store_true",
                       help="Wait for deployment to complete")
    parser.add_argument("--health-only", action="store_true",
                       help="Only run health checks, skip version verification")
    parser.add_argument("--version-only", action="store_true", 
                       help="Only verify version, skip health checks")
    parser.add_argument("--output", type=str,
                       help="Output report to file")
    parser.add_argument("--json", action="store_true",
                       help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # Initialize verifier
    verifier = DeploymentVerifier(args.url, args.timeout)
    
    print(f"🚀 Starting deployment verification for {args.url}")
    print(f"📌 Expected version: {verifier.expected_version}")
    print(f"⏰ Timeout: {args.timeout}s")
    print("=" * 50)
    
    overall_success = True
    results = {}
    
    try:
        # Wait for deployment if requested
        if args.wait:
            wait_success, wait_results = verifier.wait_for_deployment(args.timeout)
            results["wait_results"] = wait_results
            if not wait_success:
                overall_success = False
        
        # Run version verification unless disabled
        if not args.health_only:
            version_success, version_info = verifier.verify_version_deployment()
            results["version_check"] = version_info
            if not version_success:
                overall_success = False
        
        # Run health checks unless disabled
        if not args.version_only:
            health_success, health_info = verifier.run_comprehensive_health_check()
            results["health_check"] = health_info
            if not health_success:
                overall_success = False
        
        # Generate output
        if args.json:
            output = json.dumps(results, indent=2, default=str)
        else:
            output = verifier.generate_report(results)
        
        # Save to file if requested
        if args.output:
            Path(args.output).write_text(output)
            print(f"📄 Report saved to: {args.output}")
        else:
            print("\n" + output)
        
        # Final result
        if overall_success:
            print("\n🎉 Deployment verification SUCCESSFUL!")
            sys.exit(0)
        else:
            print("\n❌ Deployment verification FAILED!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Verification failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()