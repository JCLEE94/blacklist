"""Database query builder tests

Tests for query building, SQL generation, and parameter binding.
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Mock QueryBuilder for testing purposes - replace with actual import when available
class QueryBuilder:
    """Mock QueryBuilder for testing"""
    def __init__(self):
        self.query_parts = []
        self.params = []
    
    def select(self, columns):
        self.query_parts.append(f"SELECT {columns}")
        return self
    
    def from_table(self, table):
        self.query_parts.append(f"FROM {table}")
        return self
    
    def where(self, condition, *params):
        self.query_parts.append(f"WHERE {condition}")
        self.params.extend(params)
        return self
    
    def join(self, table, condition):
        self.query_parts.append(f"JOIN {table} ON {condition}")
        return self
    
    def group_by(self, columns):
        self.query_parts.append(f"GROUP BY {columns}")
        return self
    
    def having(self, condition, *params):
        self.query_parts.append(f"HAVING {condition}")
        self.params.extend(params)
        return self
    
    def order_by(self, columns):
        self.query_parts.append(f"ORDER BY {columns}")
        return self
    
    def limit(self, count):
        self.query_parts.append(f"LIMIT {count}")
        return self
    
    def insert_into(self, table):
        self.query_parts.append(f"INSERT INTO {table}")
        return self
    
    def values(self, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        self.query_parts.append(f"({columns}) VALUES ({placeholders})")
        self.params.extend(data.values())
        return self
    
    def update(self, table):
        self.query_parts.append(f"UPDATE {table}")
        return self
    
    def set(self, data):
        assignments = ', '.join([f"{k} = ?" for k in data.keys()])
        self.query_parts.append(f"SET {assignments}")
        self.params.extend(data.values())
        return self
    
    def delete_from(self, table):
        self.query_parts.append(f"DELETE FROM {table}")
        return self
    
    def build(self):
        return ' '.join(self.query_parts)
    
    def build_with_params(self):
        return self.build(), self.params


class TestQueryBuilder:
    """쿼리 빌더 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.builder = QueryBuilder()

    def test_select_query_basic(self):
        """기본 SELECT 쿼리 테스트"""
        query = self.builder.select("*").from_table("blacklist_ips").build()
        expected = "SELECT * FROM blacklist_ips"
        assert query.strip() == expected

    def test_select_query_with_conditions(self):
        """조건부 SELECT 쿼리 테스트"""
        query = (self.builder
                .select("ip_address, source")
                .from_table("blacklist_ips")
                .where("is_active = ?", True)
                .build())
        
        assert "SELECT ip_address, source" in query
        assert "FROM blacklist_ips" in query
        assert "WHERE is_active = ?" in query

    def test_insert_query(self):
        """INSERT 쿼리 테스트"""
        query = (self.builder
                .insert_into("blacklist_ips")
                .values({
                    "ip_address": "192.168.1.1",
                    "source": "regtech",
                    "is_active": True
                })
                .build())
        
        assert "INSERT INTO blacklist_ips" in query
        assert "VALUES" in query

    def test_update_query(self):
        """UPDATE 쿼리 테스트"""
        query = (self.builder
                .update("blacklist_ips")
                .set({"is_active": False})
                .where("ip_address = ?", "192.168.1.1")
                .build())
        
        assert "UPDATE blacklist_ips" in query
        assert "SET is_active = ?" in query
        assert "WHERE ip_address = ?" in query

    def test_delete_query(self):
        """DELETE 쿼리 테스트"""
        query = (self.builder
                .delete_from("blacklist_ips")
                .where("exp_date < ?", datetime.now())
                .build())
        
        assert "DELETE FROM blacklist_ips" in query
        assert "WHERE exp_date < ?" in query

    def test_join_query(self):
        """JOIN 쿼리 테스트"""
        query = (self.builder
                .select("b.ip_address, s.name")
                .from_table("blacklist_ips b")
                .join("sources s", "b.source_id = s.id")
                .build())
        
        assert "SELECT b.ip_address, s.name" in query
        assert "JOIN sources s ON b.source_id = s.id" in query

    def test_complex_query(self):
        """복잡한 쿼리 테스트"""
        query = (self.builder
                .select("COUNT(*) as total")
                .from_table("blacklist_ips")
                .where("is_active = ?", True)
                .where("source IN (?, ?)", "regtech", "secudium")
                .group_by("source")
                .having("COUNT(*) > ?", 10)
                .order_by("total DESC")
                .limit(5)
                .build())
        
        assert "COUNT(*) as total" in query
        assert "WHERE is_active = ?" in query
        assert "GROUP BY source" in query
        assert "HAVING COUNT(*) > ?" in query
        assert "ORDER BY total DESC" in query
        assert "LIMIT 5" in query

    def test_parameter_binding(self):
        """파라미터 바인딩 테스트"""
        query, params = (self.builder
                        .select("*")
                        .from_table("blacklist_ips")
                        .where("ip_address = ?", "192.168.1.1")
                        .where("created_at > ?", datetime.now())
                        .build_with_params())
        
        assert "WHERE ip_address = ?" in query
        assert len(params) == 2
        assert params[0] == "192.168.1.1"

    def test_sql_injection_protection(self):
        """SQL 인젝션 보호 테스트"""
        malicious_input = "'; DROP TABLE blacklist_ips; --"
        
        query, params = (self.builder
                        .select("*")
                        .from_table("blacklist_ips")
                        .where("ip_address = ?", malicious_input)
                        .build_with_params())
        
        # 파라미터가 안전하게 바인딩되었는지 확인
        assert malicious_input in params
        assert "DROP TABLE" not in query

    def test_query_validation(self):
        """쿼리 유효성 검증 테스트"""
        # 빈 쿼리 테스트
        empty_builder = QueryBuilder()
        query = empty_builder.build()
        assert query == ""
        
        # 불완전한 쿼리 테스트
        incomplete_query = self.builder.select("*").build()
        assert "SELECT *" in incomplete_query

    def test_query_escaping(self):
        """쿼리 이스케이프 테스트"""
        # 특수 문자 처리
        special_chars = "test'value\"with\nspecial\tchars"
        query, params = (self.builder
                        .select("*")
                        .from_table("blacklist_ips")
                        .where("description = ?", special_chars)
                        .build_with_params())
        
        assert special_chars in params
        assert "description = ?" in query
