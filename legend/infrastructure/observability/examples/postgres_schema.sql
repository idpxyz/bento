-- PostgreSQL Schema for IDP Observability Framework
-- ==============================================
--
-- This script creates the necessary tables for storing observability data
-- including metrics, metric metadata, spans, and span events.
--
-- Usage:
--   psql -U postgres -d observability -f postgres_schema.sql
--
-- Prerequisites:
--   1. Create a database: CREATE DATABASE observability;
--   2. Optionally create a dedicated user for observability

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS observability;

-- Set the search path for this session
SET search_path TO observability;

-- Metrics tables
-- ===========================================================

-- Metric metadata table - stores information about each metric
CREATE TABLE IF NOT EXISTS example_metric_metadata (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    help TEXT,
    type VARCHAR(50) NOT NULL,
    unit VARCHAR(50),
    label_names TEXT[] DEFAULT '{}',
    buckets FLOAT[] DEFAULT NULL,
    objectives JSONB DEFAULT NULL,
    alert_threshold FLOAT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Create index on metric name for faster lookups
CREATE INDEX IF NOT EXISTS idx_metric_metadata_name ON example_metric_metadata(name);

-- Metrics table - stores the actual metric values
CREATE TABLE IF NOT EXISTS example_metrics (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    labels JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create time-based index for faster time-range queries
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON example_metrics USING BRIN(timestamp);
-- Create index on metric name for faster lookups
CREATE INDEX IF NOT EXISTS idx_metrics_name ON example_metrics(name);
-- Create index on labels for JSON query operations
CREATE INDEX IF NOT EXISTS idx_metrics_labels ON example_metrics USING GIN(labels);

-- Spans tables (for distributed tracing)
-- ===========================================================

-- Main spans table
CREATE TABLE IF NOT EXISTS example_spans (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(36) NOT NULL,
    span_id VARCHAR(36) NOT NULL,
    parent_span_id VARCHAR(36),
    name VARCHAR(255) NOT NULL,
    kind VARCHAR(50),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_ms DOUBLE PRECISION,
    status_code VARCHAR(50),
    status_message TEXT,
    service_name VARCHAR(255),
    attributes JSONB DEFAULT '{}'::jsonb,
    resource_attributes JSONB DEFAULT '{}'::jsonb,
    UNIQUE(trace_id, span_id)
);

-- Create indexes for faster trace queries
CREATE INDEX IF NOT EXISTS idx_spans_trace_id ON example_spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_service_name ON example_spans(service_name);
CREATE INDEX IF NOT EXISTS idx_spans_start_time ON example_spans USING BRIN(start_time);
CREATE INDEX IF NOT EXISTS idx_spans_duration ON example_spans(duration_ms);
CREATE INDEX IF NOT EXISTS idx_spans_attributes ON example_spans USING GIN(attributes);

-- Span events table (for exceptions, logs and other events within a span)
CREATE TABLE IF NOT EXISTS example_span_events (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(36) NOT NULL,
    span_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    attributes JSONB DEFAULT '{}'::jsonb,
    FOREIGN KEY (trace_id, span_id) REFERENCES example_spans(trace_id, span_id) ON DELETE CASCADE
);

-- Create indexes for span events
CREATE INDEX IF NOT EXISTS idx_span_events_span_id ON example_span_events(span_id);
CREATE INDEX IF NOT EXISTS idx_span_events_timestamp ON example_span_events USING BRIN(timestamp);

-- Maintenance functions
-- ===========================================================

-- Function to clean up old data (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_observability_data(retention_days INTEGER)
RETURNS TABLE(metrics_deleted BIGINT, spans_deleted BIGINT) AS $$
DECLARE
    cutoff_date TIMESTAMP WITH TIME ZONE;
    metrics_count BIGINT;
    spans_count BIGINT;
BEGIN
    -- Calculate cutoff date
    cutoff_date := NOW() - (retention_days * INTERVAL '1 day');
    
    -- Delete old metrics
    DELETE FROM example_metrics 
    WHERE timestamp < cutoff_date;
    GET DIAGNOSTICS metrics_count = ROW_COUNT;
    
    -- Delete old spans and related events (cascade)
    DELETE FROM example_spans 
    WHERE start_time < cutoff_date;
    GET DIAGNOSTICS spans_count = ROW_COUNT;
    
    -- Return deletion counts
    RETURN QUERY SELECT metrics_count, spans_count;
END;
$$ LANGUAGE plpgsql;

-- Create view for recent errors
CREATE OR REPLACE VIEW recent_errors AS
SELECT 
    s.trace_id,
    s.span_id,
    s.name AS span_name,
    s.service_name,
    s.start_time,
    s.duration_ms,
    e.name AS event_name,
    e.timestamp,
    e.attributes->'exception.type' AS exception_type,
    e.attributes->'exception.message' AS exception_message,
    e.attributes->'exception.stacktrace' AS stacktrace
FROM 
    example_spans s
JOIN 
    example_span_events e ON s.trace_id = e.trace_id AND s.span_id = e.span_id
WHERE 
    e.name = 'exception' 
    AND s.start_time > (NOW() - INTERVAL '24 hours')
ORDER BY 
    e.timestamp DESC;

-- Create aggregated metrics view (hourly)
CREATE OR REPLACE VIEW hourly_metrics_aggregation AS
SELECT
    name,
    date_trunc('hour', timestamp) AS hour,
    labels,
    COUNT(*) AS sample_count,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY value) AS median,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY value) AS p95,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY value) AS p99
FROM
    example_metrics
WHERE
    timestamp > (NOW() - INTERVAL '7 days')
GROUP BY
    name, date_trunc('hour', timestamp), labels
ORDER BY
    hour DESC, name;

-- Sample query to find slow traces
CREATE OR REPLACE VIEW slow_traces AS
SELECT
    trace_id,
    MAX(duration_ms) AS max_span_duration,
    SUM(duration_ms) AS total_duration,
    COUNT(*) AS span_count,
    MIN(start_time) AS trace_start_time,
    jsonb_object_agg(span_id, name) AS span_names
FROM
    example_spans
WHERE
    start_time > (NOW() - INTERVAL '24 hours')
GROUP BY
    trace_id
HAVING
    MAX(duration_ms) > 1000  -- Spans taking more than 1 second
ORDER BY
    max_span_duration DESC
LIMIT 100;

-- Add comments for documentation
COMMENT ON SCHEMA observability IS 'Schema for storing observability data including metrics and traces';
COMMENT ON TABLE example_metric_metadata IS 'Stores metadata about metrics including type, description, and configuration';
COMMENT ON TABLE example_metrics IS 'Stores individual metric data points with values and labels';
COMMENT ON TABLE example_spans IS 'Stores distributed tracing spans';
COMMENT ON TABLE example_span_events IS 'Stores events within spans, such as logs and exceptions';
COMMENT ON FUNCTION cleanup_old_observability_data IS 'Removes observability data older than the specified number of days';
COMMENT ON VIEW recent_errors IS 'Shows recent exceptions recorded in traces';
COMMENT ON VIEW hourly_metrics_aggregation IS 'Provides hourly aggregation of metrics for trend analysis';
COMMENT ON VIEW slow_traces IS 'Identifies slow traces for performance troubleshooting';

-- Grant permissions if using a dedicated user (uncomment and modify as needed)
-- GRANT USAGE ON SCHEMA observability TO observability_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA observability TO observability_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA observability TO observability_user; 