"""
향상된 테스트 설정 및 픽스처

모든 통합 테스트에서 사용할 공통 픽스처와 모킹 유틸리티를 제공합니다.
"""

import os
import sys
import tempfile
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from contextlib import contextmanager
from typing import Generator, Dict, Any

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 테스트 환경 변수 설정
os.environ.update({
    'FLASK_ENV': 'testing',
    'TESTING': 'true',
    'COLLECTION_ENABLED': 'false',
    'FORCE_DISABLE_COLLECTION': 'true',
    'CACHE_TYPE': 'simple',
    'DATABASE_URL': 'sqlite:///:memory:',
    'SECRET_KEY': 'test-secret-key',
    'JWT_SECRET_KEY': 'test-jwt-secret',
    'REGTECH_USERNAME': 'test-regtech-user',
    'REGTECH_PASSWORD': 'test-regtech-pass',
    'SECUDIUM_USERNAME': 'test-secudium-user',
    'SECUDIUM_PASSWORD': 'test-secudium-pass',
})


@pytest.fixture(scope='session')
def test_database():
    """테스트용 메모리 데이터베이스"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # 스키마 설정
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 기본 테이블 생성
        cursor.execute("""
            CREATE TABLE blacklist_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL UNIQUE,
                first_seen TEXT,
                last_seen TEXT,
                detection_months TEXT DEFAULT '[]',
                is_active BOOLEAN DEFAULT 1,
                threat_level TEXT DEFAULT 'medium',
                source TEXT DEFAULT 'test',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE collection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                items_collected INTEGER DEFAULT 0,
                execution_time_ms REAL DEFAULT 0.0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                service TEXT,
                failure_reason TEXT
            )
        """)
        
        # 테스트 데이터 삽입
        cursor.execute("""
            INSERT INTO blacklist_entries (ip_address, source, is_active)
            VALUES 
                ('192.168.1.100', 'test', 1),
                ('10.0.0.50', 'regtech', 1),
                ('172.16.0.1', 'secudium', 0)
        """)
        
        conn.commit()
        conn.close()
        
        yield db_path
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def mock_flask_app():
    """모킹된 Flask 애플리케이션"""
    with patch('flask.Flask') as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        
        # 기본 설정
        mock_app.config = {
            'TESTING': True,
            'SECRET_KEY': 'test-key',
            'COLLECTION_ENABLED': False,
            'DATABASE_URL': 'sqlite:///:memory:'
        }
        
        # 라우트 등록 모킹
        mock_app.register_blueprint = MagicMock()
        mock_app.route = lambda *args, **kwargs: lambda f: f
        
        yield mock_app


@pytest.fixture
def mock_database_connection(test_database):
    """모킹된 데이터베이스 연결"""
    with patch('sqlite3.connect') as mock_connect:
        conn = sqlite3.connect(test_database)
        conn.row_factory = sqlite3.Row
        mock_connect.return_value = conn
        yield conn
        conn.close()


@pytest.fixture
def mock_external_services():
    """외부 서비스 모킹"""
    mocks = {}
    
    # REGTECH API 모킹
    with patch('requests.Session.post') as mock_regtech_post:
        mock_regtech_post.return_value.status_code = 200
        mock_regtech_post.return_value.json.return_value = {
            'success': True,
            'data': []
        }
        mocks['regtech_post'] = mock_regtech_post
        
        # SECUDIUM API 모킹
        with patch('requests.Session.get') as mock_secudium_get:
            mock_secudium_get.return_value.status_code = 200
            mock_secudium_get.return_value.content = b'test,excel,content'
            mocks['secudium_get'] = mock_secudium_get
            
            # Redis 모킹
            with patch('redis.Redis') as mock_redis_class:
                mock_redis = MagicMock()
                mock_redis.ping.return_value = True
                mock_redis.get.return_value = None
                mock_redis.set.return_value = True
                mock_redis_class.return_value = mock_redis
                mocks['redis'] = mock_redis
                
                yield mocks


@pytest.fixture
def mock_file_system():
    """파일 시스템 모킹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # 필요한 디렉토리 구조 생성
        (tmpdir_path / 'instance').mkdir()
        (tmpdir_path / 'src').mkdir()
        (tmpdir_path / 'tests').mkdir()
        (tmpdir_path / '.github' / 'workflows').mkdir(parents=True)
        (tmpdir_path / 'k8s').mkdir()
        (tmpdir_path / 'scripts').mkdir()
        
        # 기본 파일들 생성
        (tmpdir_path / 'requirements.txt').write_text('flask==2.3.3\nrequests==2.31.0\n')
        (tmpdir_path / 'pytest.ini').write_text('[tool:pytest]\naddopts = --cov=src\n')
        
        # 워크플로우 파일 생성
        workflow_content = """
name: CI/CD Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
    paths-ignore:
      - '**.md'
      - 'docs/**'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  REGISTRY: registry.jclee.me
  IMAGE_NAME: blacklist

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest
        
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t $REGISTRY/$IMAGE_NAME .
        
  create-offline-package:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create package
        run: echo "Creating offline package"
        
  deploy:
    runs-on: ubuntu-latest
    needs: [test, build]
    steps:
      - name: Deploy to ArgoCD
        run: echo "Deploying"
"""
        (tmpdir_path / '.github' / 'workflows' / 'ci-cd.yml').write_text(workflow_content)
        
        # K8s 매니페스트 생성
        deployment_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
