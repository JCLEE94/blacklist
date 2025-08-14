#!/usr/bin/env python3
"""
오프라인 패키지 빌더 - Docker 이미지 관리
"""

import subprocess
import json
from pathlib import Path
from .base import OfflinePackageBase


class DockerManager(OfflinePackageBase):
    """Docker 이미지 관리 클래스"""
    
    def collect_docker_images(self):
        """Docker 이미지 수집"""
        self.log_progress("Collecting Docker images...")
        
        # docker-compose.yml에서 이미지 추출
        images = self._extract_images_from_compose()
        
        # 추가 필수 이미지
        additional_images = [
            "redis:7-alpine",
            "nginx:alpine", 
            "python:3.9-slim",
            "postgres:13-alpine"
        ]
        
        all_images = list(set(images + additional_images))
        
        # 이미지 저장
        for image in all_images:
            self._save_docker_image(image)
        
        # 이미지 목록 저장
        self._save_image_manifest(all_images)
        
        self.log_progress(f"Collected {len(all_images)} Docker images", "docker_images")
    
    def _extract_images_from_compose(self) -> list:
        """docker-compose.yml에서 이미지 목록 추출"""
        compose_file = self.project_root / "docker-compose.yml"
        images = []
        
        if compose_file.exists():
            try:
                import yaml
                with open(compose_file) as f:
                    compose_data = yaml.safe_load(f)
                
                for service_name, service_config in compose_data.get('services', {}).items():
                    if 'image' in service_config:
                        images.append(service_config['image'])
                
            except Exception as e:
                print(f"   ⚠️  Could not parse docker-compose.yml: {e}")
        
        return images
    
    def _save_docker_image(self, image_name: str):
        """Docker 이미지 저장"""
        try:
            # 이미지 pull
            print(f"   📥 Pulling {image_name}...")
            pull_result = subprocess.run(
                ['docker', 'pull', image_name],
                capture_output=True, text=True
            )
            
            if pull_result.returncode != 0:
                print(f"   ❌ Failed to pull {image_name}")
                return
            
            # 이미지를 tar 파일로 저장
            safe_name = image_name.replace('/', '_').replace(':', '_')
            output_file = self.dirs["docker_images"] / f"{safe_name}.tar"
            
            print(f"   💾 Saving {image_name} to {output_file.name}...")
            save_result = subprocess.run(
                ['docker', 'save', '-o', str(output_file), image_name],
                capture_output=True, text=True
            )
            
            if save_result.returncode == 0:
                print(f"   ✓ Saved {image_name}")
            else:
                print(f"   ❌ Failed to save {image_name}")
                
        except Exception as e:
            print(f"   ❌ Error processing {image_name}: {e}")
    
    def _save_image_manifest(self, images: list):
        """이미지 매니페스트 저장"""
        manifest = {
            "images": [],
            "load_script": "#!/bin/bash\n# Load all Docker images\n"
        }
        
        for image in images:
            safe_name = image.replace('/', '_').replace(':', '_')
            tar_file = f"{safe_name}.tar"
            
            manifest["images"].append({
                "name": image,
                "tar_file": tar_file,
                "size_mb": self._get_file_size(self.dirs["docker_images"] / tar_file)
            })
            
            manifest["load_script"] += f"docker load -i docker-images/{tar_file}\n"
        
        # 매니페스트 저장
        manifest_file = self.dirs["docker_images"] / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # 로드 스크립트 저장
        load_script = self.dirs["scripts"] / "load-docker-images.sh"
        with open(load_script, 'w') as f:
            f.write(manifest["load_script"])
        load_script.chmod(0o755)
        
        print(f"   ✓ Image manifest created: {manifest_file}")
    
    def _get_file_size(self, file_path: Path) -> float:
        """파일 크기 (MB) 반환"""
        try:
            return round(file_path.stat().st_size / (1024 * 1024), 2)
        except:
            return 0.0