"""
자동 백업 및 롤백 관리자

AI 자동화 플랫폼의 중요한 변경사항에 대한 자동 백업 생성 및
롤백 기능을 제공합니다.
"""

import json
import logging
import shutil
import sqlite3
import subprocess
import tarfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.utils.structured_logging import get_logger
except ImportError:

    def get_logger(name):
        return logging.getLogger(name)


logger = get_logger(__name__)


class BackupType(Enum):
    """백업 유형"""

    GIT_CHECKPOINT = "git_checkpoint"
    DATABASE_SNAPSHOT = "database_snapshot"
    CONFIG_BACKUP = "config_backup"
    FULL_SYSTEM = "full_system"
    AUTOMATION_STATE = "automation_state"


class BackupStatus(Enum):
    """백업 상태"""

    CREATED = "created"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    RESTORED = "restored"
    EXPIRED = "expired"


@dataclass
class BackupRecord:
    """백업 레코드"""

    backup_id: str
    backup_type: BackupType
    timestamp: datetime
    file_path: str
    description: str
    size_bytes: int
    checksum: str
    metadata: Dict[str, Any]
    status: BackupStatus = BackupStatus.CREATED
    expiry_date: Optional[datetime] = None


class AutomationBackupManager:
    """자동화 백업 관리자"""

    def __init__(self, backup_root: str = "/tmp/blacklist_backups"):
        self.logger = get_logger(self.__class__.__name__)
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.records_file = self.backup_root / "backup_records.json"
        self.max_backups_per_type = 10
        self.retention_days = 7

        self._load_records()

    def _load_records(self):
        """백업 레코드 로드"""
        try:
            if self.records_file.exists():
                with open(self.records_file, "r") as f:
                    data = json.load(f)
                    self.backup_records = [
                        BackupRecord(
                            backup_id=r["backup_id"],
                            backup_type=BackupType(r["backup_type"]),
                            timestamp=datetime.fromisoformat(r["timestamp"]),
                            file_path=r["file_path"],
                            description=r["description"],
                            size_bytes=r["size_bytes"],
                            checksum=r["checksum"],
                            metadata=r["metadata"],
                            status=BackupStatus(r["status"]),
                            expiry_date=(
                                datetime.fromisoformat(r["expiry_date"])
                                if r.get("expiry_date")
                                else None
                            ),
                        )
                        for r in data
                    ]
            else:
                self.backup_records = []
        except Exception as e:
            self.logger.error(f"백업 레코드 로드 실패: {e}")
            self.backup_records = []

    def _save_records(self):
        """백업 레코드 저장"""
        try:
            data = []
            for record in self.backup_records:
                record_dict = asdict(record)
                record_dict["backup_type"] = record.backup_type.value
                record_dict["status"] = record.status.value
                record_dict["timestamp"] = record.timestamp.isoformat()
                if record.expiry_date:
                    record_dict["expiry_date"] = record.expiry_date.isoformat()
                data.append(record_dict)

            with open(self.records_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"백업 레코드 저장 실패: {e}")

    def create_backup(
        self,
        backup_type: BackupType,
        description: str,
        source_paths: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[BackupRecord]:
        """백업 생성"""
        try:
            backup_id = (
                f"{backup_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            backup_file = self.backup_root / f"{backup_id}.tar.gz"

            metadata = metadata or {}
            metadata.update(
                {
                    "created_by": "automation_system",
                    "git_commit": self._get_current_git_commit(),
                    "system_info": self._get_system_info(),
                }
            )

            # 백업 유형별 처리
            if backup_type == BackupType.GIT_CHECKPOINT:
                success, size = self._create_git_backup(backup_file)

            elif backup_type == BackupType.DATABASE_SNAPSHOT:
                success, size = self._create_database_backup(backup_file)

            elif backup_type == BackupType.CONFIG_BACKUP:
                success, size = self._create_config_backup(backup_file, source_paths)

            elif backup_type == BackupType.FULL_SYSTEM:
                success, size = self._create_full_system_backup(backup_file)

            elif backup_type == BackupType.AUTOMATION_STATE:
                success, size = self._create_automation_state_backup(
                    backup_file, metadata
                )

            else:
                self.logger.error(f"지원하지 않는 백업 유형: {backup_type}")
                return None

            if not success:
                return None

            # 체크섬 계산
            checksum = self._calculate_checksum(backup_file)

            # 백업 레코드 생성
            backup_record = BackupRecord(
                backup_id=backup_id,
                backup_type=backup_type,
                timestamp=datetime.now(),
                file_path=str(backup_file),
                description=description,
                size_bytes=size,
                checksum=checksum,
                metadata=metadata,
                status=BackupStatus.CREATED,
                expiry_date=datetime.now() + timedelta(days=self.retention_days),
            )

            # 백업 검증
            if self._verify_backup(backup_record):
                backup_record.status = BackupStatus.VERIFIED
                self.backup_records.append(backup_record)
                self._save_records()

                # 오래된 백업 정리
                self._cleanup_old_backups(backup_type)

                self.logger.info(f"백업 생성 완료: {backup_id} ({size} bytes)")
                return backup_record
            else:
                self.logger.error(f"백업 검증 실패: {backup_id}")
                if backup_file.exists():
                    backup_file.unlink()
                return None

        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None

    def _create_git_backup(self, backup_file: Path) -> Tuple[bool, int]:
        """Git 상태 백업"""
        try:
            temp_dir = self.backup_root / "temp_git"
            temp_dir.mkdir(exist_ok=True)

            # Git 상태 정보 수집
            git_status = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            ).stdout

            git_diff = subprocess.run(
                ["git", "diff", "HEAD"], capture_output=True, text=True
            ).stdout

            git_log = subprocess.run(
                ["git", "log", "--oneline", "-10"], capture_output=True, text=True
            ).stdout

            # 백업 데이터 생성
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "git_status": git_status,
                "git_diff": git_diff,
                "git_log": git_log,
                "branch": subprocess.run(
                    ["git", "branch", "--show-current"], capture_output=True, text=True
                ).stdout.strip(),
            }

            # JSON 파일로 저장 후 압축
            json_file = temp_dir / "git_backup.json"
            with open(json_file, "w") as f:
                json.dump(backup_data, f, indent=2)

            # TAR 압축
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(json_file, arcname="git_backup.json")

            # 임시 파일 정리
            shutil.rmtree(temp_dir)

            return True, backup_file.stat().st_size

        except Exception as e:
            self.logger.error(f"Git 백업 생성 실패: {e}")
            return False, 0

    def _create_database_backup(self, backup_file: Path) -> Tuple[bool, int]:
        """데이터베이스 백업"""
        try:
            temp_dir = self.backup_root / "temp_db"
            temp_dir.mkdir(exist_ok=True)

            # SQLite 데이터베이스 찾기
            db_files = []
            for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
                db_files.extend(Path(".").glob(f"**/{pattern}"))

            if not db_files:
                self.logger.warning("백업할 데이터베이스 파일을 찾을 수 없습니다.")
                return False, 0

            # 데이터베이스 백업
            backup_count = 0
            with tarfile.open(backup_file, "w:gz") as tar:
                for db_file in db_files:
                    if db_file.exists() and db_file.stat().st_size > 0:
                        # 데이터베이스 무결성 검사
                        try:
                            conn = sqlite3.connect(db_file)
                            conn.execute("PRAGMA integrity_check")
                            conn.close()

                            # 백업에 추가
                            tar.add(
                                db_file, arcname=f"db_{backup_count}_{db_file.name}"
                            )
                            backup_count += 1
                            self.logger.info(f"데이터베이스 백업 추가: {db_file}")

                        except Exception as e:
                            self.logger.warning(f"데이터베이스 검증 실패: {db_file} - {e}")

            shutil.rmtree(temp_dir, ignore_errors=True)

            if backup_count > 0:
                return True, backup_file.stat().st_size
            else:
                return False, 0

        except Exception as e:
            self.logger.error(f"데이터베이스 백업 실패: {e}")
            return False, 0

    def _create_config_backup(
        self, backup_file: Path, source_paths: List[str]
    ) -> Tuple[bool, int]:
        """설정 파일 백업"""
        try:
            default_config_paths = [
                ".env",
                ".env.example",
                "config/",
                "docker-compose.yml",
                "Dockerfile",
                "requirements.txt",
                "pyproject.toml",
                "pytest.ini",
                ".flake8",
                ".gitignore",
            ]

            paths_to_backup = source_paths or default_config_paths
            backup_count = 0

            with tarfile.open(backup_file, "w:gz") as tar:
                for path_str in paths_to_backup:
                    path = Path(path_str)
                    if path.exists():
                        if path.is_file():
                            tar.add(path, arcname=path.name)
                            backup_count += 1
                        elif path.is_dir():
                            # 디렉토리 내 설정 파일들 추가
                            for file_path in path.rglob("*"):
                                if (
                                    file_path.is_file()
                                    and not file_path.name.startswith(".")
                                ):
                                    rel_path = file_path.relative_to(path.parent)
                                    tar.add(file_path, arcname=str(rel_path))
                                    backup_count += 1

            if backup_count > 0:
                self.logger.info(f"설정 파일 {backup_count}개 백업 완료")
                return True, backup_file.stat().st_size
            else:
                return False, 0

        except Exception as e:
            self.logger.error(f"설정 파일 백업 실패: {e}")
            return False, 0

    def _create_full_system_backup(self, backup_file: Path) -> Tuple[bool, int]:
        """전체 시스템 백업 (위험한 변경 전)"""
        try:
            important_paths = [
                "src/",
                "tests/",
                "config/",
                "templates/",
                "static/",
                "requirements.txt",
                "pyproject.toml",
                "pytest.ini",
                ".env.example",
                "docker-compose.yml",
                "Dockerfile",
            ]

            backup_count = 0
            with tarfile.open(backup_file, "w:gz") as tar:
                for path_str in important_paths:
                    path = Path(path_str)
                    if path.exists():
                        tar.add(path, arcname=path.name)
                        backup_count += 1

                        if path.is_dir():
                            # 파일 개수 계산 (디렉토리용)
                            file_count = len(list(path.rglob("*")))
                            self.logger.info(f"디렉토리 백업: {path} ({file_count}개 파일)")
                        else:
                            self.logger.info(f"파일 백업: {path}")

            if backup_count > 0:
                return True, backup_file.stat().st_size
            else:
                return False, 0

        except Exception as e:
            self.logger.error(f"전체 시스템 백업 실패: {e}")
            return False, 0

    def _create_automation_state_backup(
        self, backup_file: Path, metadata: Dict[str, Any]
    ) -> Tuple[bool, int]:
        """자동화 상태 백업"""
        try:
            temp_dir = self.backup_root / "temp_automation"
            temp_dir.mkdir(exist_ok=True)

            # 자동화 상태 정보 수집
            automation_state = {
                "timestamp": datetime.now().isoformat(),
                "git_changes_count": self._get_git_changes_count(),
                "test_coverage": self._get_test_coverage(),
                "automation_progress": metadata.get("automation_progress", 0),
                "current_step": metadata.get("current_step", "unknown"),
                "system_metrics": {
                    "memory_usage": self._get_memory_usage(),
                    "disk_usage": self._get_disk_usage(),
                    "process_count": self._get_process_count(),
                },
                "backup_records": [
                    asdict(r) for r in self.backup_records[-5:]
                ],  # 최근 5개만
                "metadata": metadata,
            }

            # JSON 파일로 저장
            state_file = temp_dir / "automation_state.json"
            with open(state_file, "w") as f:
                json.dump(automation_state, f, indent=2, default=str)

            # 압축
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(state_file, arcname="automation_state.json")

            # 정리
            shutil.rmtree(temp_dir)

            return True, backup_file.stat().st_size

        except Exception as e:
            self.logger.error(f"자동화 상태 백업 실패: {e}")
            return False, 0

    def restore_backup(
        self, backup_id: str, restore_path: Optional[str] = None
    ) -> bool:
        """백업 복원"""
        try:
            # 백업 레코드 찾기
            backup_record = None
            for record in self.backup_records:
                if record.backup_id == backup_id:
                    backup_record = record
                    break

            if not backup_record:
                self.logger.error(f"백업 레코드를 찾을 수 없습니다: {backup_id}")
                return False

            backup_file = Path(backup_record.file_path)
            if not backup_file.exists():
                self.logger.error(f"백업 파일이 존재하지 않습니다: {backup_file}")
                backup_record.status = BackupStatus.CORRUPTED
                self._save_records()
                return False

            # 백업 검증
            if not self._verify_backup(backup_record):
                self.logger.error(f"백업 파일이 손상되었습니다: {backup_id}")
                return False

            # 복원 경로 결정
            if restore_path is None:
                restore_path = (
                    f"restore_{backup_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

            restore_dir = self.backup_root / restore_path
            restore_dir.mkdir(parents=True, exist_ok=True)

            # 백업 파일 압축 해제 (보안: 파일 경로 검증)
            with tarfile.open(backup_file, "r:gz") as tar:
                # Security: Validate tar members to prevent directory traversal
                safe_members = []
                for member in tar.getmembers():
                    # Ensure the member path doesn't escape the restore directory
                    if not (
                        member.name.startswith("..") or member.name.startswith("/")
                    ):
                        safe_members.append(member)
                tar.extractall(restore_dir, members=safe_members)

            self.logger.info(f"백업 복원 완료: {backup_id} -> {restore_dir}")

            # 상태 업데이트
            backup_record.status = BackupStatus.RESTORED
            backup_record.metadata["restored_at"] = datetime.now().isoformat()
            backup_record.metadata["restore_path"] = str(restore_dir)
            self._save_records()

            return True

        except Exception as e:
            self.logger.error(f"백업 복원 실패: {e}")
            return False

    def rollback_to_backup(
        self, backup_id: str, target_paths: List[str] = None
    ) -> bool:
        """백업으로 롤백 (실제 파일 복원)"""
        try:
            self.logger.warning(f"롤백 시작: {backup_id}")

            # 현재 상태 백업 (롤백 전 안전 장치)
            rollback_backup = self.create_backup(
                BackupType.AUTOMATION_STATE,
                f"롤백 전 상태 백업 (대상: {backup_id})",
                metadata={
                    "rollback_target": backup_id,
                    "rollback_timestamp": datetime.now().isoformat(),
                },
            )

            if not rollback_backup:
                self.logger.error("롤백 전 백업 생성 실패 - 롤백 중단")
                return False

            # 백업 복원
            if not self.restore_backup(backup_id, f"rollback_temp_{backup_id}"):
                return False

            # 실제 파일 복원 로직은 백업 유형에 따라 다름
            backup_record = next(
                (r for r in self.backup_records if r.backup_id == backup_id), None
            )
            if not backup_record:
                return False

            if backup_record.backup_type == BackupType.GIT_CHECKPOINT:
                success = self._rollback_git_state(backup_id)
            elif backup_record.backup_type == BackupType.CONFIG_BACKUP:
                success = self._rollback_config_files(backup_id, target_paths)
            else:
                self.logger.warning(f"롤백이 지원되지 않는 백업 유형: {backup_record.backup_type}")
                success = False

            if success:
                self.logger.info(f"롤백 완료: {backup_id}")
            else:
                self.logger.error(f"롤백 실패: {backup_id}")

            return success

        except Exception as e:
            self.logger.error(f"롤백 처리 실패: {e}")
            return False

    def _rollback_git_state(self, backup_id: str) -> bool:
        """Git 상태 롤백"""
        try:
            restore_dir = self.backup_root / f"rollback_temp_{backup_id}"
            git_backup_file = restore_dir / "git_backup.json"

            if not git_backup_file.exists():
                return False

            with open(git_backup_file, "r") as f:
                git_data = json.load(f)

            # Git 상태 정보 출력 (실제 롤백은 수동 검토 필요)
            self.logger.info("Git 롤백 정보:")
            self.logger.info(f"브랜치: {git_data.get('branch')}")
            self.logger.info(f"변경사항:\n{git_data.get('git_status', 'None')}")

            # 자동 롤백은 위험하므로 정보만 제공
            self.logger.warning("Git 자동 롤백은 지원하지 않습니다. 수동으로 처리해주세요.")

            return True

        except Exception as e:
            self.logger.error(f"Git 상태 롤백 실패: {e}")
            return False

    def _rollback_config_files(self, backup_id: str, target_paths: List[str]) -> bool:
        """설정 파일 롤백"""
        try:
            restore_dir = self.backup_root / f"rollback_temp_{backup_id}"

            if not restore_dir.exists():
                return False

            # 복원할 파일 목록
            files_to_restore = target_paths or []
            if not files_to_restore:
                # 기본적으로 모든 백업된 파일
                files_to_restore = [
                    f.name for f in restore_dir.iterdir() if f.is_file()
                ]

            restored_count = 0
            for file_name in files_to_restore:
                source_file = restore_dir / file_name
                target_file = Path(file_name)

                if source_file.exists():
                    try:
                        # 백업 후 복원
                        if target_file.exists():
                            backup_path = target_file.with_suffix(
                                target_file.suffix + ".rollback_backup"
                            )
                            shutil.copy2(target_file, backup_path)

                        shutil.copy2(source_file, target_file)
                        restored_count += 1
                        self.logger.info(f"파일 복원: {file_name}")

                    except Exception as e:
                        self.logger.error(f"파일 복원 실패: {file_name} - {e}")

            self.logger.info(f"설정 파일 롤백 완료: {restored_count}개 파일")
            return restored_count > 0

        except Exception as e:
            self.logger.error(f"설정 파일 롤백 실패: {e}")
            return False

    def _verify_backup(self, backup_record: BackupRecord) -> bool:
        """백업 파일 검증"""
        try:
            backup_file = Path(backup_record.file_path)

            if not backup_file.exists():
                return False

            # 파일 크기 검증
            actual_size = backup_file.stat().st_size
            if actual_size != backup_record.size_bytes:
                self.logger.error(
                    f"백업 파일 크기 불일치: 예상 {backup_record.size_bytes}, 실제 {actual_size}"
                )
                return False

            # 체크섬 검증
            actual_checksum = self._calculate_checksum(backup_file)
            if actual_checksum != backup_record.checksum:
                self.logger.error(
                    f"백업 파일 체크섬 불일치: 예상 {backup_record.checksum}, 실제 {actual_checksum}"
                )
                return False

            # TAR 파일 무결성 검사
            try:
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.getnames()  # 목록만 확인
                return True
            except Exception as e:
                self.logger.error(f"백업 파일 구조 검증 실패: {e}")
                return False

        except Exception as e:
            self.logger.error(f"백업 검증 실패: {e}")
            return False

    def _calculate_checksum(self, file_path: Path) -> str:
        """파일 체크섬 계산 (SHA256)"""
        import hashlib

        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _cleanup_old_backups(self, backup_type: BackupType):
        """오래된 백업 정리"""
        try:
            # 같은 타입의 백업들을 시간순 정렬
            type_backups = [
                r for r in self.backup_records if r.backup_type == backup_type
            ]
            type_backups.sort(key=lambda x: x.timestamp, reverse=True)

            # 최대 개수 초과시 오래된 것 삭제
            if len(type_backups) > self.max_backups_per_type:
                for backup_to_remove in type_backups[self.max_backups_per_type :]:
                    self._delete_backup(backup_to_remove.backup_id)

            # 만료된 백업 삭제
            now = datetime.now()
            for backup_record in self.backup_records[:]:  # 복사본으로 순회
                if backup_record.expiry_date and backup_record.expiry_date < now:
                    self._delete_backup(backup_record.backup_id)

        except Exception as e:
            self.logger.error(f"백업 정리 실패: {e}")

    def _delete_backup(self, backup_id: str):
        """백업 삭제"""
        try:
            backup_record = next(
                (r for r in self.backup_records if r.backup_id == backup_id), None
            )
            if backup_record:
                backup_file = Path(backup_record.file_path)
                if backup_file.exists():
                    backup_file.unlink()

                self.backup_records.remove(backup_record)
                self._save_records()

                self.logger.info(f"백업 삭제됨: {backup_id}")

        except Exception as e:
            self.logger.error(f"백업 삭제 실패: {e}")

    def list_backups(self, backup_type: BackupType = None) -> List[BackupRecord]:
        """백업 목록 조회"""
        if backup_type:
            return [r for r in self.backup_records if r.backup_type == backup_type]
        return self.backup_records

    def get_backup_status(self) -> Dict[str, Any]:
        """백업 시스템 상태"""
        total_size = sum(r.size_bytes for r in self.backup_records)
        status_counts = {}
        for status in BackupStatus:
            status_counts[status.value] = len(
                [r for r in self.backup_records if r.status == status]
            )

        type_counts = {}
        for backup_type in BackupType:
            type_counts[backup_type.value] = len(
                [r for r in self.backup_records if r.backup_type == backup_type]
            )

        return {
            "total_backups": len(self.backup_records),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "backup_root": str(self.backup_root),
            "retention_days": self.retention_days,
            "max_backups_per_type": self.max_backups_per_type,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "oldest_backup": (
                min([r.timestamp for r in self.backup_records]).isoformat()
                if self.backup_records
                else None
            ),
            "newest_backup": (
                max([r.timestamp for r in self.backup_records]).isoformat()
                if self.backup_records
                else None
            ),
        }

    # 시스템 정보 수집 유틸리티 메서드들
    def _get_current_git_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"

    def _get_git_changes_count(self) -> int:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return (
                len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
            )
        except:
            return 0

    def _get_test_coverage(self) -> float:
        try:
            coverage_file = Path("coverage.json")
            if coverage_file.exists():
                with open(coverage_file) as f:
                    data = json.load(f)
                    return data.get("totals", {}).get("percent_covered", 0.0)
        except:
            pass
        return 0.0

    def _get_memory_usage(self) -> float:
        try:
            import psutil

            return psutil.virtual_memory().percent
        except:
            return 0.0

    def _get_disk_usage(self) -> float:
        try:
            import psutil

            return psutil.disk_usage(".").percent
        except:
            return 0.0

    def _get_process_count(self) -> int:
        try:
            import psutil

            return len(psutil.pids())
        except:
            return 0

    def _get_system_info(self) -> Dict[str, Any]:
        try:
            import platform

            import psutil

            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage(".").total,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            }
        except Exception:
            return {"platform": "unknown"}


# 싱글톤 인스턴스
_backup_manager = None


def get_backup_manager() -> AutomationBackupManager:
    """백업 관리자 싱글톤 인스턴스 반환"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = AutomationBackupManager()
    return _backup_manager


# 편의 함수들
def create_checkpoint(
    description: str, backup_type: BackupType = BackupType.GIT_CHECKPOINT
) -> Optional[BackupRecord]:
    """체크포인트 생성"""
    return get_backup_manager().create_backup(backup_type, description)


def safe_rollback(backup_id: str) -> bool:
    """안전한 롤백"""
    return get_backup_manager().rollback_to_backup(backup_id)


if __name__ == "__main__":
    # 테스트 실행
    manager = get_backup_manager()

    # Git 백업 테스트
    git_backup = manager.create_backup(BackupType.GIT_CHECKPOINT, "테스트 Git 백업")

    if git_backup:
        print(f"Git 백업 생성: {git_backup.backup_id}")

        # 상태 출력
        status = manager.get_backup_status()
        print(f"백업 시스템 상태: {json.dumps(status, indent=2, default=str)}")
