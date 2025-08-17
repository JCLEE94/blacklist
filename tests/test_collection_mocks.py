#!/usr/bin/env python3
"""
Collection Mocks for Testing
컬렉션 테스트용 모의 객체 및 헬퍼 함수
"""

import os
import tempfile
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from datetime import datetime


def enable_collection_for_tests():
    """테스트 환경에서 수집 기능 활성화"""
    os.environ['FORCE_DISABLE_COLLECTION'] = 'false'
    os.environ['COLLECTION_ENABLED'] = 'true'
    os.environ['TEST_MODE'] = 'true'


def disable_collection_for_tests():
    """테스트 환경에서 수집 기능 비활성화"""
    os.environ['FORCE_DISABLE_COLLECTION'] = 'true'
    os.environ['COLLECTION_ENABLED'] = 'false'


class MockCollectionResponse:
    """모의 수집 응답 객체"""
    
    def __init__(self, status_code: int = 200, content: str = "", json_data: Dict = None):
        self.status_code = status_code
        self.content = content.encode('utf-8')
        self.text = content
        self._json_data = json_data or {}
    
    def json(self):
        return self._json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockRegtechCollector:
    """REGTECH 수집기 모의 객체"""
    
    def __init__(self):
        self.collected_data = []
        self.collection_count = 0
    
    def collect_data(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """모의 데이터 수집"""
        self.collection_count += 1
        
        # 모의 데이터 생성
        mock_data = [
            {
                'ip': '192.168.1.100',
                'country': 'KR',
                'reason': 'Malware C2',
                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                'threat_level': 'HIGH'
            },
            {
                'ip': '10.0.0.50',
                'country': 'US',
                'reason': 'Botnet Activity',
                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                'threat_level': 'CRITICAL'
            }
        ]
        
        self.collected_data.extend(mock_data)
        
        return {
            'success': True,
            'collected_count': len(mock_data),
            'data': mock_data,
            'collection_time': 1500.0,
            'source': 'REGTECH_MOCK'
        }


class MockSecudiumCollector:
    """SECUDIUM 수집기 모의 객체"""
    
    def __init__(self):
        self.collected_data = []
        self.collection_count = 0
    
    def collect_data(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """모의 데이터 수집"""
        self.collection_count += 1
        
        # 모의 데이터 생성
        mock_data = [
            {
                'ip': '172.16.0.200',
                'country': 'CN',
                'reason': 'APT Attack',
                'detection_date': datetime.now().strftime('%Y-%m-%d'),
                'threat_level': 'CRITICAL'
            }
        ]
        
        self.collected_data.extend(mock_data)
        
        return {
            'success': True,
            'collected_count': len(mock_data),
            'data': mock_data,
            'collection_time': 800.0,
            'source': 'SECUDIUM_MOCK'
        }


def create_mock_excel_file(data: List[Dict]) -> str:
    """테스트용 모의 Excel 파일 생성"""
    import pandas as pd
    
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # Excel 파일로 저장
        df.to_excel(tmp_file.name, index=False)
        
        return tmp_file.name


def mock_requests_session():
    """모의 requests session"""
    session_mock = Mock()
    
    # 로그인 응답 모의
    login_response = MockCollectionResponse(
        status_code=200,
        json_data={'success': True, 'token': 'mock_token_12345'}
    )
    
    # 데이터 다운로드 응답 모의
    download_response = MockCollectionResponse(
        status_code=200,
        content="Mock Excel File Content"
    )
    
    session_mock.post.return_value = login_response
    session_mock.get.return_value = download_response
    
    return session_mock


def setup_test_environment():
    """테스트 환경 설정"""
    # 테스트용 임시 디렉토리 생성
    test_data_dir = tempfile.mkdtemp(prefix='blacklist_test_')
    os.environ['TEST_DATA_DIR'] = test_data_dir
    
    # 수집 활성화
    enable_collection_for_tests()
    
    return test_data_dir


def cleanup_test_environment(test_data_dir: str = None):
    """테스트 환경 정리"""
    import shutil
    
    if test_data_dir and os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir, ignore_errors=True)
    
    # 환경 변수 정리
    test_env_vars = ['TEST_DATA_DIR', 'TEST_MODE']
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


# 패치 데코레이터 헬퍼
def patch_collection_system():
    """수집 시스템 전체 패치"""
    return patch.multiple(
        'src.core.collectors.unified_collector',
        RegtechCollector=MockRegtechCollector,
        SecudiumCollector=MockSecudiumCollector
    )


def patch_requests():
    """requests 라이브러리 패치"""
    return patch('requests.Session', return_value=mock_requests_session())


if __name__ == "__main__":
    # 모의 수집기 테스트
    print("🧪 Collection Mocks Test")
    
    # REGTECH 모의 수집기 테스트
    regtech_mock = MockRegtechCollector()
    result = regtech_mock.collect_data()
    print(f"REGTECH Mock: {result['collected_count']}개 수집됨")
    
    # SECUDIUM 모의 수집기 테스트
    secudium_mock = MockSecudiumCollector()
    result = secudium_mock.collect_data()
    print(f"SECUDIUM Mock: {result['collected_count']}개 수집됨")
    
    print("✅ Collection mocks 테스트 완료")