spec:
  template:
    spec:
      containers:
      - name: blacklist
        image: registry.jclee.me/blacklist:latest
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
"""
        (tmpdir_path / 'k8s' / 'deployment.yaml').write_text(deployment_yaml)
        
        # ArgoCD 앱 정의
        argocd_app_yaml = """
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  annotations:
    argocd-image-updater.argoproj.io/image-list: registry.jclee.me/blacklist:latest
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
"""
        (tmpdir_path / 'k8s' / 'argocd-app-clean.yaml').write_text(argocd_app_yaml)
        
        # 스크립트 파일들 생성
        k8s_script = """#!/bin/bash
print_step() { echo "STEP: $1"; }
print_success() { echo "SUCCESS: $1"; }
print_error() { echo "ERROR: $1"; }
"""
        (tmpdir_path / 'scripts' / 'k8s-management.sh').write_text(k8s_script)
        
        multi_deploy_script = """#!/bin/bash
# Multi-cluster deployment
REMOTE_SERVER="192.168.50.110"
rsync -av . $REMOTE_SERVER:/tmp/deploy/
ssh $REMOTE_SERVER "cd /tmp/deploy && ./deploy.sh"
"""
        (tmpdir_path / 'scripts' / 'multi-deploy.sh').write_text(multi_deploy_script)
        
        # Dockerfile 생성
        dockerfile_content = """
