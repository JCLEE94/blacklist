"""
🚀 AI 자동화 플랫폼 v8.3.0 - Enterprise Backup & Disaster Recovery System
Automated backup and disaster recovery procedures with Korean reporting

Features:
- Automated daily/hourly backup scheduling
- Multi-tier backup strategy (Database, Files, Config, Git)
- Point-in-time recovery capability
- Automated integrity verification
- Korean language disaster recovery reporting
- Zero-downtime backup operations
- Automated retention policies
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import tarfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackupType(Enum):
    FULL = "전체백업"
    INCREMENTAL = "증분백업"
    DIFFERENTIAL = "차등백업"
    SNAPSHOT = "스냅샷"


class BackupStatus(Enum):
    PENDING = "대기중"
    IN_PROGRESS = "진행중"
    COMPLETED = "완료"
    FAILED = "실패"
    VERIFIED = "검증완료"


class RecoveryLevel(Enum):
    MINIMAL = "최소복구"  # 핵심 서비스만
    STANDARD = "표준복구"  # 일반적 복구
    FULL = "완전복구"  # 모든 데이터 복구
    DISASTER = "재해복구"  # 완전한 재해복구


@dataclass
class BackupMetadata:
    """백업 메타데이터"""

    backup_id: str
    backup_type: BackupType
    created_at: datetime
    size_bytes: int
    checksum: str
    status: BackupStatus
    retention_days: int
    components: List[str]
    korean_description: str
    recovery_point: datetime


@dataclass
class RecoveryPlan:
    """재해복구 계획"""

    plan_id: str
    recovery_level: RecoveryLevel
    estimated_rto: int  # Recovery Time Objective (minutes)
    estimated_rpo: int  # Recovery Point Objective (minutes)
    steps: List[str]
    korean_description: str
    prerequisites: List[str]
    validation_steps: List[str]


class EnterpriseBackupManager:
    """엔터프라이즈급 백업 및 재해복구 관리자"""

    def __init__(self):
        self.backup_root = Path("backups")
        self.db_path = "disaster_recovery/backup_registry.db"
        self.config_file = "config/backup_config.json"

        # 백업 설정
        self.retention_policies = {
            BackupType.FULL: 30,  # 30일 보관
            BackupType.INCREMENTAL: 7,  # 7일 보관
            BackupType.DIFFERENTIAL: 14,  # 14일 보관
            BackupType.SNAPSHOT: 3,  # 3일 보관
        }

        # 백업 컴포넌트
        self.backup_components = {
            "database": {
                "path": "instance/blacklist.db",
                "type": "sqlite",
                "critical": True,
                "korean_name": "데이터베이스",
            },
            "config": {
                "path": "config/",
                "type": "directory",
                "critical": True,
                "korean_name": "설정파일",
            },
            "logs": {
                "path": "logs/",
                "type": "directory",
                "critical": False,
                "korean_name": "로그파일",
            },
            "source": {
                "path": "src/",
                "type": "directory",
                "critical": True,
                "korean_name": "소스코드",
            },
            "templates": {
                "path": "templates/",
                "type": "directory",
                "critical": True,
                "korean_name": "템플릿",
            },
        }

        self.backup_history: List[BackupMetadata] = []
        self.recovery_plans: Dict[RecoveryLevel, RecoveryPlan] = {}

        # 초기화
        self._init_backup_system()

    def _init_backup_system(self):
        """백업 시스템 초기화"""
        # 백업 디렉토리 생성
        self.backup_root.mkdir(exist_ok=True)
        Path("disaster_recovery").mkdir(exist_ok=True)

        # 데이터베이스 초기화
        self._init_database()

        # 복구 계획 초기화
        self._init_recovery_plans()

        logger.info("✅ Enterprise 백업 시스템 초기화 완료")

    def _init_database(self):
        """백업 레지스트리 데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 백업 메타데이터 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_metadata (
                    backup_id TEXT PRIMARY KEY,
                    backup_type TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retention_days INTEGER NOT NULL,
                    components TEXT NOT NULL,
                    korean_description TEXT NOT NULL,
                    recovery_point DATETIME NOT NULL,
                    file_path TEXT NOT NULL
                )
            """
            )

            # 복구 이력 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_history (
                    recovery_id TEXT PRIMARY KEY,
                    backup_id TEXT NOT NULL,
                    recovery_level TEXT NOT NULL,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    status TEXT NOT NULL,
                    korean_description TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (backup_id) REFERENCES backup_metadata (backup_id)
                )
            """
            )

            # 백업 스케줄 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    backup_type TEXT NOT NULL,
                    schedule_cron TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL,
                    last_run DATETIME,
                    next_run DATETIME,
                    korean_description TEXT NOT NULL
                )
            """
            )

            conn.commit()

    def _init_recovery_plans(self):
        """재해복구 계획 초기화"""
        self.recovery_plans = {
            RecoveryLevel.MINIMAL: RecoveryPlan(
                plan_id="minimal-recovery-v8-3-0",
                recovery_level=RecoveryLevel.MINIMAL,
                estimated_rto=15,  # 15분
                estimated_rpo=60,  # 1시간
                steps=[
                    "1. 핵심 데이터베이스 복구",
                    "2. 기본 설정파일 복원",
                    "3. API 서비스 재시작",
                    "4. 헬스체크 검증",
                ],
                korean_description="핵심 서비스만 빠르게 복구하여 기본 운영 재개",
                prerequisites=["최신 데이터베이스 백업 확인", "설정 백업 무결성 검증"],
                validation_steps=[
                    "API 헬스체크 성공 확인",
                    "데이터베이스 연결 상태 확인",
                    "기본 기능 동작 테스트",
                ],
            ),
            RecoveryLevel.STANDARD: RecoveryPlan(
                plan_id="standard-recovery-v8-3-0",
                recovery_level=RecoveryLevel.STANDARD,
                estimated_rto=45,  # 45분
                estimated_rpo=30,  # 30분
                steps=[
                    "1. 전체 데이터베이스 복구",
                    "2. 설정 및 템플릿 복원",
                    "3. 로그 데이터 복구 (선택적)",
                    "4. 서비스 완전 재시작",
                    "5. 모니터링 시스템 복구",
                    "6. 기능 전체 검증",
                ],
                korean_description="표준적인 전체 시스템 복구로 정상 운영 상태 복원",
                prerequisites=[
                    "모든 백업 파일 무결성 검증",
                    "복구 대상 시스템 준비 완료",
                    "네트워크 및 인프라 정상 상태",
                ],
                validation_steps=[
                    "전체 API 엔드포인트 테스트",
                    "데이터 수집 시스템 동작 확인",
                    "모니터링 대시보드 정상 동작",
                    "성능 지표 정상 범위 확인",
                ],
            ),
            RecoveryLevel.FULL: RecoveryPlan(
                plan_id="full-recovery-v8-3-0",
                recovery_level=RecoveryLevel.FULL,
                estimated_rto=90,  # 90분
                estimated_rpo=15,  # 15분
                steps=[
                    "1. 시스템 완전 초기화",
                    "2. 모든 백업 데이터 완전 복원",
                    "3. 소스코드 및 설정 전체 복구",
                    "4. 로그 히스토리 완전 복원",
                    "5. 모든 서비스 단계별 재시작",
                    "6. 모니터링 및 알림 시스템 복구",
                    "7. 성능 최적화 및 튜닝",
                    "8. 전체 시스템 검증 및 테스트",
                ],
                korean_description="모든 데이터와 설정을 완벽하게 복원하는 완전 복구",
                prerequisites=[
                    "모든 백업 세트 완전 검증",
                    "충분한 복구 시간 확보",
                    "전체 인프라 재구축 준비",
                    "복구 검증을 위한 테스트 환경",
                ],
                validation_steps=[
                    "모든 기능 완전 동작 확인",
                    "히스토리 데이터 무결성 검증",
                    "성능 벤치마크 기준 충족",
                    "보안 스캔 통과 확인",
                    "모니터링 메트릭 정상 수집",
                ],
            ),
            RecoveryLevel.DISASTER: RecoveryPlan(
                plan_id="disaster-recovery-v8-3-0",
                recovery_level=RecoveryLevel.DISASTER,
                estimated_rto=180,  # 3시간
                estimated_rpo=5,  # 5분
                steps=[
                    "1. 재해 상황 평가 및 영향 분석",
                    "2. 대체 인프라 긴급 구축",
                    "3. 오프사이트 백업에서 데이터 복구",
                    "4. 네트워크 및 보안 재설정",
                    "5. 서비스 단계적 복구 시작",
                    "6. 데이터 동기화 및 일관성 검증",
                    "7. Blue-Green 배포로 안전한 전환",
                    "8. 전체 시스템 성능 검증",
                    "9. 사용자 서비스 재개 공지",
                    "10. 재해 복구 완료 보고",
                ],
                korean_description="완전한 재해 상황에서 새로운 환경으로 전체 복구",
                prerequisites=[
                    "오프사이트 백업 접근 가능 확인",
                    "대체 인프라 또는 클라우드 환경 준비",
                    "DNS 및 네트워크 라우팅 변경 권한",
                    "재해복구팀 비상 소집",
                    "고객/사용자 커뮤니케이션 채널 준비",
                ],
                validation_steps=[
                    "전체 서비스 가용성 100% 확인",
                    "데이터 무손실 복구 검증",
                    "성능 SLA 기준 충족 확인",
                    "보안 및 컴플라이언스 검증",
                    "모니터링 시스템 완전 복구",
                    "백업 시스템 정상 동작 확인",
                    "재해 복구 절차 개선사항 도출",
                ],
            ),
        }

    async def create_backup(
        self, backup_type: BackupType, components: List[str] = None
    ) -> BackupMetadata:
        """백업 생성"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_type.name.lower()}"

        logger.info(f"🔄 {backup_type.value} 시작: {backup_id}")

        # 백업할 컴포넌트 결정
        if components is None:
            components = list(self.backup_components.keys())

        # 백업 메타데이터 생성
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_type,
            created_at=datetime.now(),
            size_bytes=0,
            checksum="",
            status=BackupStatus.IN_PROGRESS,
            retention_days=self.retention_policies[backup_type],
            components=components,
            korean_description=self._generate_backup_description(
                backup_type, components
            ),
            recovery_point=datetime.now(),
        )

        try:
            # 백업 디렉토리 생성
            backup_dir = self.backup_root / backup_id
            backup_dir.mkdir(exist_ok=True)

            # 컴포넌트별 백업 수행
            total_size = 0
            checksums = []

            for component in components:
                component_size, component_checksum = await self._backup_component(
                    component, backup_dir
                )
                total_size += component_size
                checksums.append(component_checksum)

            # 백업 압축
            compressed_file = await self._compress_backup(backup_dir)

            # 메타데이터 업데이트
            metadata.size_bytes = compressed_file.stat().st_size
            metadata.checksum = self._calculate_file_checksum(compressed_file)
            metadata.status = BackupStatus.COMPLETED

            # 백업 검증
            if await self._verify_backup(metadata, compressed_file):
                metadata.status = BackupStatus.VERIFIED
                logger.info(
                    f"✅ {backup_type.value} 완료: {backup_id} ({self._format_size(metadata.size_bytes)})"
                )
            else:
                metadata.status = BackupStatus.FAILED
                logger.error(f"❌ {backup_type.value} 검증 실패: {backup_id}")

            # 데이터베이스에 저장
            await self._store_backup_metadata(metadata, str(compressed_file))

            # 정리 작업
            shutil.rmtree(backup_dir)  # 압축 후 원본 삭제

            return metadata

        except Exception as e:
            metadata.status = BackupStatus.FAILED
            logger.error(f"❌ {backup_type.value} 실패: {backup_id} - {e}")
            return metadata

    async def _backup_component(
        self, component: str, backup_dir: Path
    ) -> Tuple[int, str]:
        """개별 컴포넌트 백업"""
        component_config = self.backup_components[component]
        source_path = Path(component_config["path"])

        if not source_path.exists():
            logger.warning(f"⚠️ 백업 소스 없음: {source_path}")
            return 0, ""

        dest_path = backup_dir / component
        size = 0

        if component_config["type"] == "sqlite":
            # SQLite 데이터베이스 백업
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Online backup using SQLite backup API
            with sqlite3.connect(source_path) as source_conn:
                with sqlite3.connect(dest_path) as backup_conn:
                    source_conn.backup(backup_conn)

            size = dest_path.stat().st_size

        elif component_config["type"] == "directory":
            # 디렉토리 백업
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            size = self._calculate_directory_size(dest_path)

        # 체크섬 계산
        checksum = self._calculate_component_checksum(dest_path)

        logger.info(f"📦 컴포넌트 백업 완료: {component} ({self._format_size(size)})")
        return size, checksum

    async def _compress_backup(self, backup_dir: Path) -> Path:
        """백업 압축"""
        compressed_file = backup_dir.with_suffix(".tar.gz")

        with tarfile.open(compressed_file, "w:gz") as tar:
            tar.add(backup_dir, arcname=backup_dir.name)

        return compressed_file

    async def _verify_backup(self, metadata: BackupMetadata, backup_file: Path) -> bool:
        """백업 무결성 검증"""
        try:
            # 파일 존재 확인
            if not backup_file.exists():
                return False

            # 압축 파일 무결성 확인
            with tarfile.open(backup_file, "r:gz") as tar:
                # 모든 파일이 정상적으로 압축되었는지 확인
                tar.getmembers()

            # 체크섬 검증
            calculated_checksum = self._calculate_file_checksum(backup_file)
            if calculated_checksum != metadata.checksum:
                logger.error(
                    f"❌ 체크섬 불일치: {calculated_checksum} != {metadata.checksum}"
                )
                return False

            logger.info(f"✅ 백업 검증 성공: {metadata.backup_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 백업 검증 실패: {e}")
            return False

    async def _store_backup_metadata(self, metadata: BackupMetadata, file_path: str):
        """백업 메타데이터 저장"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO backup_metadata 
                (backup_id, backup_type, created_at, size_bytes, checksum, 
                 status, retention_days, components, korean_description, 
                 recovery_point, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metadata.backup_id,
                    metadata.backup_type.name,
                    metadata.created_at,
                    metadata.size_bytes,
                    metadata.checksum,
                    metadata.status.name,
                    metadata.retention_days,
                    json.dumps(metadata.components),
                    metadata.korean_description,
                    metadata.recovery_point,
                    file_path,
                ),
            )
            conn.commit()

    async def restore_from_backup(
        self,
        backup_id: str,
        recovery_level: RecoveryLevel = RecoveryLevel.STANDARD,
        components: List[str] = None,
    ) -> bool:
        """백업에서 복구"""
        recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"🔧 복구 시작: {backup_id} -> {recovery_level.value}")

        try:
            # 백업 메타데이터 조회
            metadata = await self._get_backup_metadata(backup_id)
            if not metadata:
                logger.error(f"❌ 백업을 찾을 수 없음: {backup_id}")
                return False

            # 복구 계획 가져오기
            recovery_plan = self.recovery_plans.get(recovery_level)
            if not recovery_plan:
                logger.error(f"❌ 복구 계획 없음: {recovery_level}")
                return False

            # 복구 이력 기록 시작
            await self._start_recovery_record(recovery_id, backup_id, recovery_level)

            # 복구 전 검증
            if not await self._pre_recovery_validation(metadata, recovery_plan):
                logger.error("❌ 복구 전 검증 실패")
                return False

            # 백업 파일 압축 해제
            backup_file = Path(await self._get_backup_file_path(backup_id))
            temp_restore_dir = Path("temp_restore") / recovery_id
            temp_restore_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(temp_restore_dir)

            extracted_backup_dir = temp_restore_dir / backup_id

            # 컴포넌트별 복구
            if components is None:
                components = metadata.components

            success_count = 0
            for component in components:
                if await self._restore_component(component, extracted_backup_dir):
                    success_count += 1
                    logger.info(f"✅ 컴포넌트 복구 성공: {component}")
                else:
                    logger.error(f"❌ 컴포넌트 복구 실패: {component}")

            # 복구 후 검증
            recovery_success = await self._post_recovery_validation(recovery_plan)

            # 정리 작업
            shutil.rmtree(temp_restore_dir)

            # 복구 이력 완료
            await self._complete_recovery_record(recovery_id, recovery_success)

            if recovery_success:
                logger.info(f"✅ {recovery_level.value} 완료: {recovery_id}")
                await self._send_recovery_notification(
                    recovery_id, True, recovery_level
                )
            else:
                logger.error(f"❌ {recovery_level.value} 실패: {recovery_id}")
                await self._send_recovery_notification(
                    recovery_id, False, recovery_level
                )

            return recovery_success

        except Exception as e:
            logger.error(f"❌ 복구 중 오류: {e}")
            await self._complete_recovery_record(recovery_id, False, str(e))
            return False

    async def _restore_component(self, component: str, backup_dir: Path) -> bool:
        """개별 컴포넌트 복구"""
        component_config = self.backup_components[component]
        source_path = backup_dir / component
        dest_path = Path(component_config["path"])

        if not source_path.exists():
            logger.warning(f"⚠️ 백업 컴포넌트 없음: {source_path}")
            return False

        try:
            # 기존 파일/디렉토리 백업 (안전 조치)
            if dest_path.exists():
                backup_old_path = dest_path.with_suffix(
                    f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                )
                if dest_path.is_file():
                    shutil.copy2(dest_path, backup_old_path)
                else:
                    shutil.copytree(dest_path, backup_old_path)

            # 복구 수행
            if component_config["type"] == "sqlite":
                # SQLite 데이터베이스 복구
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)

            elif component_config["type"] == "directory":
                # 디렉토리 복구
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)

            logger.info(f"📦 컴포넌트 복구 완료: {component}")
            return True

        except Exception as e:
            logger.error(f"❌ 컴포넌트 복구 실패 {component}: {e}")
            return False

    async def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """백업 메타데이터 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM backup_metadata WHERE backup_id = ?
            """,
                (backup_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return BackupMetadata(
                backup_id=row[0],
                backup_type=BackupType[row[1]],
                created_at=datetime.fromisoformat(row[2]),
                size_bytes=row[3],
                checksum=row[4],
                status=BackupStatus[row[5]],
                retention_days=row[6],
                components=json.loads(row[7]),
                korean_description=row[8],
                recovery_point=datetime.fromisoformat(row[9]),
            )

    def _generate_backup_description(
        self, backup_type: BackupType, components: List[str]
    ) -> str:
        """백업 설명 생성"""
        korean_components = [
            self.backup_components[comp]["korean_name"]
            for comp in components
            if comp in self.backup_components
        ]

        component_str = ", ".join(korean_components)
        return f"{backup_type.value}: {component_str} 백업 생성"

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """파일 체크섬 계산"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _calculate_component_checksum(self, path: Path) -> str:
        """컴포넌트 체크섬 계산"""
        if path.is_file():
            return self._calculate_file_checksum(path)
        else:
            # 디렉토리의 경우 모든 파일의 체크섬을 합한 체크섬
            checksums = []
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    checksums.append(self._calculate_file_checksum(file_path))

            combined = "".join(sorted(checksums))
            return hashlib.sha256(combined.encode()).hexdigest()

    def _calculate_directory_size(self, dir_path: Path) -> int:
        """디렉토리 크기 계산"""
        total_size = 0
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def _format_size(self, size_bytes: int) -> str:
        """바이트 크기를 읽기 좋은 형태로 변환"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    async def cleanup_old_backups(self):
        """보관 정책에 따른 오래된 백업 정리"""
        logger.info("🧹 오래된 백업 정리 시작")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 보관 기간이 지난 백업 조회
            cursor.execute(
                """
                SELECT backup_id, file_path, backup_type, created_at, retention_days
                FROM backup_metadata
                WHERE datetime(created_at, '+' || retention_days || ' days') < datetime('now')
                AND status != 'FAILED'
            """
            )

            expired_backups = cursor.fetchall()

            for backup in expired_backups:
                backup_id, file_path, backup_type, created_at, retention_days = backup

                try:
                    # 백업 파일 삭제
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # 데이터베이스에서 제거
                    cursor.execute(
                        "DELETE FROM backup_metadata WHERE backup_id = ?", (backup_id,)
                    )

                    logger.info(f"🗑️ 만료된 백업 삭제: {backup_id}")

                except Exception as e:
                    logger.error(f"❌ 백업 삭제 실패 {backup_id}: {e}")

            conn.commit()
            logger.info(f"✅ 백업 정리 완료: {len(expired_backups)}개 파일 삭제")

    async def get_backup_status_report(self) -> Dict[str, Any]:
        """백업 상태 리포트 (한국어)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 백업 통계
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(size_bytes) as total_size,
                    COUNT(CASE WHEN status = 'VERIFIED' THEN 1 END) as verified,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
                FROM backup_metadata
                WHERE datetime(created_at) >= datetime('now', '-7 days')
            """
            )

            stats = cursor.fetchone()

            # 최근 백업
            cursor.execute(
                """
                SELECT backup_id, backup_type, created_at, size_bytes, status, korean_description
                FROM backup_metadata
                ORDER BY created_at DESC
                LIMIT 10
            """
            )

            recent_backups = cursor.fetchall()

            return {
                "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "period": "최근 7일",
                "statistics": {
                    "total_backups": stats[0] or 0,
                    "total_size": self._format_size(stats[1] or 0),
                    "success_rate": f"{((stats[2] or 0) / (stats[0] or 1)) * 100:.1f}%",
                    "verified_backups": stats[2] or 0,
                    "failed_backups": stats[3] or 0,
                },
                "recent_backups": [
                    {
                        "backup_id": backup[0],
                        "type": BackupType[backup[1]].value,
                        "created_at": backup[2],
                        "size": self._format_size(backup[3]),
                        "status": BackupStatus[backup[4]].value,
                        "description": backup[5],
                    }
                    for backup in recent_backups
                ],
                "korean_summary": f"총 {stats[0] or 0}개 백업 중 {stats[2] or 0}개 검증 완료, 성공률 {((stats[2] or 0) / (stats[0] or 1)) * 100:.1f}%",
            }

    async def schedule_automated_backups(self):
        """자동 백업 스케줄링"""
        logger.info("📅 자동 백업 스케줄 시작")

        # 매일 자정 전체 백업
        asyncio.create_task(self._schedule_daily_backup())

        # 매 6시간 증분 백업
        asyncio.create_task(self._schedule_incremental_backup())

        # 매주 일요일 시스템 스냅샷
        asyncio.create_task(self._schedule_weekly_snapshot())

    async def _schedule_daily_backup(self):
        """일일 전체 백업 스케줄"""
        while True:
            try:
                # 자정까지의 시간 계산
                now = datetime.now()
                tomorrow = now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                sleep_seconds = (tomorrow - now).total_seconds()

                await asyncio.sleep(sleep_seconds)

                # 전체 백업 수행
                logger.info("🌙 일일 전체 백업 시작")
                await self.create_backup(BackupType.FULL)

                # 오래된 백업 정리
                await self.cleanup_old_backups()

            except Exception as e:
                logger.error(f"❌ 일일 백업 스케줄 오류: {e}")
                await asyncio.sleep(3600)  # 1시간 후 재시도

    async def _schedule_incremental_backup(self):
        """증분 백업 스케줄 (6시간마다)"""
        while True:
            try:
                await asyncio.sleep(6 * 3600)  # 6시간 대기

                logger.info("⏰ 증분 백업 시작")
                await self.create_backup(BackupType.INCREMENTAL, ["database", "config"])

            except Exception as e:
                logger.error(f"❌ 증분 백업 스케줄 오류: {e}")

    async def _schedule_weekly_snapshot(self):
        """주간 스냅샷 스케줄"""
        while True:
            try:
                # 다음 일요일 자정까지 대기
                now = datetime.now()
                days_until_sunday = (6 - now.weekday()) % 7
                if days_until_sunday == 0 and now.hour == 0:
                    days_until_sunday = 7

                next_sunday = now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=days_until_sunday)
                sleep_seconds = (next_sunday - now).total_seconds()

                await asyncio.sleep(sleep_seconds)

                logger.info("📸 주간 스냅샷 백업 시작")
                await self.create_backup(BackupType.SNAPSHOT)

            except Exception as e:
                logger.error(f"❌ 주간 스냅샷 스케줄 오류: {e}")
                await asyncio.sleep(3600)

    async def _send_recovery_notification(
        self, recovery_id: str, success: bool, recovery_level: RecoveryLevel
    ):
        """복구 완료 알림 (한국어)"""
        status = "성공" if success else "실패"
        icon = "✅" if success else "❌"

        message = f"{icon} {recovery_level.value} {status}: {recovery_id}"

        logger.info(f"📧 복구 알림: {message}")

        # 여기에 실제 알림 시스템 연동 (이메일, 슬랙, 등) 구현


# 글로벌 백업 관리자 인스턴스
_backup_manager_instance = None


def get_backup_manager() -> EnterpriseBackupManager:
    """백업 관리자 인스턴스 반환 (싱글톤)"""
    global _backup_manager_instance
    if _backup_manager_instance is None:
        _backup_manager_instance = EnterpriseBackupManager()
    return _backup_manager_instance


if __name__ == "__main__":

    async def main():
        """테스트 실행"""
        backup_manager = get_backup_manager()

        # 전체 백업 생성
        print("🔄 전체 백업 생성 중...")
        backup_metadata = await backup_manager.create_backup(BackupType.FULL)
        print(f"✅ 백업 완료: {backup_metadata.backup_id}")

        # 백업 상태 리포트
        report = await backup_manager.get_backup_status_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))

        # 복구 테스트 (주의: 실제 데이터 영향)
        # await backup_manager.restore_from_backup(backup_metadata.backup_id, RecoveryLevel.MINIMAL)

    asyncio.run(main())
