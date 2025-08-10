#!/usr/bin/env python3
"""
Git 작업을 단계별로 실행하는 스크립트
"""
import os
import subprocess
import sys

def execute_command(command, description):
    """명령어를 실행하고 결과를 반환"""
    print(f"\n🔄 {description}")
    print(f"실행 명령어: {command}")
    
    try:
        # Working directory를 명시적으로 설정
        result = subprocess.run(
            command, 
            shell=True, 
            cwd="/home/jclee/app/blacklist",
            text=True,
            capture_output=True
        )
        
        if result.stdout:
            print(f"📤 출력:\n{result.stdout}")
        
        if result.stderr:
            print(f"⚠️ 경고/오류:\n{result.stderr}")
            
        if result.returncode == 0:
            print(f"✅ {description} 성공")
            return True
        else:
            print(f"❌ {description} 실패 (코드: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"💥 예외 발생: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 Blacklist 프로젝트 Git 작업 시작")
    print("="*50)
    
    # 1. Git 상태 확인
    if not execute_command("git status --porcelain", "Git 상태 확인"):
        return False
        
    # 2. 모든 변경사항 스테이징
    if not execute_command("git add .", "변경사항 스테이징"):
        return False
    
    # 3. 커밋 생성 (Claude co-author 포함)
    commit_cmd = 'git commit -F commit_message.txt'
    if not execute_command(commit_cmd, "Claude co-author와 함께 커밋 생성"):
        return False
    
    # 4. 원격 저장소로 푸시
    if not execute_command("git push origin main", "GitHub origin/main으로 푸시"):
        return False
    
    print("\n" + "="*60)
    print("🎉 Git 작업 완료!")
    print("="*60)
    
    print("\n🔄 자동 트리거된 CI/CD 파이프라인:")
    print("   1. 📦 GitHub Actions 셀프호스트 러너 시작")
    print("   2. 🏗️ Docker 멀티스테이지 빌드 실행")  
    print("   3. 🚢 registry.jclee.me 이미지 푸시")
    print("   4. 📊 Helm 차트 버전 자동 업데이트")
    print("   5. 🔄 ArgoCD GitOps 자동 동기화")
    print("   6. ⚡ Kubernetes 클러스터 배포")
    
    print(f"\n🌐 모니터링 URL:")
    print(f"   - GitHub Actions: https://github.com/JCLEE94/blacklist/actions")
    print(f"   - ArgoCD 대시보드: https://argo.jclee.me")
    print(f"   - 도커 레지스트리: registry.jclee.me")
    
    # 임시 파일 정리
    temp_files = [
        "commit_message.txt", 
        "git_commit_and_push.sh", 
        "check_git_status.sh",
        "execute_git.py",
        "final_git_operations.py"
    ]
    
    print(f"\n🧹 임시 파일 정리...")
    for file in temp_files:
        file_path = f"/home/jclee/app/blacklist/{file}"
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"   ✅ {file} 삭제")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🚀 CI/CD 파이프라인이 백그라운드에서 실행 중입니다!")
        print("📈 실시간 상태는 GitHub Actions 페이지에서 확인할 수 있습니다.")
        sys.exit(0)
    else:
        print("\n❌ Git 작업 실패")
        sys.exit(1)