# /deploy - GitOps Deployment

# Docker-Compose 배포 절차

**Execute MCP tools for Docker-Compose deployment:**

```python
# 1. Activate Serena
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# 2. GitHub CLI를 활용한 배포 전 검증
print("🔍 GitHub 상태 확인 중...")

# PR 병합 상태 확인
merged_prs = mcp__serena__execute_shell_command('gh pr list --state merged --limit 5')
print(f"  ✅ 최근 병합된 PR: {merged_prs}")

# CI/CD 워크플로우 상태 확인  
workflow_status = mcp__serena__execute_shell_command('gh run list --workflow="CI/CD Pipeline" --limit 3')
print(f"  🔄 워크플로우 상태: {workflow_status}")

# Release 준비
print("📦 Release 생성 중...")
release_result = mcp__serena__execute_shell_command('gh release create v$(date +%Y.%m.%d) --title "Release $(date +%Y-%m-%d)" --generate-notes')

# 기존 검증 로직
git_status = mcp__serena__execute_shell_command('git status --porcelain')
docker_status = mcp__serena__execute_shell_command('docker version && docker-compose version')
services_health = mcp__serena__execute_shell_command('docker-compose ps')

# 3. Environment validation
env_validation = {
    "docker_registry": validate_docker_registry_access(),
    "compose_file": validate_compose_configuration(),
    "environment_vars": validate_environment_variables(),
    "port_conflicts": check_port_availability(),
    "disk_space": check_disk_space_requirements()
}

# 4. Playwright E2E testing (REQUIRED before deployment)
Task(
    subagent_type="runner-test-automation", 
    description="Execute Playwright E2E tests",
    prompt="Run comprehensive Playwright tests: UI functionality, API endpoints, integration flows, error handling. ALL tests must pass before deployment."
)

# 5. Deploy with specialized agent
Task(
    subagent_type="specialist-deployment-infra",
    description="Execute Docker-Compose deployment",
    prompt="Deploy services using docker-compose: build images, start containers, health checks, service dependencies."
)

# 6. Post-deployment monitoring
deployment_status = mcp__serena__execute_shell_command('docker-compose ps -a')
health_checks = mcp__serena__execute_shell_command('docker-compose exec commands-app curl -f http://localhost:3000/health')
service_logs = mcp__serena__execute_shell_command('docker-compose logs --tail=50')

# 7. Store deployment results
mcp__serena__write_memory('deploy_status', f'''
Deployment completed: {datetime.now()}
Services status: {deployment_status}
Health checks: {health_checks}
Environment: {env_validation}
''')

print("✅ Docker-Compose deployment completed → Services running")
```
     description="GitOps deployment execution",
     prompt="""
CRITICAL SECURITY REQUIREMENTS:
1. Validate all service tokens (ArgoCD, GitHub, Registry)
2. Check for hardcoded credentials in code
3. Verify no sensitive data in commit history
4. Ensure all environment variables are properly configured
5. Validate Kubernetes resource limits and security contexts
""")
```

### Token Validation & Management
```python
# Auto-validate all required credentials
credential_check = {
    "argocd_token": validate_argocd_jwt(),
    "github_token": validate_github_pat(),
    "registry_credentials": validate_docker_registry(),
    "k8s_access": validate_kubernetes_access()
}

# Auto-renewal for expired tokens
for credential, status in credential_check.items():
    if status.expired or status.expires_soon:
        auto_renew_credential(credential)
```

## GitOps Workflow Execution

### GitHub Actions CI/CD Pipeline
```python
# Never use direct docker/helm/kubectl commands
# Always use GitHub Actions pipeline
deployment_workflow = {
    "pre_checks": run_pre_deployment_validation(),
    "git_commit": create_deployment_commit(),
    "pipeline_trigger": push_to_trigger_github_actions(),
    "monitoring": monitor_pipeline_execution(),
    "verification": verify_deployment_success()
}
```

### Automated Git Operations
```bash
# Intelligent commit creation
git add .
git commit -m "$(generate_intelligent_commit_message())"
git push origin main

