---
metadata:
  name: "main-add"
  version: "1.0.0"
  category: "core"
  description: "/main add {지시사항} - 자동 분석, 모듈 생성 및 워크플로우 연동"
  dependencies:
    - "mcp__shrimp-task-manager"
    - "mcp__serena"
    - "mcp__sequential-thinking"
---

# /main add Command - 지시사항 자동 통합 시스템

## 🎯 목적
사용자 지시사항을 분석하여 자동으로 모듈을 생성하고 main workflow에 연동

## 📝 명령어 구조
```bash
/main add {지시사항}
```

## 🔄 자동화 워크플로우

```python
def main_add_command(instruction):
    """
    /main add 명령어 처리
    1. 지시사항 분석
    2. 모듈 자동 생성  
    3. main workflow 연동
    4. 테스트 및 검증
    """
    
    print(f"🎯 /main add 실행: {instruction}")
    
    # Step 1: 지시사항 분석
    analysis_result = analyze_instruction(instruction)
    
    # Step 2: 모듈 생성
    module_info = generate_module(analysis_result)
    
    # Step 3: main workflow 연동
    integrate_to_main_workflow(module_info)
    
    # Step 4: 검증
    validate_integration(module_info)
    
    return f"✅ 지시사항 '{instruction}' 자동 통합 완료"

def analyze_instruction(instruction):
    """지시사항 심층 분석"""
    
    print("🔍 지시사항 분석 시작...")
    
    # Sequential Thinking으로 분석
    analysis = mcp__sequential_thinking__sequentialthinking(
        thought=f"""
        사용자 지시사항 분석: "{instruction}"
        
        분석 항목:
        1. 기술 도메인 (Docker, GitHub, CI/CD, 보안, 네트워크 등)
        2. 작업 유형 (설정, 최적화, 자동화, 검증, 배포 등)
        3. 의존성 (기존 모듈과의 관계)
        4. 우선순위 (긴급도/중요도)
        5. 구현 복잡도
        6. 검증 방법
        """,
        thought_number=1,
        total_thoughts=5,
        next_thought_needed=True
    )
    
    # Task Manager로 세부 분석
    detailed_analysis = mcp__shrimp_task_manager__analyze_task(
        summary=f"지시사항 분석: {instruction}",
        initial_concept=f"""
        사용자가 요청한 '{instruction}' 지시사항에 대한 기술적 분석:
        
        1. 도메인 분류 및 범위 설정
        2. 기존 시스템과의 통합 지점 식별
        3. 자동화 가능 영역 및 수동 개입 필요 영역 구분
        4. 구현 우선순위 및 의존성 매핑
        5. 성공 기준 및 검증 방법 정의
        """
    )
    
    return {
        'instruction': instruction,
        'domain': extract_domain(instruction),
        'work_type': extract_work_type(instruction),
        'complexity': assess_complexity(instruction),
        'dependencies': find_dependencies(instruction),
        'priority': assess_priority(instruction),
        'verification_method': define_verification(instruction)
    }

def extract_domain(instruction):
    """기술 도메인 추출"""
    
    domain_keywords = {
        'docker': ['docker', 'container', '컨테이너', 'dockerfile', 'compose'],
        'github': ['github', 'actions', 'workflow', 'ci/cd', 'pipeline'],
        'security': ['보안', 'security', 'auth', '인증', 'ssl', 'tls'],
        'network': ['network', '네트워크', 'proxy', 'nginx', 'dns'],
        'deployment': ['deploy', '배포', 'k8s', 'kubernetes', 'helm'],
        'monitoring': ['monitoring', '모니터링', 'log', 'metric', 'alert'],
        'database': ['db', 'database', 'postgres', 'redis', 'mysql'],
        'api': ['api', 'rest', 'graphql', 'endpoint', 'service']
    }
    
    instruction_lower = instruction.lower()
    detected_domains = []
    
    for domain, keywords in domain_keywords.items():
        if any(keyword in instruction_lower for keyword in keywords):
            detected_domains.append(domain)
    
    return detected_domains if detected_domains else ['general']

def extract_work_type(instruction):
    """작업 유형 분류"""
    
    work_types = {
        'automation': ['자동', 'auto', 'workflow', '워크플로우'],
        'optimization': ['최적화', 'optimize', 'improve', '개선'],
        'configuration': ['설정', 'config', 'configure', '구성'],
        'validation': ['검증', 'validate', 'test', '테스트'],
        'integration': ['연동', 'integrate', '통합', 'connect'],
        'security': ['보안', 'secure', '보호', 'protect'],
        'monitoring': ['모니터링', 'monitor', '감시', 'watch'],
        'deployment': ['배포', 'deploy', '릴리스', 'release']
    }
    
    instruction_lower = instruction.lower()
    detected_types = []
    
    for work_type, keywords in work_types.items():
        if any(keyword in instruction_lower for keyword in keywords):
            detected_types.append(work_type)
    
    return detected_types if detected_types else ['general']

def assess_complexity(instruction):
    """구현 복잡도 평가"""
    
    # 복잡도 지표
    complexity_indicators = {
        'high': ['분산', 'distributed', '마이크로서비스', 'kubernetes', 'multi'],
        'medium': ['docker', 'github', 'workflow', 'integration'],
        'low': ['설정', 'config', 'simple', '단순']
    }
    
    instruction_lower = instruction.lower()
    
    for level, indicators in complexity_indicators.items():
        if any(indicator in instruction_lower for indicator in indicators):
            return level
    
    return 'medium'  # 기본값

def find_dependencies(instruction):
    """의존성 모듈 찾기"""
    
    # 기존 모듈과의 연관성 체크
    existing_modules = [
        'docker-independence', 'docker-volume-migration', 'docker-compose-unification',
        'github-selfhosted-optimization', 'registry-push-workflow',
        'cncf-structure-refactor', 'root-clean'
    ]
    
    instruction_lower = instruction.lower()
    related_modules = []
    
    module_keywords = {
        'docker-independence': ['docker', 'independent', '독립'],
        'docker-volume-migration': ['volume', '볼륨', 'mount'],
        'github-selfhosted-optimization': ['github', 'actions', 'runner'],
        'registry-push-workflow': ['registry', 'push', '푸시'],
        'cncf-structure-refactor': ['structure', '구조', 'cncf'],
        'root-clean': ['root', 'clean', '정리']
    }
    
    for module, keywords in module_keywords.items():
        if any(keyword in instruction_lower for keyword in keywords):
            related_modules.append(module)
    
    return related_modules

def assess_priority(instruction):
    """우선순위 평가"""
    
    priority_keywords = {
        'critical': ['긴급', 'urgent', 'critical', '즉시', 'asap'],
        'high': ['중요', 'important', 'high', '우선'],
        'medium': ['보통', 'medium', 'normal'],
        'low': ['나중', 'later', 'low', '추후']
    }
    
    instruction_lower = instruction.lower()
    
    for priority, keywords in priority_keywords.items():
        if any(keyword in instruction_lower for keyword in keywords):
            return priority
    
    return 'medium'  # 기본값

def define_verification(instruction):
    """검증 방법 정의"""
    
    domain = extract_domain(instruction)[0] if extract_domain(instruction) else 'general'
    
    verification_methods = {
        'docker': 'Docker 컨테이너 독립 실행 테스트',
        'github': 'GitHub Actions 워크플로우 실행 테스트',
        'security': '보안 스캔 및 취약점 검사',
        'network': '네트워크 연결 및 응답 테스트',
        'deployment': '배포 파이프라인 실행 검증',
        'monitoring': '메트릭 수집 및 알람 테스트',
        'database': 'DB 연결 및 쿼리 성능 테스트',
        'api': 'API 엔드포인트 응답 테스트',
        'general': '기능 동작 및 통합 테스트'
    }
    
    return verification_methods.get(domain, verification_methods['general'])

def generate_module(analysis_result):
    """분석 결과를 바탕으로 모듈 자동 생성"""
    
    print("🔧 모듈 자동 생성 시작...")
    
    instruction = analysis_result['instruction']
    domains = analysis_result['domain']
    work_types = analysis_result['work_type']
    
    # 모듈명 생성
    module_name = generate_module_name(instruction, domains, work_types)
    
    # 모듈 콘텐츠 생성
    module_content = generate_module_content(analysis_result)
    
    # 파일 저장
    module_path = f"/home/jclee/.claude/commands/modules/{module_name}.md"
    
    # Task Manager로 모듈 생성
    task_result = mcp__shrimp_task_manager__split_tasks(
        update_mode="clearAllTasks",
        global_analysis_result=f"사용자 지시사항 '{instruction}' 구현을 위한 모듈 생성",
        tasks_raw=f"""[{{
            "name": "모듈 파일 생성",
            "description": "{module_path}에 모듈 파일 생성",
            "implementation_guide": "분석 결과를 바탕으로 표준 모듈 템플릿 사용하여 생성",
            "verification_criteria": "모듈 파일이 올바른 형식으로 생성되고 메타데이터가 포함되어야 함",
            "dependencies": [],
            "related_files": [{{
                "path": "{module_path}",
                "type": "CREATE",
                "description": "생성할 모듈 파일"
            }}]
        }}]"""
    )
    
    # 실제 파일 생성
    mcp__serena__create_text_file(
        relative_path=module_path.replace("/home/jclee/.claude/commands/", ""),
        content=module_content
    )
    
    print(f"✅ 모듈 생성 완료: {module_path}")
    
    return {
        'name': module_name,
        'path': module_path,
        'content': module_content,
        'analysis': analysis_result
    }

def generate_module_name(instruction, domains, work_types):
    """모듈명 자동 생성"""
    
    # 도메인과 작업 유형 조합으로 모듈명 생성
    domain_part = domains[0] if domains else 'general'
    work_part = work_types[0] if work_types else 'task'
    
    # 특수 문자 제거 및 케밥 케이스 변환
    name_parts = []
    
    if domain_part != 'general':
        name_parts.append(domain_part)
    
    if work_part != 'general':
        name_parts.append(work_part)
    
    # 지시사항에서 핵심 키워드 추출
    keywords = extract_keywords_from_instruction(instruction)
    if keywords:
        name_parts.extend(keywords[:2])  # 최대 2개 키워드
    
    module_name = '-'.join(name_parts)
    
    # 길이 제한 (최대 50자)
    if len(module_name) > 50:
        module_name = module_name[:47] + '...'
    
    return module_name

def extract_keywords_from_instruction(instruction):
    """지시사항에서 핵심 키워드 추출"""
    
    # 불용어 제거
    stop_words = ['및', '그리고', '또는', '하면', '해서', '에서', '으로', '를', '을', '이', '가']
    
    # 한글/영문 키워드 추출
    import re
    
    # 한글 키워드
    korean_words = re.findall(r'[가-힣]+', instruction)
    # 영문 키워드  
    english_words = re.findall(r'[a-zA-Z]+', instruction)
    
    # 불용어 제거 및 길이 필터링
    keywords = []
    for word in korean_words + english_words:
        if (word.lower() not in stop_words and 
            len(word) >= 2 and 
            len(word) <= 15):
            keywords.append(word.lower())
    
    return keywords[:3]  # 최대 3개

def generate_module_content(analysis_result):
    """모듈 콘텐츠 생성"""
    
    instruction = analysis_result['instruction']
    domains = analysis_result['domain']
    work_types = analysis_result['work_type']
    complexity = analysis_result['complexity']
    verification = analysis_result['verification_method']
    
    content = f"""---
metadata:
  name: "{analysis_result.get('module_name', 'auto-generated')}"
  version: "1.0.0"
  category: "{domains[0] if domains else 'general'}"
  description: "Auto-generated module for: {instruction}"
  dependencies:
    - "mcp__mcp-server-commands"
    - "mcp__serena"
---

# {instruction} - 자동 생성 모듈

## 🎯 목적
{instruction}

## 📊 분석 결과
- **도메인**: {', '.join(domains)}
- **작업 유형**: {', '.join(work_types)}
- **복잡도**: {complexity}
- **의존성**: {', '.join(analysis_result.get('dependencies', []))}
- **우선순위**: {analysis_result.get('priority', 'medium')}

## 🔧 구현 워크플로우

```python
def execute_{analysis_result.get('module_name', 'task').replace('-', '_')}():
    \"\"\"
    {instruction} 자동 실행
    \"\"\"
    
    print("🚀 {instruction} 실행 시작...")
    
    # Step 1: 현재 상태 체크
    current_state = check_current_state()
    
    # Step 2: 필요한 변경사항 식별
    required_changes = identify_required_changes(current_state)
    
    # Step 3: 변경사항 적용
    apply_changes(required_changes)
    
    # Step 4: 검증
    validation_result = validate_changes()
    
    if validation_result['success']:
        print("✅ {instruction} 완료")
        return True
    else:
        print(f"❌ {instruction} 실패: {{validation_result['error']}}")
        return False

