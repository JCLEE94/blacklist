#!/usr/bin/env python3
"""
Base Analytics Class - Common functionality for all analyzers
"""

import logging
import sqlite3
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseAnalyzer:
    """Base class for all analytics components"""
    
    def __init__(self, db_path: str = "instance/blacklist.db"):
        self.db_path = db_path
        
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with error handling"""
        try:
            return sqlite3.connect(self.db_path)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def _execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute query with error handling"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
            
    def _safe_execute(self, func_name: str, func) -> Dict[str, Any]:
        """Safely execute analysis function with error handling"""
        try:
            return func()
        except Exception as e:
            logger.error(f"{func_name} analysis failed: {e}")
            return {}
            
    def _calculate_severity_score(self, frequency: int, threat_level: str) -> float:
        """Calculate severity score based on frequency and threat level"""
        level_weights = {"CRITICAL": 1.0, "HIGH": 0.8, "MEDIUM": 0.6, "LOW": 0.4}
        
        base_score = level_weights.get(threat_level, 0.5)
        frequency_factor = min(frequency / 100, 1.0)  # Normalize
        
        return round(base_score * (0.7 + frequency_factor * 0.3), 2)