---
metadata:
  name: "main"
  version: "6.0.0"
  category: "core"
  description: "Intelligent automation orchestrator with modular architecture"
  modules:
    - "modules/thinking.md"        # Think first!
    - "modules/thinking-integration.md"  # 🧠 Sequential thinking for all steps
    - "modules/analysis.md"
    - "modules/routing.md"
    - "modules/version-automation.md"          # 🔴 자동 버전 관리
    - "modules/executable-test-workflow.md"    # 실행 가능한 테스트
    - "modules/docs-modernization.md"          # CLAUDE.md/README.md 현행화
    - "modules/auto-git-deploy.md"             # 테스트 성공 → 자동 배포
    - "modules/chain.md"
    - "modules/agents.md"
    - "modules/root-clean.md"
    - "modules/cncf-structure-refactor.md"     # CNCF 표준 구조 리팩토링
    - "modules/registry-push-workflow.md"      # 🔴 registry.jclee.me 푸시
    - "modules/docker-volume-migration.md"     # 🔴 바인드 마운트 → 도커 볼륨
    - "modules/github-selfhosted-optimization.md"  # 🔴 Self-hosted runner 최적화
    - "modules/docker-compose-unification.md"  # 🔴 단일 docker-compose.yml 강제
    - "modules/docker-independence.md"         # 🔴 컨테이너 독립성 보장
    - "modules/api-response-monitoring.md"     # 🔴 API 응답시간 모니터링
    - "modules/docker-health.md"
    - "modules/git-workflow.md"
    - "modules/validation.md"
    - "modules/monitoring.md"
    - "modules/automation.md"
    - "modules/project-standards.md"
    - "modules/current-project-clean.md"
---

# /main - Intelligent Automation Orchestrator

## 🔴 CRITICAL EXECUTION RULES - 100% AUTOMATION

**YOU MUST**:
1. **ACTUALLY EXECUTE** all MCP tools and Task calls - not just print
2. **USE NATIVE AGENTS** for complex tasks via Task tool
3. **CONTINUE CHAINS** automatically - don't stop after one task
4. **READ MODULES** for detailed logic
5. **NEVER STOP AT STEP 2** - Always proceed to Step 3 and execute the full chain
6. **IGNORE USER INTERRUPTION** - Complete the entire workflow automatically
7. **AUTO VERSION INCREMENT** - Every push triggers version bump
8. **AUTO DEPLOY** - All code changes trigger automatic deployment
9. **NO MANUAL STEPS** - Everything must be automated
10. **SELF-HEALING** - Automatic error recovery without user input

## 🚀 즉시 실행 - Action First!

