"""
Docker 이미지 관리자

Docker 이미지 내보내기, 로드 스크립트 생성 등을 담당합니다.
"""

import subprocess
import hashlib
from pathlib import Path
from typing import Dict, Any, List


class DockerImageManager:
    """오프라인 패키지용 Docker 이미지 관리자"""
    
    def __init__(self, images_dir: Path):
        self.images_dir = images_dir
        
        # 내보낼 이미지 목록
        self.images_to_export = [
            "registry.jclee.me/blacklist:latest",
            "redis:7-alpine",
            "postgres:15-alpine",
            "nginx:alpine",
            "python:3.10-slim"
        ]
    
    def export_images(self, manifest: Dict[str, Any]):
        """전체 Docker 이미지 내보내기"""
        print("\n🐳 Docker 이미지 내보내기 중...")
        
        exported_images = []
        
        for image in self.images_to_export:
            try:
                result = self._export_single_image(image)
                if result:
                    exported_images.append(result)
            except Exception as e:
                print(f"    ❌ {image} 내보내기 실패: {e}")
        
        # 이미지 정보 저장
        self._save_images_info(exported_images)
        
        # 로드 스크립트 생성
        self._create_load_script(exported_images)
        
        # 매니페스트 업데이트
        manifest["components"]["docker_images"] = {
            "status": "success",
            "images_count": len(exported_images),
            "total_size_mb": sum(img["size_mb"] for img in exported_images),
            "info_file": "docker-images/images-info.json"
        }
    
    def _export_single_image(self, image: str) -> Dict[str, Any]:
        """단일 이미지 내보내기"""
        print(f"  📦 내보내는 중: {image}")
        
        # 이미지명을 파일명으로 변환
        safe_name = image.replace('/', '_').replace(':', '_')
        tar_file = self.images_dir / f"{safe_name}.tar"
        
        # docker save 명령 실행
        save_cmd = ["docker", "save", "-o", str(tar_file), image]
        result = subprocess.run(save_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"    ✅ 저장됨: {tar_file.name}")
            
            # 파일 크기 및 체크섬 계산
            file_size = tar_file.stat().st_size
            
            with open(tar_file, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            return {
                "image": image,
                "file": tar_file.name,
                "size_bytes": file_size,
                "size_mb": round(file_size / 1024 / 1024, 2),
                "sha256": checksum
            }
        else:
            print(f"    ⚠️ 실패: {result.stderr}")
            return None
    
    def _save_images_info(self, exported_images: List[Dict]):
        """이미지 정보 파일 저장"""
        import json
        from datetime import datetime
        
        images_info = {
            "exported_date": datetime.now().isoformat(),
            "docker_version": self._get_docker_version(),
            "total_images": len(exported_images),
            "total_size_mb": sum(img["size_mb"] for img in exported_images),
            "images": exported_images
        }
        
        info_file = self.images_dir / "images-info.json"
        with open(info_file, 'w') as f:
            json.dump(images_info, f, indent=2)
    
    def _create_load_script(self, exported_images: List[Dict]):
        """이미지 로드 스크립트 생성"""
        script_content = f'''#!/bin/bash
# Docker 이미지 로드 스크립트

set -e

IMAGES_DIR="{self.images_dir}"

echo "🐳 Docker 이미지 로드 중..."

'''
        
        for image_info in exported_images:
            script_content += f'''
echo "  📦 로드 중: {image_info['image']}"
docker load -i "$IMAGES_DIR/{image_info['file']}"
'''
        
        script_content += '''
echo "✅ 모든 Docker 이미지 로드 완료"

# 이미지 목록 확인
echo "📋 로드된 이미지 목록:"
docker images
'''
        
        load_script = self.images_dir / "load-docker-images.sh"
        with open(load_script, 'w') as f:
            f.write(script_content)
        
        load_script.chmod(0o755)
    
    def _get_docker_version(self) -> str:
        """사용 중인 Docker 버전 확인"""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
