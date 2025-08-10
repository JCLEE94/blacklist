#!/usr/bin/env python3
"""
NodePort Manager - 프로젝트별 NodePort 할당 관리자
Git 레포지토리 이름의 해시를 기반으로 고유한 NodePort 번호를 할당합니다.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime


class NodePortManager:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config_file = self.project_root / ".nodeport-current.json"
        self.nodeport_range = (30000, 32767)  # Kubernetes NodePort 범위
        
    def get_repo_name(self):
        """Git 레포지토리 이름을 가져옵니다."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # https://github.com/user/repo.git 또는 git@github.com:user/repo.git 형식
                repo_name = url.split('/')[-1].replace('.git', '')
                return repo_name
        except Exception:
            pass
        
        # Fallback: 현재 디렉토리 이름 사용
        return self.project_root.name
    
    def calculate_nodeport(self, repo_name):
        """레포지토리 이름의 해시를 기반으로 NodePort를 계산합니다."""
        # SHA-256 해시 생성
        hash_obj = hashlib.sha256(repo_name.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # 해시의 첫 8자리를 정수로 변환
        hash_int = int(hash_hex[:8], 16)
        
        # NodePort 범위 내의 포트 번호 생성
        port_range = self.nodeport_range[1] - self.nodeport_range[0]
        nodeport = self.nodeport_range[0] + (hash_int % port_range)
        
        return nodeport
    
    def allocate_nodeport(self):
        """NodePort를 할당하고 결과를 저장합니다."""
        repo_name = self.get_repo_name()
        primary_port = self.calculate_nodeport(repo_name)
        
        # 추가 서비스용 포트들 (MSA용)
        additional_ports = {
            'api-gateway': primary_port + 1,
            'collection-service': primary_port + 2,
            'analytics-service': primary_port + 3,
            'blacklist-service': primary_port + 4,
        }
        
        # 포트 범위 검증
        max_port = max([primary_port] + list(additional_ports.values()))
        if max_port > self.nodeport_range[1]:
            print(f"경고: 계산된 포트 {max_port}가 범위를 초과합니다.", file=sys.stderr)
        
        allocation_result = {
            'project_name': repo_name,
            'primary_nodeport': primary_port,
            'additional_ports': additional_ports,
            'allocation_method': 'hash-based',
            'hash_source': f"SHA-256 of '{repo_name}'",
            'allocated_at': datetime.now().isoformat(),
            'port_range': {
                'min': self.nodeport_range[0],
                'max': self.nodeport_range[1]
            }
        }
        
        # 결과 저장
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(allocation_result, f, indent=2, ensure_ascii=False)
        
        return allocation_result
    
    def get_current_allocation(self):
        """현재 할당된 NodePort 정보를 반환합니다."""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def display_allocation(self, allocation):
        """할당 결과를 표시합니다."""
        print(f"🔧 NodePort 할당 결과")
        print(f"프로젝트: {allocation['project_name']}")
        print(f"기본 NodePort: {allocation['primary_nodeport']}")
        print(f"추가 서비스 포트:")
        for service, port in allocation['additional_ports'].items():
            print(f"  - {service}: {port}")
        print(f"할당 시간: {allocation['allocated_at']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NodePort 할당 관리자")
    parser.add_argument('--allocate', action='store_true', 
                       help='새로운 NodePort를 할당합니다')
    parser.add_argument('--show', action='store_true',
                       help='현재 할당된 NodePort를 표시합니다')
    parser.add_argument('--project-root', type=str,
                       help='프로젝트 루트 디렉토리 경로')
    
    args = parser.parse_args()
    
    manager = NodePortManager(args.project_root)
    
    if args.allocate:
        allocation = manager.allocate_nodeport()
        manager.display_allocation(allocation)
        print(f"✅ NodePort 할당 완료: {manager.config_file}")
    elif args.show:
        allocation = manager.get_current_allocation()
        if allocation:
            manager.display_allocation(allocation)
        else:
            print("❌ 할당된 NodePort가 없습니다. --allocate를 사용하여 할당하세요.")
    else:
        # 기본 동작: 할당 후 표시
        allocation = manager.allocate_nodeport()
        manager.display_allocation(allocation)


if __name__ == "__main__":
    main()