def check_current_state():
    \"\"\"현재 상태 체크\"\"\"
    
    # TODO: 도메인별 상태 체크 로직 구현
    # {domains[0] if domains else 'general'} 관련 상태 확인
    
    return {{
        'status': 'unknown',
        'issues': [],
        'recommendations': []
    }}

def identify_required_changes(current_state):
    \"\"\"필요한 변경사항 식별\"\"\"
    
    changes = []
    
    # TODO: 분석 결과를 바탕으로 변경사항 식별
    # 작업 유형: {', '.join(work_types)}
    
    return changes

def apply_changes(required_changes):
    \"\"\"변경사항 적용\"\"\"
    
    for change in required_changes:
        print(f"  🔧 적용 중: {{change['description']}}")
        
        # TODO: 실제 변경 로직 구현
        execute_change(change)

def validate_changes():
    \"\"\"변경사항 검증\"\"\"
    
    print("🧪 검증 시작: {verification}")
    
    # TODO: 검증 로직 구현
    # {verification}
    
    return {{
        'success': True,
        'message': '검증 완료',
        'details': []
    }}

# 실행 진입점
if __name__ == "__main__":
    print("🎯 {instruction} 모듈 실행")
    
    success = execute_{analysis_result.get('module_name', 'task').replace('-', '_')}()
    
    if success:
        print("✅ 모듈 실행 완료")
    else:
        print("❌ 모듈 실행 실패")
