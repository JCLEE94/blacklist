#!/usr/bin/env python3
import subprocess
import os
import sys

def run_command(cmd, description):
    """명령어 실행 및 결과 출력"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, cwd="/home/jclee/app/blacklist", 
                              capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 오류 발생: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def main():
    """Git 작업 실행"""
    print("🚀 Git 커밋 및 푸시 작업 시작")
    
    # 현재 상태 확인
    if not run_command("git status --porcelain", "Git 상태 확인"):
        return False
    
    # 변경사항 스테이징
    if not run_command("git add .", "변경사항 스테이징"):
        return False
    
    # 커밋 생성
    if not run_command("git commit -F commit_message.txt", "커밋 생성"):
        return False
    
    # 원격 저장소로 푸시
    if not run_command("git push origin main", "origin/main으로 푸시"):
        return False
    
    print("\n✅ Git 작업 성공적으로 완료!")
    print("\n🔄 CI/CD 파이프라인 자동 트리거:")
    print("   1. 📦 Docker 이미지 빌드")
    print("   2. 🚢 registry.jclee.me 이미지 푸시")
    print("   3. ⚙️ Helm 차트 버전 업데이트")
    print("   4. 🔄 ArgoCD GitOps 자동 싱크")
    
    # 임시 파일 정리
    cleanup_files = ["commit_message.txt", "git_commit_and_push.sh", "execute_git.py"]
    for file in cleanup_files:
        if os.path.exists(file):
            os.remove(file)
            
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)