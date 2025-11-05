-- PostgreSQL schema for metrics storage
-- This schema defines tables and functions for storing, aggregating, 
-- and querying metrics data.

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS metrics;

-- Set search path
SET search_path TO metrics, public;

-- Enum type for metric types
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'metric_type') THEN
        CREATE TYPE metric_type AS ENUM ('counter', 'gauge', 'histogram', 'summary');
    END IF;
END$$;

-- Create metrics metadata table to store information about registered metrics
CREATE TABLE IF NOT EXISTS metrics_metadata (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    help_text TEXT,
    unit VARCHAR(50),
    label_names JSONB,
    buckets JSONB,
    objectives JSONB,
    alert_threshold FLOAT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE (service_name, metric_name)
);

-- Create index on service_name and metric_name for faster lookup
CREATE INDEX IF NOT EXISTS idx_metrics_metadata_names ON metrics_metadata (service_name, metric_name);

-- Create metrics table to store actual metric values
CREATE TABLE IF NOT EXISTS metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_id INTEGER NOT NULL REFERENCES metrics_metadata(id) ON DELETE CASCADE,
    labels JSONB NOT NULL DEFAULT '{}',
    value FLOAT NOT NULL,
    timestamp TIMESTAMP NOT NULL
);

-- Create index on metric_id and timestamp for faster queries
CREATE INDEX IF NOT EXISTS idx_metrics_metric_id ON metrics (metric_id);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics (timestamp);

-- Create aggregated metrics table to store summarized metrics data
CREATE TABLE IF NOT EXISTS aggregated_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_id INTEGER NOT NULL REFERENCES metrics_metadata(id) ON DELETE CASCADE,
    labels JSONB NOT NULL DEFAULT '{}',
    min_value FLOAT,
    max_value FLOAT,
    sum_value FLOAT,
    count_value INTEGER,
    avg_value FLOAT,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL
);

-- Create index on aggregated metrics for faster queries
CREATE INDEX IF NOT EXISTS idx_aggregated_metrics_period ON aggregated_metrics (period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_aggregated_metrics_metric_id ON aggregated_metrics (metric_id);

-- Create health checks table to monitor recorder health
CREATE TABLE IF NOT EXISTS health_checks (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) NOT NULL,
    check_time TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    response_time_ms FLOAT NOT NULL
);

-- Create index on health checks for faster queries
CREATE INDEX IF NOT EXISTS idx_health_checks_service ON health_checks (service_name);
CREATE INDEX IF NOT EXISTS idx_health_checks_time ON health_checks (check_time);

-- Stored procedure to cleanup old metrics
CREATE OR REPLACE FUNCTION cleanup_old_metrics(
    retention_days INTEGER,
    service_name_filter VARCHAR DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP;
BEGIN
    -- Calculate cutoff date
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    -- Delete old metrics
    IF service_name_filter IS NOT NULL THEN
        WITH metric_ids AS (
            SELECT id FROM metrics_metadata WHERE service_name = service_name_filter
        )
        DELETE FROM metrics
        WHERE metric_id IN (SELECT id FROM metric_ids)
          AND timestamp < cutoff_date;
    ELSE
        DELETE FROM metrics WHERE timestamp < cutoff_date;
    END IF;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Also clean up old health checks
    DELETE FROM health_checks WHERE check_time < cutoff_date;
    
    -- Clean up old aggregated metrics
    DELETE FROM aggregated_metrics WHERE period_end < cutoff_date;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Stored procedure to aggregate metrics
CREATE OR REPLACE FUNCTION aggregate_metrics(
    aggregation_interval_seconds INTEGER,
    service_name_filter VARCHAR DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    aggregated_count INTEGER;
    cutoff_time TIMESTAMP;
    period_start TIMESTAMP;
    period_end TIMESTAMP;
BEGIN
    -- Calculate time periods
    cutoff_time := NOW() - (aggregation_interval_seconds || ' seconds')::INTERVAL;
    period_start := DATE_TRUNC('minute', cutoff_time - (aggregation_interval_seconds || ' seconds')::INTERVAL);
    period_end := period_start + (aggregation_interval_seconds || ' seconds')::INTERVAL;
    
    -- Insert aggregated data
    WITH metric_ids AS (
        SELECT id FROM metrics_metadata 
        WHERE service_name_filter IS NULL OR service_name = service_name_filter
    )
    INSERT INTO aggregated_metrics (
        metric_id, labels, min_value, max_value, sum_value, count_value, avg_value, period_start, period_end
    )
    SELECT 
        metric_id, 
        labels, 
        MIN(value) as min_value, 
        MAX(value) as max_value, 
        SUM(value) as sum_value, 
        COUNT(*) as count_value, 
        AVG(value) as avg_value,
        period_start,
        period_end
    FROM metrics
    WHERE metric_id IN (SELECT id FROM metric_ids)
      AND timestamp >= period_start
      AND timestamp < period_end
    GROUP BY metric_id, labels
    ON CONFLICT (metric_id, labels, period_start, period_end) 
    DO UPDATE SET
        min_value = EXCLUDED.min_value,
        max_value = EXCLUDED.max_value,
        sum_value = EXCLUDED.sum_value,
        count_value = EXCLUDED.count_value,
        avg_value = EXCLUDED.avg_value;
    
    GET DIAGNOSTICS aggregated_count = ROW_COUNT;
    
    -- Clean up raw metrics that have been aggregated
    DELETE FROM metrics
    WHERE timestamp >= period_start
      AND timestamp < period_end
      AND metric_id IN (
          SELECT id FROM metrics_metadata 
          WHERE service_name_filter IS NULL OR service_name = service_name_filter
      );
    
    RETURN aggregated_count;
END;
$$ LANGUAGE plpgsql;

-- Add constraint for uniqueness in aggregated metrics
ALTER TABLE aggregated_metrics ADD CONSTRAINT IF NOT EXISTS unique_aggregated_metrics 
UNIQUE (metric_id, labels, period_start, period_end);

-- Comments explaining usage:
COMMENT ON TABLE metrics IS 'Stores all raw metric data points';
COMMENT ON TABLE metrics_metadata IS 'Stores metadata about metrics including help text and configuration';
COMMENT ON TABLE aggregated_metrics IS 'Stores pre-computed aggregations of metrics for faster querying';
COMMENT ON TABLE health_checks IS 'Stores health check information for metrics recorders';

COMMENT ON FUNCTION aggregate_metrics IS 'Aggregates raw metrics data for a specific time window';
COMMENT ON FUNCTION cleanup_old_metrics IS 'Deletes old metrics data based on retention period'; 