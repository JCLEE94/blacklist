#!/usr/bin/env python3
"""
GitHub Actions 워크플로우 검증 스크립트
"""
import yaml
import json
import sys
from collections import defaultdict

def load_workflow(file_path):
    """워크플로우 파일 로드"""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 파일 로드 실패: {e}")
        sys.exit(1)

def validate_job_dependencies(workflow):
    """Job 의존성 검증"""
    jobs = workflow.get('jobs', {})
    errors = []
    warnings = []
    
    # Job 의존성 그래프 생성
    dep_graph = defaultdict(list)
    
    for job_name, job_config in jobs.items():
        needs = job_config.get('needs', [])
        if isinstance(needs, str):
            needs = [needs]
        
        for dep in needs:
            if dep not in jobs:
                errors.append(f"Job '{job_name}'이 존재하지 않는 job '{dep}'에 의존합니다")
            else:
                dep_graph[dep].append(job_name)
    
    # 순환 의존성 검사
    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in dep_graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    visited = set()
    for job in jobs:
        if job not in visited:
            if has_cycle(job, visited, set()):
                errors.append(f"순환 의존성이 감지되었습니다: {job}")
    
    return errors, warnings

def analyze_workflow_flow(workflow):
    """워크플로우 흐름 분석"""
    jobs = workflow.get('jobs', {})
    
    print("\n📊 워크플로우 흐름 분석:")
    print("=" * 50)
    
    # Job 실행 순서 분석
    job_order = []
    processed = set()
    
    # 의존성이 없는 job 찾기
    no_deps = []
    for job_name, job_config in jobs.items():
        if not job_config.get('needs'):
            no_deps.append(job_name)
    
    # 위상 정렬로 실행 순서 결정
    queue = no_deps[:]
    while queue:
        current = queue.pop(0)
        if current not in processed:
            job_order.append(current)
            processed.add(current)
            
            # 이 job에 의존하는 job들 찾기
            for job_name, job_config in jobs.items():
                needs = job_config.get('needs', [])
                if isinstance(needs, str):
                    needs = [needs]
                
                if current in needs and job_name not in processed:
                    # 모든 의존성이 처리되었는지 확인
                    if all(dep in processed for dep in needs):
                        queue.append(job_name)
    
    # 실행 순서 출력
    print("\n🔄 Job 실행 순서:")
    for i, job in enumerate(job_order, 1):
        job_config = jobs[job]
        needs = job_config.get('needs', [])
        if isinstance(needs, str):
            needs = [needs]
        
        deps_str = f" (의존: {', '.join(needs)})" if needs else " (독립 실행)"
        condition = job_config.get('if', '')
        condition_str = f" [조건: {condition}]" if condition else ""
        
        print(f"{i}. {job}{deps_str}{condition_str}")

def check_output_usage(workflow):
    """Job 출력값 사용 검증"""
    jobs = workflow.get('jobs', {})
    outputs_defined = {}
    outputs_used = {}
    
    print("\n📤 Job 출력값 분석:")
    print("=" * 50)
    
    # 출력값 정의 찾기
    for job_name, job_config in jobs.items():
        outputs = job_config.get('outputs', {})
        if outputs:
            outputs_defined[job_name] = list(outputs.keys())
            print(f"\n✅ {job_name} 출력값 정의:")
            for output_name, output_value in outputs.items():
                print(f"   - {output_name}: {output_value}")
    
    # 출력값 사용 찾기
    for job_name, job_config in jobs.items():
        # steps에서 출력값 사용 확인
        for step in job_config.get('steps', []):
            for key, value in step.items():
                if isinstance(value, str) and 'needs.' in value:
                    # needs.job_name.outputs.output_name 패턴 찾기
                    import re
                    matches = re.findall(r'needs\.(\w+)\.outputs\.(\w+)', str(value))
                    for dep_job, output_name in matches:
                        if dep_job not in outputs_used:
                            outputs_used[dep_job] = []
                        outputs_used[dep_job].append((job_name, output_name))
    
    # 사용되지 않는 출력값 찾기
    print("\n⚠️  출력값 사용 검증:")
    for job_name, outputs in outputs_defined.items():
        for output in outputs:
            used = False
            for dep_job, usages in outputs_used.items():
                if dep_job == job_name and any(usage[1] == output for usage in usages):
                    used = True
                    break
            
            if not used:
                print(f"   - {job_name}.{output}는 정의되었지만 사용되지 않습니다")

def validate_artifacts(workflow):
    """아티팩트 업로드/다운로드 검증"""
    jobs = workflow.get('jobs', {})
    artifacts_uploaded = {}
    artifacts_downloaded = {}
    
    print("\n📦 아티팩트 분석:")
    print("=" * 50)
    
    for job_name, job_config in jobs.items():
        for step in job_config.get('steps', []):
            # 아티팩트 업로드 찾기
            if step.get('uses', '').startswith('actions/upload-artifact'):
                artifact_name = step.get('with', {}).get('name', 'unknown')
                artifacts_uploaded[artifact_name] = job_name
                print(f"⬆️  {job_name}에서 '{artifact_name}' 업로드")
            
            # 아티팩트 다운로드 찾기
            if step.get('uses', '').startswith('actions/download-artifact'):
                artifact_name = step.get('with', {}).get('name', 'unknown')
                artifacts_downloaded[artifact_name] = job_name
                print(f"⬇️  {job_name}에서 '{artifact_name}' 다운로드")
    
    # 매칭 검증
    print("\n🔍 아티팩트 매칭 검증:")
    for artifact, downloader in artifacts_downloaded.items():
        if artifact not in artifacts_uploaded:
            print(f"❌ '{artifact}'가 다운로드되지만 업로드되지 않습니다")
        else:
            uploader = artifacts_uploaded[artifact]
            print(f"✅ '{artifact}': {uploader} → {downloader}")

def check_concurrency(workflow):
    """동시 실행 제어 검증"""
    concurrency = workflow.get('concurrency', {})
    
    print("\n🔒 동시 실행 제어:")
    print("=" * 50)
    
    if concurrency:
        print(f"✅ 동시 실행 그룹: {concurrency.get('group')}")
        print(f"✅ 진행 중인 실행 취소: {concurrency.get('cancel-in-progress', False)}")
    else:
        print("⚠️  동시 실행 제어가 설정되지 않았습니다")

def main():
    print("🔍 GitHub Actions 워크플로우 검증")
    print("=" * 50)
    
    workflow_file = '.github/workflows/offline-production-deploy.yml'
    workflow = load_workflow(workflow_file)
    
    # 기본 정보 출력
    print(f"\n📋 워크플로우: {workflow.get('name')}")
    print(f"트리거: {list(workflow.get('on', {}).keys())}")
    
    # Job 의존성 검증
    errors, warnings = validate_job_dependencies(workflow)
    
    if errors:
        print("\n❌ 오류:")
        for error in errors:
            print(f"   - {error}")
    
    if warnings:
        print("\n⚠️  경고:")
        for warning in warnings:
            print(f"   - {warning}")
    
    # 워크플로우 흐름 분석
    analyze_workflow_flow(workflow)
    
    # 출력값 사용 검증
    check_output_usage(workflow)
    
    # 아티팩트 검증
    validate_artifacts(workflow)
    
    # 동시 실행 제어 검증
    check_concurrency(workflow)
    
    # 최종 결과
    print("\n" + "=" * 50)
    if errors:
        print("❌ 검증 실패: 오류를 수정해주세요")
        sys.exit(1)
    else:
        print("✅ 워크플로우 검증 완료!")

if __name__ == "__main__":
    main()