# This triggers: GitHub Actions → Docker Build → registry.jclee.me
#                    ↓
# Helm Package → charts.jclee.me → ArgoCD Detection → Kubernetes Deploy
```

## ArgoCD Integration & Monitoring

### Real-time Deployment Monitoring
```python
# Monitor ArgoCD application status
argocd_monitoring = {
    "sync_status": monitor_app_sync_status(),
    "health_status": check_application_health(),
    "resource_status": verify_all_resources_deployed(),
    "rollback_readiness": prepare_automatic_rollback()
}

# Auto-rollback on failure detection
if argocd_monitoring.health_status != "Healthy":
    initiate_automatic_rollback()
```

### Service Verification Protocol
```python
# Verify deployed services work as intended
service_verification = {
    "health_endpoints": test_all_health_endpoints(),
    "api_functionality": validate_api_responses(),
    "database_connectivity": verify_database_connections(),
    "external_integrations": test_third_party_services()
}
```

## Infrastructure Endpoints (Production)

### Registry & Repository Management
```python
# Production infrastructure configuration
infrastructure_config = {
    "docker_registry": "registry.jclee.me",
    "helm_repository": "charts.jclee.me",
    "argocd_dashboard": "argo.jclee.me",
    "credentials": {
        "username": "admin",
        "password": "bingogo1"  # Environment managed
    }
}
```

### Kubernetes Cluster Operations
```python
# Internal cluster management via kubectl
k8s_operations = {
    "namespace_management": ensure_namespace_exists(),
    "resource_monitoring": monitor_pod_health(),
    "scaling_decisions": auto_scale_based_on_load(),
    "security_policies": enforce_security_contexts()
}
```

## Advanced Deployment Features

### Blue-Green Deployment Strategy
```python
# Zero-downtime deployment approach
blue_green_deployment = {
    "current_version": get_current_production_version(),
    "new_version": prepare_new_version_deployment(),
    "traffic_switching": gradual_traffic_migration(),
    "rollback_preparation": maintain_previous_version_ready()
}
```

### Intelligent Health Monitoring
```python
# Post-deployment health validation
health_monitoring = {
    "response_time": monitor_api_response_times(),
    "error_rates": track_error_percentages(),
    "resource_usage": monitor_cpu_memory_utilization(),
    "user_experience": validate_end_user_functionality()
}
```

## Korean User Feedback
```korean
배포 진행 상황:
- "보안 검증 시작..."
- "토큰 유효성 확인 완료"
- "GitHub Actions 파이프라인 실행 중..."
- "ArgoCD 동기화 진행 중..."
- "서비스 상태 검증 중..."
- "배포 완료 및 서비스 정상 동작 확인"
```

## Emergency Response Protocols

### Automatic Rollback System
```python
# Failure detection and response
emergency_protocols = {
    "failure_detection": {
        "response_time_degradation": "> 2x normal",
        "error_rate_spike": "> 5% error rate",
        "resource_exhaustion": "> 80% CPU/Memory",
        "health_check_failures": "> 2 consecutive failures"
    },
    "rollback_triggers": auto_rollback_on_failure_detection(),
    "notification_system": alert_team_on_deployment_issues()
}
```

### Service Recovery Procedures
```python
# Intelligent recovery strategies
recovery_strategies = {
    "pod_restart": restart_failing_pods(),
    "traffic_rerouting": redirect_traffic_to_healthy_instances(),
    "database_failover": switch_to_backup_database(),
    "cache_invalidation": clear_corrupted_cache_data()
}
```

## Continuous Deployment Optimization

### Performance Metrics Tracking
```python
# Deployment efficiency monitoring
deployment_metrics = {
    "pipeline_duration": track_ci_cd_execution_time(),
    "deployment_frequency": monitor_deployment_cadence(),
    "failure_rate": calculate_deployment_success_rate(),
    "recovery_time": measure_rollback_efficiency()
}
```

### Predictive Analysis
- **Deployment Risk Assessment**: AI-powered risk analysis before deployment
- **Capacity Planning**: Predict resource needs based on usage patterns
- **Failure Prediction**: Identify potential failure points before deployment
- **Optimization Recommendations**: Suggest improvements based on historical data