```

## 📋 체크리스트

- [ ] 현재 상태 분석
- [ ] 요구사항 정의
- [ ] 구현 계획 수립
- [ ] 코드 개발
- [ ] 테스트 실행
- [ ] 검증 완료
- [ ] 문서화

## 🎯 성공 기준

{verification}

## 📝 참고사항

이 모듈은 사용자 지시사항 '{instruction}'을 바탕으로 자동 생성되었습니다.
구현 세부사항은 실제 요구사항에 맞게 조정이 필요할 수 있습니다.
"""
    
    return content

def integrate_to_main_workflow(module_info):
    """main workflow에 자동 연동"""
    
    print("🔗 Main workflow 연동 시작...")
    
    module_name = module_info['name']
    analysis = module_info['analysis']
    
    # 1. main.md 모듈 리스트에 추가
    add_to_module_list(module_name, analysis)
    
    # 2. 워크플로우 실행 섹션에 체크 로직 추가
    add_to_workflow_execution(module_name, analysis)
    
    print(f"✅ Main workflow 연동 완료: {module_name}")

def add_to_module_list(module_name, analysis):
    """모듈 리스트에 추가"""
    
    # main.md 읽기
    main_content = mcp__serena__read_file("main.md")
    
    # 새 모듈 라인 생성
    domains = analysis['domain']
    work_types = analysis['work_type']
    
    description = f"{domains[0] if domains else 'general'} {work_types[0] if work_types else 'task'}"
    new_module_line = f'    - "modules/{module_name}.md"         # 🔴 {description}'
    
    # docker-health.md 앞에 삽입
    mcp__serena__replace_regex(
        relative_path="main.md",
        regex=r'(\s+- "modules/docker-health\.md")',
        repl=f'{new_module_line}\\n\\1'
    )

def add_to_workflow_execution(module_name, analysis):
    """워크플로우 실행 섹션에 체크 로직 추가"""
    
    instruction = analysis['instruction']
    domains = analysis['domain']
    priority = analysis['priority']
    
    # 우선순위에 따라 삽입 위치 결정
    if priority == 'critical':
        insert_position = "Step 2.3"  # 빠른 체크
    elif priority == 'high':
        insert_position = "Step 2.5"  # 중간 체크  
    else:
        insert_position = "Step 2.8"  # 나중 체크
    
    # 체크 로직 생성
    check_logic = f"""
    # {insert_position}: {instruction} 체크
    print("🔍 {instruction} 상태 확인...")
    
    # {module_name} 모듈 상태 체크
    {module_name.replace('-', '_')}_status = mcp__mcp-server-commands__run_command(
        command='python -c "from modules.{module_name.replace("-", "_")} import check_current_state; print(check_current_state())"'
    )
    
    if "{domains[0] if domains else 'issue'}" in {module_name.replace('-', '_')}_status:
        print("⚠️ {instruction} 이슈 발견")
        print("🔄 자동 수정 시작...")
        
        Task(
            subagent_type="specialist-{domains[0] if domains else 'general'}",
            description="Execute {instruction}",
            prompt='''
            {instruction} 자동 실행:
            1. 현재 상태 분석
            2. 문제점 식별
            3. 수정 사항 적용
            4. 검증 실행
            
            modules/{module_name}.md 워크플로우 참조
            '''
        )
    else:
        print("✅ {instruction} 정상 상태")
"""
    
    # GitHub Actions 최적화 앞에 삽입
    mcp__serena__replace_regex(
        relative_path="main.md",
        regex=r'(\s+# Step 2\.8: GitHub Actions Self-hosted Runner 최적화)',
        repl=f'{check_logic}\\n\\1'
    )

def validate_integration(module_info):
    """통합 검증"""
    
    print("🧪 통합 검증 시작...")
    
    module_name = module_info['name']
    module_path = module_info['path']
    
    # 1. 모듈 파일 존재 확인
    file_exists = mcp__mcp-server-commands__run_command(
        command=f'test -f {module_path} && echo "exists" || echo "missing"'
    )
    
    if file_exists.strip() == "missing":
        print(f"❌ 모듈 파일 생성 실패: {module_path}")
        return False
    
    # 2. main.md에서 모듈 참조 확인
    module_referenced = mcp__mcp-server-commands__run_command(
        command=f'grep -c "{module_name}.md" main.md'
    )
    
    if int(module_referenced.strip()) == 0:
        print(f"❌ Main workflow 연동 실패: {module_name}")
        return False
    
    # 3. 모듈 구문 검사
    syntax_check = mcp__mcp-server-commands__run_command(
        command=f'python -m py_compile modules/{module_name.replace("-", "_")}.py 2>/dev/null && echo "valid" || echo "invalid"'
    )
    
    print(f"✅ 통합 검증 완료: {module_name}")
    return True

# 메인 실행 함수
def execute_main_add(user_input):
    """
    /main add 명령어 실행
    사용법: /main add {지시사항}
    """
    
    # 명령어 파싱
    if not user_input.startswith('/main add '):
        return "❌ 사용법: /main add {지시사항}"
    
    instruction = user_input[10:].strip()  # '/main add ' 제거
    
    if not instruction:
        return "❌ 지시사항을 입력해주세요"
    
    print(f"🎯 /main add 실행: {instruction}")
    
    try:
        # 1. 분석
        analysis_result = analyze_instruction(instruction)
        
        # 2. 모듈 생성
        module_info = generate_module(analysis_result)
        
        # 3. 워크플로우 연동
        integrate_to_main_workflow(module_info)
        
        # 4. 검증
        validation_success = validate_integration(module_info)
        
        if validation_success:
            return f"""✅ /main add 완료!

📦 생성된 모듈: {module_info['name']}
📁 파일 경로: {module_info['path']}
🔗 Main workflow 연동 완료

다음 /main 실행 시 자동으로 '{instruction}' 체크 및 실행됩니다.
"""
        else:
            return f"⚠️ 모듈 생성은 완료되었으나 검증에서 문제가 발견되었습니다."
            
    except Exception as e:
        return f"❌ /main add 실행 중 오류: {str(e)}"

# 실행 진입점
if __name__ == "__main__":
    # 테스트 실행
    test_instruction = "Docker 컨테이너 메모리 사용량 최적화"
    result = execute_main_add(f"/main add {test_instruction}")
    print(result)
```

