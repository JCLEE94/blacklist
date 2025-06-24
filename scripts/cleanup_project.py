#!/usr/bin/env python3
"""
프로젝트 정리 스크립트
하드코딩 제거 및 폴더 구조 최적화
"""
import os
import shutil
import glob
from pathlib import Path
from datetime import datetime
import json

class ProjectCleaner:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent
        self.actions_taken = []
        
    def log_action(self, action: str, item: str):
        """작업 로깅"""
        msg = f"{'[DRY RUN] ' if self.dry_run else ''}{action}: {item}"
        print(msg)
        self.actions_taken.append({'action': action, 'item': item, 'timestamp': datetime.now().isoformat()})
    
    def remove_file(self, filepath: Path):
        """파일 삭제"""
        if filepath.exists():
            self.log_action("REMOVE FILE", str(filepath))
            if not self.dry_run:
                filepath.unlink()
    
    def remove_directory(self, dirpath: Path):
        """디렉토리 삭제"""
        if dirpath.exists():
            self.log_action("REMOVE DIR", str(dirpath))
            if not self.dry_run:
                shutil.rmtree(dirpath)
    
    def move_file(self, src: Path, dst: Path):
        """파일 이동"""
        if src.exists():
            self.log_action("MOVE", f"{src} -> {dst}")
            if not self.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
    
    def clean_data_directory(self):
        """데이터 디렉토리 정리"""
        print("\n=== 데이터 디렉토리 정리 ===")
        
        # 중복된 REGTECH 수집 파일 제거 (최신 파일만 유지)
        regtech_files = sorted(glob.glob(str(self.project_root / "data/regtech/regtech_web_blacklist_20250621_*.csv")))
        if len(regtech_files) > 1:
            # 최신 파일 유지
            for file in regtech_files[:-1]:
                self.remove_file(Path(file))
                # JSON 파일도 함께 제거
                json_file = Path(file.replace('.csv', '.json'))
                if json_file.exists():
                    self.remove_file(json_file)
        
        # 빈 디렉토리 제거
        empty_dirs = [
            "data/backups",
            "data/exports", 
            "data/logs",
            "data/secudium",
            "data/blacklist/by_detection_month"
        ]
        for dir_path in empty_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists() and not any(full_path.iterdir()):
                self.remove_directory(full_path)
        
        # 중복 소스 디렉토리 제거
        sources_dir = self.project_root / "data/sources"
        if sources_dir.exists():
            self.remove_directory(sources_dir)
    
    def clean_backups(self):
        """오래된 백업 제거"""
        print("\n=== 백업 정리 ===")
        
        backup_dir = self.project_root / "instance/backups"
        if backup_dir.exists():
            # 2일 이상 된 백업 제거
            for backup_file in backup_dir.glob("*.db"):
                file_age = datetime.now() - datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_age.days > 2:
                    self.remove_file(backup_file)
    
    def organize_tests(self):
        """테스트 파일 정리"""
        print("\n=== 테스트 파일 정리 ===")
        
        test_files = [
            ("scripts/test_apis.py", "tests/test_apis.py"),
            ("scripts/test_improved_regtech.py", "tests/test_improved_regtech.py"),
            ("scripts/integration_test_comprehensive.py", "tests/integration/test_comprehensive.py"),
            ("scripts/deployment/run_integration_tests.py", "tests/run_integration_tests.py")
        ]
        
        for src, dst in test_files:
            src_path = self.project_root / src
            dst_path = self.project_root / dst
            if src_path.exists():
                self.move_file(src_path, dst_path)
    
    def clean_documents(self):
        """문서 디렉토리 정리"""
        print("\n=== 문서 디렉토리 정리 ===")
        
        # 웹사이트 미러 제거
        website_mirrors = [
            "document/regtech/regtech.fsec.or.kr",
            "document/regtech/www.google-analytics.com",
            "document/regtech/www.googletagmanager.com",
            "document/regtech/pagead2.googlesyndication.com",
            "document/secudium/secudium.skinfosec.co.kr"
        ]
        
        for mirror in website_mirrors:
            mirror_path = self.project_root / mirror
            if mirror_path.exists():
                self.remove_directory(mirror_path)
        
        # HAR 파일 백업 후 제거
        har_files = list((self.project_root / "document").rglob("*.har"))
        if har_files:
            backup_dir = self.project_root / "document/har_backup"
            if not self.dry_run:
                backup_dir.mkdir(exist_ok=True)
            
            for har_file in har_files:
                dst = backup_dir / har_file.name
                self.move_file(har_file, dst)
    
    def consolidate_deployment_scripts(self):
        """배포 스크립트 통합"""
        print("\n=== 배포 스크립트 정리 ===")
        
        # 중복 배포 스크립트를 archive로 이동
        archive_dir = self.project_root / "scripts/deployment/archive"
        
        redundant_scripts = [
            "scripts/deployment/native_deploy.sh",
            "scripts/deployment/production_deploy.sh",
            "scripts/deployment/deploy_remote.sh"
        ]
        
        for script in redundant_scripts:
            script_path = self.project_root / script
            if script_path.exists():
                dst = archive_dir / script_path.name
                self.move_file(script_path, dst)
    
    def clean_setup_scripts(self):
        """설정 스크립트 정리"""
        print("\n=== 설정 스크립트 정리 ===")
        
        # 중복 setup 파일 제거
        duplicate_setup = self.project_root / "scripts/setup/setup_database.py"
        if duplicate_setup.exists():
            self.remove_file(duplicate_setup)
        
        # database_options 디렉토리 이동
        db_options = self.project_root / "scripts/setup/database_options"
        if db_options.exists():
            dst = self.project_root / "scripts/archive/database_options"
            self.move_file(db_options, dst)
    
    def create_gitignore_entries(self):
        """gitignore 업데이트"""
        print("\n=== .gitignore 업데이트 ===")
        
        new_entries = [
            "\n# Cleaned up directories",
            "document/har_backup/",
            "scripts/deployment/archive/",
            "scripts/archive/",
            "instance/backups/*.db",
            "data/regtech/logs/",
            "\n# Temporary and duplicate files",
            "*_old.*",
            "*_v2.*",
            "*.bak",
            "*.tmp"
        ]
        
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
            
            entries_to_add = []
            for entry in new_entries:
                if entry not in content:
                    entries_to_add.append(entry)
            
            if entries_to_add:
                self.log_action("UPDATE", ".gitignore")
                if not self.dry_run:
                    with open(gitignore_path, 'a') as f:
                        f.write('\n')
                        f.write('\n'.join(entries_to_add))
    
    def save_cleanup_report(self):
        """정리 보고서 저장"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'actions': self.actions_taken,
            'summary': {
                'files_removed': len([a for a in self.actions_taken if a['action'].startswith('REMOVE FILE')]),
                'dirs_removed': len([a for a in self.actions_taken if a['action'].startswith('REMOVE DIR')]),
                'files_moved': len([a for a in self.actions_taken if a['action'] == 'MOVE'])
            }
        }
        
        report_path = self.project_root / 'cleanup_report.json'
        self.log_action("SAVE REPORT", str(report_path))
        
        if not self.dry_run:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
    
    def run(self):
        """전체 정리 실행"""
        print(f"{'=== DRY RUN MODE ===' if self.dry_run else '=== CLEANUP MODE ==='}")
        print(f"Project root: {self.project_root}")
        
        # 각 정리 작업 실행
        self.clean_data_directory()
        self.clean_backups()
        self.organize_tests()
        self.clean_documents()
        self.consolidate_deployment_scripts()
        self.clean_setup_scripts()
        self.create_gitignore_entries()
        
        # 보고서 저장
        self.save_cleanup_report()
        
        # 요약 출력
        print(f"\n=== 정리 요약 ===")
        print(f"제거할 파일: {len([a for a in self.actions_taken if a['action'].startswith('REMOVE FILE')])}")
        print(f"제거할 디렉토리: {len([a for a in self.actions_taken if a['action'].startswith('REMOVE DIR')])}")
        print(f"이동할 파일: {len([a for a in self.actions_taken if a['action'] == 'MOVE'])}")
        
        if self.dry_run:
            print("\n실제로 정리하려면 --execute 옵션을 사용하세요.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="프로젝트 정리 스크립트")
    parser.add_argument('--execute', action='store_true', help='실제로 정리 작업 수행 (기본값: dry run)')
    
    args = parser.parse_args()
    
    cleaner = ProjectCleaner(dry_run=not args.execute)
    cleaner.run()