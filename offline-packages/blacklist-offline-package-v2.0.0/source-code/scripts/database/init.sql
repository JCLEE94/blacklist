-- Blacklist MSA 데이터베이스 초기화 스크립트

-- 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 블랙리스트 IP 테이블
CREATE TABLE IF NOT EXISTS blacklist_ips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address VARCHAR(45) NOT NULL,
    source VARCHAR(100) NOT NULL,
    detection_date TIMESTAMP NOT NULL,
    threat_type VARCHAR(100),
    risk_level VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(ip_address, source)
);

-- 수집 이력 테이블
CREATE TABLE IF NOT EXISTS collection_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    total_ips INTEGER DEFAULT 0,
    new_ips INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 분석 메트릭 테이블
CREATE TABLE IF NOT EXISTS analytics_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC,
    metric_date DATE NOT NULL,
    category VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_name, metric_date, category)
);

-- 인덱스 생성
CREATE INDEX idx_blacklist_ips_ip ON blacklist_ips(ip_address);
CREATE INDEX idx_blacklist_ips_source ON blacklist_ips(source);
CREATE INDEX idx_blacklist_ips_active ON blacklist_ips(is_active);
CREATE INDEX idx_blacklist_ips_detection ON blacklist_ips(detection_date);
CREATE INDEX idx_collection_history_source ON collection_history(source);
CREATE INDEX idx_collection_history_start ON collection_history(start_time);
CREATE INDEX idx_analytics_metrics_name_date ON analytics_metrics(metric_name, metric_date);

-- 트리거 함수: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 트리거 생성
CREATE TRIGGER update_blacklist_ips_updated_at 
    BEFORE UPDATE ON blacklist_ips 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 초기 데이터 (선택사항)
INSERT INTO analytics_metrics (metric_name, metric_value, metric_date, category) 
VALUES 
    ('total_active_ips', 0, CURRENT_DATE, 'system'),
    ('daily_new_ips', 0, CURRENT_DATE, 'system')
ON CONFLICT (metric_name, metric_date, category) DO NOTHING;