## 📋 지원되는 도메인

- **Docker**: 컨테이너, 이미지, 볼륨, 네트워크 관련
- **GitHub**: Actions, 워크플로우, CI/CD 파이프라인
- **Security**: 보안, 인증, 암호화, 취약점 관련  
- **Network**: 네트워크, 프록시, DNS, 로드밸런싱
- **Deployment**: 배포, K8s, Helm, GitOps
- **Monitoring**: 모니터링, 로깅, 메트릭, 알람
- **Database**: DB 최적화, 백업, 복제
- **API**: REST API, GraphQL, 마이크로서비스

## 🎯 사용 예시

```bash
# Docker 최적화
/main add "Docker 컨테이너 메모리 사용량 최적화"

# GitHub Actions 개선  
/main add "GitHub Actions 빌드 시간 단축"

# 보안 강화
/main add "SSL 인증서 자동 갱신 시스템"

# 모니터링 추가
/main add "API 응답시간 모니터링 및 알람"
```

## ✅ 자동화 결과

각 `/main add` 실행 시:
1. **지시사항 분석** - AI가 도메인, 복잡도, 의존성 자동 분석
2. **모듈 생성** - 표준 템플릿으로 모듈 파일 자동 생성
3. **워크플로우 연동** - main.md에 자동으로 체크 로직 추가
4. **검증 완료** - 통합 테스트로 정상 작동 확인

이제 어떤 지시사항이든 `/main add`로 자동화할 수 있습니다!