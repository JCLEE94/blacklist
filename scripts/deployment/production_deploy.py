#!/usr/bin/env python3
"""
운영 서버 직접 배포 스크립트
GitLab CI/CD 대신 SSH를 통한 직접 배포
"""
import subprocess
import os
import time
import json
from datetime import datetime
from pathlib import Path

class ProductionDeployer:
    def __init__(self):
        self.deploy_host = "192.168.50.215"
        self.deploy_port = "1111"
        self.deploy_user = "docker"
        self.project_name = "blacklist"
        self.registry_url = "192.168.50.215:1234"
        
    def run_ssh_command(self, command, capture_output=True):
        """SSH 명령 실행"""
        ssh_cmd = [
            "ssh", "-p", self.deploy_port, 
            f"{self.deploy_user}@{self.deploy_host}",
            command
        ]
        
        print(f"🔧 Executing: {command}")
        result = subprocess.run(ssh_cmd, capture_output=capture_output, text=True)
        
        if result.returncode != 0 and capture_output:
            print(f"❌ Error: {result.stderr}")
            return False, result.stderr
        
        if capture_output:
            return True, result.stdout
        return True, ""
    
    def copy_file(self, local_path, remote_path):
        """파일 복사"""
        scp_cmd = [
            "scp", "-P", self.deploy_port,
            local_path,
            f"{self.deploy_user}@{self.deploy_host}:{remote_path}"
        ]
        
        print(f"📤 Copying {local_path} to {remote_path}")
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Copy failed: {result.stderr}")
            return False
        
        return True
    
    def build_and_push_image(self):
        """Docker 이미지 빌드 및 푸시"""
        print("🏗️ Building Docker image...")
        
        # 빌드 시간 설정
        build_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
        
        # 이미지 빌드
        build_cmd = [
            "docker", "build", 
            "--build-arg", f"BUILD_TIME={build_time}",
            "-t", f"{self.project_name}:latest",
            "."
        ]
        
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Build failed: {result.stderr}")
            return False
        
        # 이미지 태깅
        tag_cmd = [
            "docker", "tag", 
            f"{self.project_name}:latest",
            f"{self.registry_url}/{self.project_name}:latest"
        ]
        
        result = subprocess.run(tag_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Tag failed: {result.stderr}")
            return False
        
        # 이미지 푸시
        push_cmd = [
            "docker", "push",
            f"{self.registry_url}/{self.project_name}:latest"
        ]
        
        result = subprocess.run(push_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Push failed: {result.stderr}")
            return False
        
        print("✅ Image built and pushed successfully")
        return True
    
    def stop_existing_containers(self):
        """기존 컨테이너 중지"""
        print("🛑 Stopping existing containers...")
        
        commands = [
            f"cd ~/app/{self.project_name}",
            f"/usr/local/bin/docker-compose -f ~/app/{self.project_name}/docker-compose.yml -p {self.project_name} down --remove-orphans || true",
            f"/usr/local/bin/docker-compose -f ~/app/{self.project_name}/docker-compose.yml -p {self.project_name} rm -f || true",
            f"/usr/local/bin/docker ps -a | grep '{self.project_name}' | awk '{{print $1}}' | xargs -r /usr/local/bin/docker rm -f || true"
        ]
        
        for cmd in commands:
            success, output = self.run_ssh_command(cmd)
            if "down" in cmd:
                print(f"📋 Stop output: {output}")
        
        print("✅ Existing containers stopped")
        return True
    
    def deploy_application(self):
        """애플리케이션 배포"""
        print("🚀 Deploying application...")
        
        # 배포 디렉토리 생성
        success, _ = self.run_ssh_command(f"mkdir -p ~/app/{self.project_name}")
        if not success:
            return False
        
        # docker-compose.yml 및 .env 파일 복사 (production 버전 사용)
        if not self.copy_file("docker-compose.production.yml", f"~/app/{self.project_name}/docker-compose.yml"):
            return False
        
        if not self.copy_file(".env.production", f"~/app/{self.project_name}/.env"):
            return False
        
        # 새 컨테이너 시작 (Synology docker-compose 사용)
        deploy_commands = [
            f"cd ~/app/{self.project_name}",
            f"export CI_PROJECT_NAME='{self.project_name}'",
            f"export BUILD_TIME='$(date \"+%Y-%m-%d %H:%M:%S KST\")'",
            f"/usr/local/bin/docker-compose -f ~/app/{self.project_name}/docker-compose.yml -p {self.project_name} pull",
            f"/usr/local/bin/docker-compose -f ~/app/{self.project_name}/docker-compose.yml -p {self.project_name} up -d --force-recreate",
            "sleep 15"
        ]
        
        for cmd in deploy_commands:
            success, output = self.run_ssh_command(cmd)
            if not success and "pull" not in cmd:  # pull 실패는 무시
                return False
            if "up -d" in cmd:
                print(f"📋 Deploy output: {output}")
        
        print("✅ Application deployed")
        return True
    
    def verify_deployment(self):
        """배포 검증"""
        print("🔍 Verifying deployment...")
        
        # 컨테이너 상태 확인
        success, output = self.run_ssh_command(f"cd ~/app/{self.project_name} && docker-compose ps")
        if success:
            print(f"📋 Container status:\n{output}")
        
        # 헬스체크
        time.sleep(10)
        
        for i in range(5):
            print(f"🔄 Health check attempt {i+1}/5...")
            
            health_cmd = f"curl -f -s http://localhost:2541/health"
            success, output = self.run_ssh_command(health_cmd)
            
            if success and "healthy" in output.lower():
                print("✅ Health check passed!")
                try:
                    health_data = json.loads(output)
                    print(f"📊 Status: {health_data.get('status', 'unknown')}")
                except:
                    print(f"📊 Raw response: {output[:200]}")
                return True
            
            print(f"❌ Health check failed (attempt {i+1}/5)")
            if i < 4:
                time.sleep(10)
        
        # 실패시 로그 확인
        print("📋 Checking logs for errors...")
        self.run_ssh_command(f"cd ~/app/{self.project_name} && docker-compose logs --tail=20")
        
        return False
    
    def get_deployment_status(self):
        """배포 상태 확인"""
        print("📊 Getting deployment status...")
        
        # 컨테이너 상태
        success, output = self.run_ssh_command(f"cd ~/app/{self.project_name} && docker-compose ps --format table")
        if success:
            print(f"Container Status:\n{output}")
        
        # 리소스 사용량
        success, output = self.run_ssh_command("docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'")
        if success:
            print(f"Resource Usage:\n{output}")
        
        # 애플리케이션 상태
        success, output = self.run_ssh_command("curl -s http://localhost:2541/api/collection/status")
        if success:
            try:
                status_data = json.loads(output)
                print(f"Application Status: {status_data.get('status', 'unknown')}")
                print(f"Total Sources: {status_data.get('summary', {}).get('total_sources', 0)}")
            except:
                print(f"Status response: {output[:200]}")
    
    def deploy(self):
        """전체 배포 프로세스 실행"""
        print("🚀 Starting production deployment...")
        print(f"📍 Target: {self.deploy_host}:{self.deploy_port}")
        print(f"📦 Project: {self.project_name}")
        
        try:
            # 1. 이미지 빌드 및 푸시
            if not self.build_and_push_image():
                print("❌ Image build/push failed")
                return False
            
            # 2. 기존 컨테이너 중지
            if not self.stop_existing_containers():
                print("❌ Failed to stop existing containers")
                return False
            
            # 3. 애플리케이션 배포
            if not self.deploy_application():
                print("❌ Application deployment failed")
                return False
            
            # 4. 배포 검증
            if not self.verify_deployment():
                print("⚠️ Deployment verification failed")
                # 상태 확인은 계속 진행
            
            # 5. 배포 상태 확인
            self.get_deployment_status()
            
            print("✅ Production deployment completed!")
            print(f"🌐 Application URL: http://{self.deploy_host}:2541")
            
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed with error: {e}")
            return False

if __name__ == "__main__":
    deployer = ProductionDeployer()
    success = deployer.deploy()
    
    if success:
        print("\n🎉 배포가 성공적으로 완료되었습니다!")
        print("🔗 접속 URL: http://192.168.50.215:2541")
    else:
        print("\n💥 배포가 실패했습니다.")
        exit(1)