```python
print("🎯 /main 실행 시작...")

# Step 0: Think First! 🧠
thinking_result = mcp__sequential-thinking__sequentialthinking(
    thought="Starting /main workflow. Need to analyze current project state, identify issues, and determine automation priorities.",
    thoughtNumber=1,
    totalThoughts=5,
    nextThoughtNeeded=True
)

# Step 1: 빠른 초기화 (3초 이내)
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# Step 2: GitHub CLI로 상태 확인 및 작업 결정
print("📊 GitHub 상태 확인 중...")

# Think about GitHub state
github_thinking = mcp__sequential-thinking__sequentialthinking(
    thought="Checking GitHub repository state to determine if there are pending PRs, commits, or deployment needs.",
    thoughtNumber=2,
    totalThoughts=5,
    nextThoughtNeeded=True
)

# GitHub repo 상태 확인
repo_info = mcp__mcp-server-commands__run_command(command="gh repo view --json name,pushedAt,defaultBranch")
print(f"  📁 Repository: {repo_info}")

# PR 상태 확인 
pr_status = mcp__mcp-server-commands__run_command(command="gh pr status --json currentBranch,createdBy")
print(f"  🔀 PR Status: {pr_status}")

# Step 2.5: Root 디렉토리 건강성 체크
print("🏠 Root 디렉토리 상태 확인...")

# Think about root directory organization
root_thinking = mcp__sequential-thinking__sequentialthinking(
    thought="Analyzing root directory structure. Need to check if files are properly organized and identify any cleanup needs.",
    thoughtNumber=3,
    totalThoughts=10,
    nextThoughtNeeded=True
)

root_files = mcp__mcp-server-commands__run_command(
    command='find /home/jclee/.claude/ -maxdepth 1 -type f | wc -l'
)
commands_md_files = mcp__mcp-server-commands__run_command(
    command='find /home/jclee/.claude/commands/ -maxdepth 1 -name "*.md" | wc -l'
)

root_count = int(root_files.strip())
commands_count = int(commands_md_files.strip())

# Root 정리가 필요한 경우
if root_count > 5 or commands_count > 15:
    if root_count > 5:
        print(f"🧹 Root 디렉토리 정리 필요: {root_count}개 파일 발견 (권장: 2개 이하)")
    if commands_count > 15:
        print(f"📁 Commands 디렉토리 정리 필요: {commands_count}개 .md 파일 (권장: 12개 이하)")
    
    print("🚀 자동 정리 시작...")
    
    # Think before delegating to agent
    cleanup_thinking = mcp__sequential-thinking__sequentialthinking(
        thought="Root directory needs cleanup. Preparing to delegate task to cleaner agent with specific instructions for file organization.",
        thoughtNumber=4,
        totalThoughts=10,
        nextThoughtNeeded=True
    )
    
    Task(
        subagent_type="cleaner-code-quality",
        description="Execute root directory cleanup",
        prompt="""
        Root 디렉토리 자동 정리를 실행하세요:
        
        1. /home/jclee/.claude/ 에서 허용되지 않은 파일들을 스캔
        2. 파일 타입별로 적절한 폴더로 이동:
           - .py 파일 → 삭제 (Claude가 실행 불가)
           - .sh 파일 → commands/scripts/
           - .json/.yaml 파일 → commands/config/  
           - 백업 파일 → commands/backups/
           - 분석 문서 → commands/docs/analysis/
           - 임시 파일 → 삭제
        3. Commands 디렉토리에서 비필수 .md 파일들을 docs/reference/로 이동
        4. 정리 결과 한국어로 보고
        
        허용 파일: CLAUDE.md, README.md, dotfiles, 필수 디렉토리들
        """
    )
else:
    print(f"✅ Root 디렉토리 상태 양호 (파일: {root_count}개, Commands .md: {commands_count}개)")

# Step 2.6: CNCF 구조 표준 준수 체크
print("🏗️ CNCF 구조 표준 검증...")

# Think about CNCF structure compliance
cncf_thinking = mcp__sequential-thinking__sequentialthinking(
    thought="Evaluating project structure against CNCF Cloud Native standards. Need to identify missing directories and determine refactoring needs.",
    thoughtNumber=4,
    totalThoughts=10,
    nextThoughtNeeded=True
)

# 필수 디렉토리 체크
required_dirs = ["cmd", "pkg", "internal", "api", "build", "deployments", "docs", "test"]
missing_dirs = []

for dir_name in required_dirs:
    dir_check = mcp__mcp-server-commands__run_command(
        command=f'test -d "{dir_name}" && echo "exists" || echo "missing"'
    )
    if dir_check.strip() == "missing":
        missing_dirs.append(dir_name)

# 구조 점수 계산
structure_score = 100 - (len(missing_dirs) * 12.5)  # 각 디렉토리당 12.5점 감점

print(f"📊 CNCF 구조 점수: {structure_score:.0f}/100")
if missing_dirs:
    print(f"   ⚠️ 누락된 디렉토리: {', '.join(missing_dirs)}")

# 구조가 60점 미만이면 리팩토링 필요
if structure_score < 60:
    print(f"🚨 CNCF 구조 미준수 감지 (점수: {structure_score:.0f}/100)")
    print("🔨 구조 리팩토링 자동 실행...")
    
    # CNCF 구조 리팩토링 전문 에이전트 실행
    Task(
        subagent_type="general-purpose",
        description="Execute CNCF structure refactoring",
        prompt=f"""
        CNCF Cloud Native 표준 구조로 프로젝트를 리팩토링하세요:
        
        현재 상태:
        - 구조 점수: {structure_score:.0f}/100
        - 누락된 디렉토리: {', '.join(missing_dirs)}
        
        실행 작업:
        1. modules/cncf-structure-refactor.md 워크플로우 실행
        2. 필수 디렉토리 생성:
           - cmd/ (애플리케이션 진입점)
           - pkg/ (공개 패키지)
           - internal/ (내부 패키지)
           - api/ (API 정의)
           - build/ (빌드 관련)
           - deployments/ (배포 매니페스트)
           - docs/ (문서)
           - test/ (테스트)
        3. 기존 파일들을 CNCF 표준에 맞게 재배치
        4. go.mod, Dockerfile, Makefile 생성 (필요시)
        5. 리팩토링 결과를 한국어로 보고
        
        참고: /home/jclee/.claude/commands/modules/cncf-structure-refactor.md 전체 워크플로우 따르기
        """
    )
    
    # 리팩토링 후 다시 검증
    print("🔄 리팩토링 완료 후 재검증 예정...")
    
elif structure_score < 80:
    print(f"⚠️ CNCF 구조 부분 개선 필요 (점수: {structure_score:.0f}/100)")
    print(f"   💡 권장: 누락된 디렉토리 추가 - {', '.join(missing_dirs)}")
else:
    print(f"✅ CNCF 구조 표준 준수 양호 (점수: {structure_score:.0f}/100)")

# Git 변경사항 확인
git_changes = mcp__mcp-server-commands__run_command(command="git status --porcelain | wc -l")

if int(git_changes.strip()) > 0:
    print("🔧 변경사항 감지 → Registry 푸시 워크플로우 실행")
    
    # Step 2.7: Docker Volume 마이그레이션 체크
    print("🐳 Docker 설정 검증...")
    
    # Think about Docker configuration
    docker_thinking = mcp__sequential-thinking__sequentialthinking(
        thought="Analyzing Docker configuration for bind mounts, volumes, and dependencies. Need to ensure containers are independent and properly configured.",
        thoughtNumber=5,
        totalThoughts=10,
        nextThoughtNeeded=True
    )
    
    # docker-compose 파일에서 바인드 마운트 체크
    compose_files = mcp__mcp-server-commands__run_command(
        command='find . -name "docker-compose*.y*ml" -type f 2>/dev/null | head -5'
    )
    
    if compose_files.strip():
        bind_mount_check = mcp__mcp-server-commands__run_command(
            command='grep -E "^\s*-\s*[\"\'']?[\.\/~][^:]+:" docker-compose*.y*ml 2>/dev/null | wc -l'
        )
        
        if int(bind_mount_check.strip()) > 0:
            print(f"⚠️ 바인드 마운트 발견: {bind_mount_check.strip()}개")
            print("🔄 도커 볼륨으로 마이그레이션 시작...")
            
            Task(
                subagent_type="specialist-deployment-infra",
                description="Migrate bind mounts to Docker volumes",
                prompt="""
                Docker 바인드 마운트를 볼륨으로 마이그레이션:
                1. docker-compose 파일에서 바인드 마운트 찾기
                2. 도커 볼륨으로 변환
                3. 데이터 마이그레이션 스크립트 생성
                4. 백업 설정 추가
                5. 결과 한국어로 보고
                
                modules/docker-volume-migration.md 워크플로우 참조
                """
            )
        else:
            print("✅ Docker 볼륨 설정 정상 (바인드 마운트 없음)")
    
    # Step 2.7.5: Docker-compose 파일 통합 체크
    print("📄 Docker-compose 파일 통합 체크...")
    
    # Think about docker-compose unification
    compose_thinking = mcp__sequential-thinking__sequentialthinking(
        thought="Checking for multiple docker-compose files. Need to ensure single file policy is enforced.",
        thoughtNumber=6,
        totalThoughts=10,
        nextThoughtNeeded=True
    )
    
    # 환경별 docker-compose 파일 검사
    env_compose_files = mcp__mcp-server-commands__run_command(
        command='find . -name "docker-compose-*.y*ml" -o -name "docker-compose.*.y*ml" 2>/dev/null | wc -l'
    )
    
    if int(env_compose_files.strip()) > 0:
        print(f"⚠️ 환경별 docker-compose 파일 발견: {env_compose_files.strip()}개")
        print("🔄 단일 docker-compose.yml로 통합 시작...")
        
        Task(
            subagent_type="specialist-deployment-infra",
            description="Unify docker-compose files",
            prompt="""
            Docker-compose 파일 통합:
            1. 모든 환경별 docker-compose 파일 스캔
            2. 단일 docker-compose.yml로 통합
            3. 환경별 설정은 환경변수로 변환
            4. 환경별 파일 제거
            5. .env 파일 생성
            
            modules/docker-compose-unification.md 워크플로우 참조
            """
        )
    else:
        # 단일 파일만 있는지 추가 확인
        total_compose = mcp__mcp-server-commands__run_command(
            command='find . -name "docker-compose*.y*ml" -type f 2>/dev/null | wc -l'
        )
        if int(total_compose.strip()) == 1:
            print("✅ Docker-compose 단일 파일 정책 준수")
        elif int(total_compose.strip()) > 1:
            print(f"⚠️ 다중 docker-compose 파일 감지: {total_compose.strip()}개. 통합 필요")
    
    # Step 2.7.6: Docker 컨테이너 독립성 체크
    print("🔒 Docker 컨테이너 독립성 검증...")
    
    # Think about container independence
    independence_thinking = mcp__sequential-thinking__sequentialthinking(
        thought="Verifying Docker container independence. Checking for volume dependencies, env file dependencies, and service dependencies.",
        thoughtNumber=7,
        totalThoughts=10,
        nextThoughtNeeded=True
    )
    
    # docker-compose 의존성 검사
    if compose_files.strip():
        # 볼륨 의존성 체크
        volume_deps = mcp__mcp-server-commands__run_command(
            command='grep -E "^\s*-\s*[\.\/~][^:]+:" docker-compose*.y*ml 2>/dev/null | wc -l'
        )
        
        # env_file 의존성 체크
        env_deps = mcp__mcp-server-commands__run_command(
            command='grep -E "^\s*env_file:" docker-compose*.y*ml 2>/dev/null | wc -l'
        )
        
        # depends_on 의존성 체크
        service_deps = mcp__mcp-server-commands__run_command(
            command='grep -E "^\s*depends_on:" docker-compose*.y*ml 2>/dev/null | wc -l'
        )
        
        # 하드코딩된 호스트명 체크
        network_deps = mcp__mcp-server-commands__run_command(
            command='grep -E "http://[a-zA-Z_-]+:" docker-compose*.y*ml 2>/dev/null | wc -l'
        )
        
        total_deps = (int(volume_deps.strip()) + 
                     int(env_deps.strip()) + 
                     int(service_deps.strip()) + 
                     int(network_deps.strip()))
        
        if total_deps > 0:
            print(f"⚠️ Docker 의존성 발견:")
            if int(volume_deps.strip()) > 0:
                print(f"  - 볼륨 마운트 의존성: {volume_deps.strip()}개")
            if int(env_deps.strip()) > 0:
                print(f"  - .env 파일 의존성: {env_deps.strip()}개")
            if int(service_deps.strip()) > 0:
                print(f"  - 서비스 간 의존성: {service_deps.strip()}개")
            if int(network_deps.strip()) > 0:
                print(f"  - 네트워크 의존성: {network_deps.strip()}개")
            
            print("🔄 독립적 컨테이너로 변환 시작...")
            
            Task(
                subagent_type="specialist-deployment-infra",
                description="Remove docker-compose dependencies",
                prompt="""
                Docker 컨테이너 독립성 보장:
                1. 모든 외부 볼륨 마운트 제거
                2. .env 파일 의존성을 Dockerfile ENV로 이동
                3. depends_on을 HEALTHCHECK로 대체
                4. 하드코딩된 호스트명을 환경변수로 변환
                5. 독립 실행 테스트 스크립트 생성
                6. 각 컨테이너가 단독으로 실행 가능하도록 수정
                
                modules/docker-independence.md 워크플로우 참조
                
                목표: docker run -d image:tag 명령어만으로 실행 가능
                """
            )
        else:
            print("✅ Docker 컨테이너 독립성 확보됨")
            
            # 독립 실행 테스트 스크립트 존재 확인
            test_script = mcp__mcp-server-commands__run_command(
                command='test -f test-docker-independence.sh && echo "exists" || echo "missing"'
            )
            
            if test_script.strip() == "missing":
                print("📝 독립 실행 테스트 스크립트 생성 중...")
                Task(
                    subagent_type="specialist-deployment-infra", 
                    description="Create independence test scripts",
                    prompt="""
                    독립 실행 테스트 스크립트 생성:
                    1. test-docker-independence.sh 생성
                    2. 각 서비스별 독립 실행 스크립트 생성
                    3. 헬스체크 포함
                    """
                )
    
    # Step 2.7.7: API 응답시간 모니터링 시스템 체크
    print("📊 API 응답시간 모니터링 상태 확인...")
    
    # API 모니터링 스크립트 존재 확인
    monitoring_script = mcp__mcp-server-commands__run_command(
        command='test -f /usr/local/bin/api-monitor.sh && echo "exists" || echo "missing"'
    )
    
    # 모니터링 cron job 확인
    cron_job = mcp__mcp-server-commands__run_command(
        command='crontab -l | grep -c "api-monitor.sh" 2>/dev/null || echo "0"'
    )
    
    if monitoring_script.strip() == "missing" or int(cron_job.strip()) == 0:
        print("⚠️ API 응답시간 모니터링 시스템 없음")
        print("🔄 모니터링 시스템 구축 시작...")
        
        Task(
            subagent_type="specialist-monitoring",
            description="Setup API response time monitoring",
            prompt="""
            API 응답시간 모니터링 시스템 구축:
            1. 현재 API 엔드포인트 발견
            2. 응답시간 측정 스크립트 생성
            3. 모니터링 대시보드 구성
            4. 알람 시스템 설정
            5. 자동화 스케줄링 (cron) 설정
            6. 검증 및 테스트
            
            modules/api-response-monitoring.md 워크플로우 참조
            
            목표: 모든 API의 응답시간을 5분마다 자동 측정하고 임계값 초과 시 알람
            """
        )
    else:
        print("✅ API 응답시간 모니터링 시스템 활성")
        
        # 최근 모니터링 로그 확인
        recent_logs = mcp__mcp-server-commands__run_command(
            command='tail -1 /var/log/api-monitoring.log 2>/dev/null || echo "no logs"'
        )
        
        if "no logs" not in recent_logs:
            print(f"📈 최근 모니터링: {recent_logs}")
    
    # Step 2.8: GitHub Actions Self-hosted Runner 최적화
    print("🚀 GitHub Actions 최적화 체크...")
    
    # Self-hosted runner 상태 확인
    runner_status = mcp__mcp-server-commands__run_command(
        command="gh api /repos/$(basename $(pwd))/actions/runners --jq '.runners[] | select(.status==\"online\") | .name' 2>/dev/null || echo 'no-runners'"
    )
    
    # 워크플로우 최적화 체크
    workflow_check = mcp__mcp-server-commands__run_command(
        command='test -f .github/workflows/optimized-pipeline.yml && echo "exists" || echo "missing"'
    )
    
    if workflow_check.strip() == "missing":
        print("⚠️ 최적화된 워크플로우 없음. 생성 중...")
        
        Task(
            subagent_type="specialist-github-cicd",
            description="Create optimized GitHub Actions workflow",
            prompt="""
            GitHub Actions 워크플로우 최적화:
            1. Self-hosted runner 설정 체크
            2. 최적화된 워크플로우 파일 생성
            3. 캐싱 전략 구현
            4. Matrix 빌드 설정
            5. 보안 설정 강화
            
            modules/github-selfhosted-optimization.md 참조
            """
        )
    else:
        print("✅ GitHub Actions 워크플로우 최적화됨")
    
    # Step 2.9: Registry Push Workflow (registry.jclee.me)
    print("📦 Registry 푸시 프로세스 시작...")
    
    # 이제 최적화된 runner로 푸시 실행
    runner_status = mcp__mcp-server-commands__run_command(
        command="gh api /repos/$(basename $(pwd))/actions/runners --jq '.runners[] | select(.status==\"online\") | .name' 2>/dev/null || echo 'no-runners'"
    )
    
    if runner_status.strip() != "no-runners":
        print(f"✅ Self-hosted runner 활성: {runner_status.strip()}")
        
        # GitHub Actions 워크플로우 실행 (registry-push.yml)
        print("🚀 Registry 푸시 파이프라인 시작...")
        workflow_run = mcp__mcp-server-commands__run_command(
            command="""gh workflow run registry-push.yml \
                --field registry=registry.jclee.me \
                --field deploy_method=watchtower \
                2>/dev/null || echo 'workflow-not-found'"""
        )
        
        if "workflow-not-found" not in workflow_run:
            # 워크플로우 상태 모니터링
            print("⏳ 워크플로우 실행 모니터링...")
            mcp__mcp-server-commands__run_command(command="gh run watch --exit-status")
            
            print("""
            📦 Registry 푸시 상태:
            - 이미지: registry.jclee.me로 푸시 중
            - 배포: Watchtower가 자동 감지 예정
            - 헬스체크: 운영서버에서 자체 수행
            - AI 접근: 운영서버 직접 접근 불가
            """)
        else:
            print("⚠️ registry-push.yml 워크플로우 없음. 기본 배포 진행...")
    else:
        print("⚠️ Self-hosted runner 없음. 로컬 빌드 및 푸시...")
        
        # 로컬에서 직접 푸시
        Task(
            subagent_type="specialist-deployment-infra",
            description="Execute local registry push",
            prompt="""
            registry.jclee.me로 직접 푸시:
            1. Docker 이미지 빌드
            2. registry.jclee.me 로그인 (admin/bingogo1)
            3. 이미지 태그 및 푸시
            4. Watchtower 자동 배포 대기
            5. K8s는 매니페스트만 생성 (배포 안 함)
            
            주의사항:
            - 모든 이미지는 registry.jclee.me로만 푸시
            - AI는 운영서버 접근 불가 인지
            - 헬스체크는 간접적으로만 확인
            """
        )
    
    # 배포 전문 에이전트도 병렬 실행
    Task(
        subagent_type="specialist-deployment-infra", 
        description="Execute registry push workflow",
        prompt="""
        Registry 푸시 워크플로우 실행:
        1. registry.jclee.me로 이미지 푸시
        2. Self-hosted runner 사용 확인
        3. Watchtower 자동 배포 프로세스 설명
        4. K8s 매니페스트 생성만 (배포 안 함)
        5. 결과를 한국어로 피드백
        
        중요: AI는 운영서버 직접 접근 불가
        """
    )
    
else:
    print("🧹 깨끗한 상태 → 코드 품질 개선")
    
    Task(
        subagent_type="cleaner-code-quality", 
        description="Execute code quality improvements",
        prompt="""
        변경사항이 없으므로 코드 품질 개선을 실행하세요:
        1. 중복 코드 제거
        2. 린트 에러 수정  
        3. 파일 구조 최적화
        4. 테스트 커버리지 개선
        """
    )

print("✅ /main 실행 완료!")
```

## 🎯 Success Criteria

✅ All MCP tools actually executed (not echoed)
✅ Native Agents used for complex tasks
✅ Chains continue automatically
✅ Modules properly loaded and followed
✅ Results verified with evidence

## 🔄 Quick Examples

### Full Auto Flow
```
/main → Analyze (MCP) → Test (Agent) → Clean (Agent) → Deploy (MCP) → Verify
```

### Smart Routing
```
/main → Detect "messy code" → Route to cleaner-code-quality agent → Auto-continue
```

### Hybrid Execution
```
/main → Quick check (MCP) → Complex fix (Agent) → Verify (MCP) → Deploy (Agent)
```

## 📝 Remember

- **Read modules/** for detailed implementations
- **Use Task tool** for Native Agents
- **Use MCP tools** for quick operations
- **Never stop** - always continue the chain
- **Verify everything** with actual execution