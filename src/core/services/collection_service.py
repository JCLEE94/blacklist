#!/usr/bin/env python3
"""
통합 블랙리스트 서비스 - 수집 관련 기능 모음 (< 500 lines)
데이터 수집, 트리거, 활성화/비활성화 등의 수집 전용 기능
"""

from .collection_operations import CollectionOperationsMixin
from .collection_status import CollectionStatusMixin
from .collection_triggers import CollectionTriggersMixin


class CollectionServiceMixin(
    CollectionOperationsMixin, CollectionTriggersMixin, CollectionStatusMixin
):
    """
    수집 관련 기능을 제공하는 믹스인 클래스
    UnifiedBlacklistService에서 사용됨
    기능은 각각의 별도 모듈로 분산되어 있음
    """

    pass