FROM python:3.10-slim AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY . /app
WORKDIR /app
CMD ["python", "main.py"]
"""
        (tmpdir_path / 'deployment' / 'Dockerfile').write_text(dockerfile_content)
        
        with patch('pathlib.Path.cwd', return_value=tmpdir_path):
            with patch('os.getcwd', return_value=str(tmpdir_path)):
                yield tmpdir_path


@pytest.fixture
def mock_container_system():
    """컨테이너 시스템 모킹"""
    with patch('src.core.container.get_container') as mock_get_container:
        mock_container = MagicMock()
        
        # 주요 서비스들 모킹
        mock_unified_service = MagicMock()
        mock_unified_service.get_system_health.return_value = {
            'status': 'healthy',
            'services': {'database': 'connected', 'cache': 'connected'}
        }
        mock_unified_service.get_blacklist_summary.return_value = {
            'total_ips': 100,
            'active_ips': 95,
            'sources': ['regtech', 'secudium']
        }
        
        mock_blacklist_manager = MagicMock()
        mock_blacklist_manager.get_active_ips.return_value = [
            '192.168.1.100', '10.0.0.50'
        ]
        
        mock_cache_manager = MagicMock()
        mock_cache_manager.get.return_value = None
        mock_cache_manager.set.return_value = True
        
        # 컨테이너 서비스 등록
        def get_service(service_name):
            services = {
                'unified_service': mock_unified_service,
                'blacklist_manager': mock_blacklist_manager,
                'cache_manager': mock_cache_manager,
            }
            return services.get(service_name, MagicMock())
        
        mock_container.get = get_service
        mock_get_container.return_value = mock_container
        
        yield {
            'container': mock_container,
            'unified_service': mock_unified_service,
            'blacklist_manager': mock_blacklist_manager,
            'cache_manager': mock_cache_manager,
        }


@pytest.fixture
def mock_subprocess():
    """subprocess 모킹"""
    with patch('subprocess.run') as mock_run:
        # 기본적으로 성공 반환
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'success'
        mock_result.stderr = ''
        mock_run.return_value = mock_result
        
        yield mock_run


@pytest.fixture
def mock_ci_cd_environment():
    """CI/CD 환경 변수 모킹"""
    ci_env = {
        'GITHUB_ACTIONS': 'true',
        'GITHUB_REPOSITORY': 'JCLEE94/blacklist',
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_SHA': 'abc123def456',
        'RUNNER_OS': 'Linux',
        'CI': 'true'
    }
    
    with patch.dict(os.environ, ci_env):
        yield ci_env


@contextmanager
def does_not_raise():
    """예외가 발생하지 않음을 나타내는 컨텍스트 매니저"""
    yield


class MockResponse:
    """HTTP 응답 모킹 클래스"""
    def __init__(self, json_data=None, status_code=200, content=b'', headers=None):
        self.json_data = json_data or {}
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content.decode('utf-8') if isinstance(content, bytes) else content
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def sample_ip_data():
    """샘플 IP 데이터"""
    return [
        {
            'ip': '192.168.1.100',
            'source': 'regtech',
            'threat_level': 'high',
            'detection_date': '2024-01-15',
            'is_active': True
        },
        {
            'ip': '10.0.0.50',
            'source': 'secudium',
            'threat_level': 'medium',
            'detection_date': '2024-01-14',
            'is_active': True
        },
        {
            'ip': '172.16.0.1',
            'source': 'manual',
            'threat_level': 'low',
            'detection_date': '2024-01-13',
            'is_active': False
        }
    ]


@pytest.fixture
def sample_collection_logs():
    """샘플 수집 로그"""
    return [
        {
            'id': 1,
            'timestamp': '2024-01-15T10:30:00',
            'source': 'regtech',
            'status': 'success',
            'items_collected': 50,
            'execution_time_ms': 1500.0
        },
        {
            'id': 2,
            'timestamp': '2024-01-15T11:00:00',
            'source': 'secudium',
            'status': 'success',
            'items_collected': 30,
            'execution_time_ms': 2000.0
        }
    ]


# 테스트 유틸리티 함수들
def create_test_flask_app():
    """테스트용 Flask 앱 생성"""
    try:
        from src.core.minimal_app import create_minimal_app
        return create_minimal_app()
    except ImportError:
        # 폴백: 기본 Flask 앱
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app


def assert_database_state(db_path: str, expected_tables: list):
    """데이터베이스 상태 검증"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    actual_tables = [row[0] for row in cursor.fetchall()]
    
    for table in expected_tables:
        assert table in actual_tables, f"테이블 {table}이 존재하지 않습니다"
    
    conn.close()


def assert_api_response(response_data: dict, expected_keys: list):
    """API 응답 형식 검증"""
    assert isinstance(response_data, dict), "응답이 딕셔너리가 아닙니다"
    
    for key in expected_keys:
        assert key in response_data, f"응답에 {key} 키가 없습니다"


# 성능 테스트 데코레이터
def performance_test(max_time_ms: float = 1000.0):
    """성능 테스트 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time_ms = (end_time - start_time) * 1000
            assert execution_time_ms < max_time_ms, \
                f"테스트 실행 시간이 너무 깁니다: {execution_time_ms:.2f}ms > {max_time_ms}ms"
            
            return result
        return wrapper
    return decorator


# 테스트 마커들
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.slow = pytest.mark.slow
pytest.mark.performance = pytest.mark.performance