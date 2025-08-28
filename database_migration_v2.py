#!/usr/bin/env python3
"""
Database Migration V2: SQLite to PostgreSQL
Advanced migration with schema validation and data integrity checks
"""

import os
import json
import sqlite3
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseMigrationV2:
    """SQLite to PostgreSQL 마이그레이션 시스템"""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"migration_backup_{self.timestamp}")
        self.backup_dir.mkdir(exist_ok=True)

        # SQLite databases
        self.sqlite_dbs = {
            "blacklist": "instance/blacklist.db",
            "api_keys": "instance/api_keys.db",
            "monitoring": "instance/monitoring.db",
        }

        # PostgreSQL configuration
        self.pg_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5433"),
            "database": os.getenv("POSTGRES_DB", "blacklist"),
            "user": os.getenv("POSTGRES_USER", "blacklist"),
            "password": os.getenv("POSTGRES_PASSWORD", "blacklist_password_change_me"),
        }

        self.migration_report = {
            "timestamp": self.timestamp,
            "sqlite_analysis": {},
            "postgresql_setup": {},
            "data_migration": {},
            "validation": {},
            "issues": [],
        }

    def analyze_sqlite_schema(self) -> Dict[str, Any]:
        """SQLite 스키마 분석"""
        print("🔍 SQLite 데이터베이스 스키마 분석 중...")

        schema_analysis = {}

        for db_name, db_path in self.sqlite_dbs.items():
            if not Path(db_path).exists():
                logger.warning(f"데이터베이스 파일 없음: {db_path}")
                continue

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 테이블 목록 조회
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]

                table_info = {}
                for table in tables:
                    # 테이블 스키마
                    cursor.execute(f"PRAGMA table_info({table});")
                    columns = cursor.fetchall()

                    # 행 수 계산
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    row_count = cursor.fetchone()[0]

                    table_info[table] = {
                        "columns": columns,
                        "row_count": row_count,
                        "create_sql": None,
                    }

                    # CREATE 문 조회
                    cursor.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                        (table,),
                    )
                    create_sql = cursor.fetchone()
                    if create_sql:
                        table_info[table]["create_sql"] = create_sql[0]

                schema_analysis[db_name] = {
                    "path": db_path,
                    "tables": table_info,
                    "total_tables": len(tables),
                }

                conn.close()
                print(f"  ✓ {db_name}: {len(tables)}개 테이블 분석 완료")

            except Exception as e:
                logger.error(f"SQLite 분석 실패 ({db_path}): {e}")
                self.migration_report["issues"].append(
                    f"SQLite 분석 오류: {db_path} - {str(e)}"
                )

        self.migration_report["sqlite_analysis"] = schema_analysis
        return schema_analysis

    def generate_postgresql_schema(self, sqlite_analysis: Dict[str, Any]) -> str:
        """PostgreSQL 스키마 생성"""
        print("📝 PostgreSQL 스키마 생성 중...")

        pg_schema_sql = []
        pg_schema_sql.append("-- PostgreSQL Schema for Blacklist System")
        pg_schema_sql.append(f"-- Generated: {datetime.now().isoformat()}")
        pg_schema_sql.append("")

        # 데이터베이스별 스키마 변환
        for db_name, db_info in sqlite_analysis.items():
            pg_schema_sql.append(f"-- === {db_name.upper()} DATABASE TABLES ===")

            for table_name, table_info in db_info["tables"].items():
                if not table_info["create_sql"]:
                    continue

                # SQLite → PostgreSQL 변환
                create_sql = table_info["create_sql"]

                # SQLite 타입을 PostgreSQL 타입으로 변환
                type_mappings = {
                    "INTEGER": "INTEGER",
                    "TEXT": "TEXT",
                    "REAL": "REAL",
                    "BLOB": "BYTEA",
                    "BOOLEAN": "BOOLEAN",
                    "DATETIME": "TIMESTAMP",
                    "TIMESTAMP": "TIMESTAMP",
                }

                pg_create = create_sql
                for sqlite_type, pg_type in type_mappings.items():
                    pg_create = pg_create.replace(sqlite_type, pg_type)

                # AUTOINCREMENT를 SERIAL로 변환
                pg_create = pg_create.replace("AUTOINCREMENT", "")
                pg_create = pg_create.replace(
                    "INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY"
                )

                pg_schema_sql.append(pg_create + ";")
                pg_schema_sql.append("")

        schema_content = "\n".join(pg_schema_sql)

        # 스키마 파일 저장
        schema_file = self.backup_dir / "postgresql_schema.sql"
        with open(schema_file, "w", encoding="utf-8") as f:
            f.write(schema_content)

        print(f"  ✓ PostgreSQL 스키마 생성: {schema_file}")
        return str(schema_file)

    def setup_postgresql(self, schema_file: str) -> bool:
        """PostgreSQL 설정 및 스키마 생성"""
        print("🐘 PostgreSQL 데이터베이스 설정 중...")

        try:
            # PostgreSQL 연결 테스트
            pg_conn_str = f"postgresql://{self.pg_config['user']}:{self.pg_config['password']}@{self.pg_config['host']}:{self.pg_config['port']}/{self.pg_config['database']}"

            # psql 명령어로 스키마 적용
            cmd = ["psql", pg_conn_str, "-f", schema_file]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("  ✓ PostgreSQL 스키마 적용 성공")
                self.migration_report["postgresql_setup"]["status"] = "success"
                self.migration_report["postgresql_setup"]["schema_file"] = schema_file
                return True
            else:
                logger.error(f"PostgreSQL 스키마 적용 실패: {result.stderr}")
                self.migration_report["issues"].append(
                    f"PostgreSQL 스키마 오류: {result.stderr}"
                )
                return False

        except Exception as e:
            logger.error(f"PostgreSQL 설정 실패: {e}")
            self.migration_report["issues"].append(f"PostgreSQL 연결 오류: {str(e)}")
            return False

    def migrate_data(self, sqlite_analysis: Dict[str, Any]) -> bool:
        """데이터 마이그레이션 실행"""
        print("📦 데이터 마이그레이션 실행 중...")

        migration_success = True
        migrated_tables = 0
        total_rows = 0

        try:
            import psycopg2

            # PostgreSQL 연결
            pg_conn = psycopg2.connect(
                host=self.pg_config["host"],
                port=self.pg_config["port"],
                database=self.pg_config["database"],
                user=self.pg_config["user"],
                password=self.pg_config["password"],
            )
            pg_cursor = pg_conn.cursor()

            for db_name, db_info in sqlite_analysis.items():
                sqlite_conn = sqlite3.connect(db_info["path"])
                sqlite_cursor = sqlite_conn.cursor()

                for table_name, table_info in db_info["tables"].items():
                    if table_info["row_count"] == 0:
                        continue

                    try:
                        # SQLite에서 데이터 조회
                        sqlite_cursor.execute(f"SELECT * FROM {table_name};")
                        rows = sqlite_cursor.fetchall()

                        if not rows:
                            continue

                        # PostgreSQL에 데이터 삽입
                        columns = [col[1] for col in table_info["columns"]]
                        placeholders = ",".join(["%s"] * len(columns))

                        insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders});"

                        pg_cursor.executemany(insert_query, rows)
                        pg_conn.commit()

                        migrated_tables += 1
                        total_rows += len(rows)
                        print(f"  ✓ {table_name}: {len(rows)}행 마이그레이션")

                    except Exception as e:
                        logger.error(f"테이블 {table_name} 마이그레이션 실패: {e}")
                        self.migration_report["issues"].append(
                            f"테이블 마이그레이션 오류: {table_name} - {str(e)}"
                        )
                        migration_success = False

                sqlite_conn.close()

            pg_conn.close()

            self.migration_report["data_migration"] = {
                "status": "success" if migration_success else "partial",
                "migrated_tables": migrated_tables,
                "total_rows": total_rows,
            }

            print(f"  ✓ 데이터 마이그레이션 완료: {migrated_tables}개 테이블, {total_rows}행")
            return migration_success

        except ImportError:
            logger.error("psycopg2 패키지가 설치되지 않았습니다. pip install psycopg2-binary")
            self.migration_report["issues"].append("psycopg2 패키지 필요")
            return False
        except Exception as e:
            logger.error(f"데이터 마이그레이션 실패: {e}")
            self.migration_report["issues"].append(f"데이터 마이그레이션 오류: {str(e)}")
            return False

    def validate_migration(self) -> bool:
        """마이그레이션 결과 검증"""
        print("✅ 마이그레이션 결과 검증 중...")

        validation_results = {
            "postgresql_connectivity": False,
            "table_counts": {},
            "data_integrity": True,
        }

        try:
            import psycopg2

            # PostgreSQL 연결 테스트
            pg_conn = psycopg2.connect(
                host=self.pg_config["host"],
                port=self.pg_config["port"],
                database=self.pg_config["database"],
                user=self.pg_config["user"],
                password=self.pg_config["password"],
            )
            pg_cursor = pg_conn.cursor()
            validation_results["postgresql_connectivity"] = True

            # 테이블 수 검증
            for db_name, db_info in self.migration_report["sqlite_analysis"].items():
                for table_name, table_info in db_info["tables"].items():
                    try:
                        pg_cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                        pg_count = pg_cursor.fetchone()[0]
                        sqlite_count = table_info["row_count"]

                        validation_results["table_counts"][table_name] = {
                            "sqlite": sqlite_count,
                            "postgresql": pg_count,
                            "match": sqlite_count == pg_count,
                        }

                        if sqlite_count != pg_count:
                            validation_results["data_integrity"] = False

                    except Exception as e:
                        logger.warning(f"테이블 {table_name} 검증 실패: {e}")

            pg_conn.close()

            self.migration_report["validation"] = validation_results

            # 검증 결과 출력
            all_valid = (
                validation_results["data_integrity"]
                and validation_results["postgresql_connectivity"]
            )

            if all_valid:
                print("  ✅ 모든 검증 통과")
            else:
                print("  ⚠️ 일부 검증 실패")

            return all_valid

        except Exception as e:
            logger.error(f"검증 실패: {e}")
            return False

    def generate_report(self) -> str:
        """마이그레이션 보고서 생성"""
        report_file = self.backup_dir / "migration_report_v2.md"

        report_content = f"""# 🐘 Database Migration V2 Report

## 📅 Migration Details
- **Timestamp**: {self.timestamp}
- **SQLite → PostgreSQL Migration**
- **Backup Location**: {self.backup_dir}

## 📊 SQLite Analysis
"""

        for db_name, db_info in self.migration_report.get(
            "sqlite_analysis", {}
        ).items():
            report_content += f"""
### {db_name.upper()} Database
- **Tables**: {db_info.get('total_tables', 0)}
- **Location**: {db_info.get('path', 'N/A')}
"""
            for table_name, table_info in db_info.get("tables", {}).items():
                report_content += (
                    f"  - `{table_name}`: {table_info.get('row_count', 0)} rows\n"
                )

        report_content += f"""
## 🐘 PostgreSQL Setup
- **Status**: {self.migration_report.get('postgresql_setup', {}).get('status', 'N/A')}
- **Schema File**: {self.migration_report.get('postgresql_setup', {}).get('schema_file', 'N/A')}

## 📦 Data Migration
- **Status**: {self.migration_report.get('data_migration', {}).get('status', 'N/A')}
- **Tables Migrated**: {self.migration_report.get('data_migration', {}).get('migrated_tables', 0)}
- **Total Rows**: {self.migration_report.get('data_migration', {}).get('total_rows', 0)}

## ✅ Validation Results
"""

        validation = self.migration_report.get("validation", {})
        if validation:
            report_content += f"- **PostgreSQL Connectivity**: {'✅' if validation.get('postgresql_connectivity') else '❌'}\n"
            report_content += f"- **Data Integrity**: {'✅' if validation.get('data_integrity') else '❌'}\n"

            report_content += "\n### Table Count Comparison\n"
            for table, counts in validation.get("table_counts", {}).items():
                match_icon = "✅" if counts.get("match") else "❌"
                report_content += f"- `{table}`: SQLite {counts.get('sqlite', 0)} → PostgreSQL {counts.get('postgresql', 0)} {match_icon}\n"

        if self.migration_report.get("issues"):
            report_content += f"""
## ⚠️ Issues Found
"""
            for issue in self.migration_report["issues"]:
                report_content += f"- {issue}\n"

        report_content += f"""
## 🎯 Next Steps
1. **Test Application**: Start the application and verify all functionality
2. **Update Environment**: Switch DATABASE_URL to PostgreSQL
3. **Performance Testing**: Monitor query performance
4. **Backup Management**: Keep SQLite backups for rollback if needed

## 📝 Configuration
Update your `.env` file:
```env
DATABASE_URL=postgresql://{self.pg_config['user']}:{self.pg_config['password']}@{self.pg_config['host']}:{self.pg_config['port']}/{self.pg_config['database']}
```

---
*Generated by Database Migration V2 System*
"""

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        return str(report_file)

    def run_migration(self) -> bool:
        """전체 마이그레이션 실행"""
        print("=" * 60)
        print("🚀 Database Migration V2: SQLite → PostgreSQL")
        print("=" * 60)

        try:
            # 1. SQLite 분석
            sqlite_analysis = self.analyze_sqlite_schema()
            if not sqlite_analysis:
                print("❌ SQLite 분석 실패")
                return False

            # 2. PostgreSQL 스키마 생성
            schema_file = self.generate_postgresql_schema(sqlite_analysis)

            # 3. PostgreSQL 설정
            if not self.setup_postgresql(schema_file):
                print("❌ PostgreSQL 설정 실패")
                return False

            # 4. 데이터 마이그레이션
            if not self.migrate_data(sqlite_analysis):
                print("⚠️ 데이터 마이그레이션 부분 실패")

            # 5. 검증
            validation_success = self.validate_migration()

            # 6. 보고서 생성
            report_file = self.generate_report()

            print("=" * 60)
            if validation_success:
                print("✅ Database Migration V2 완료!")
            else:
                print("⚠️ Database Migration V2 부분 완료 (검증 실패)")
            print(f"📄 보고서: {report_file}")
            print("=" * 60)

            return validation_success

        except Exception as e:
            logger.error(f"마이그레이션 실행 실패: {e}")
            self.migration_report["issues"].append(f"전체 실행 오류: {str(e)}")
            return False


def main():
    """메인 실행 함수"""
    migration = DatabaseMigrationV2()
    success = migration.run_migration()

    if success:
        print("✅ 마이그레이션 성공적으로 완료!")
        return 0
    else:
        print("❌ 마이그레이션 실패 또는 부분 완료")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
