-- Query to verify Outbox events after order creation
-- Run this after creating an order via the API

-- 1. Check all Outbox events
SELECT
    id,
    aggregate_id,
    event_type,
    status,
    created_at,
    published_at,
    jsonb_pretty(payload::jsonb) as payload_formatted
FROM outbox
ORDER BY created_at DESC
LIMIT 10;

-- 2. Count events by status
SELECT
    status,
    COUNT(*) as count
FROM outbox
GROUP BY status;

-- 3. Check specific OrderCreatedEvent details
SELECT
    aggregate_id as order_id,
    payload->>'customer_id' as customer_id,
    payload->>'total' as total,
    payload->>'item_count' as item_count,
    jsonb_array_length(payload->'items') as items_in_payload,
    created_at
FROM outbox
WHERE event_type = 'OrderCreatedEvent'
ORDER BY created_at DESC
LIMIT 5;

-- 4. Verify event status transitions (NEW → SENT)
SELECT
    event_type,
    status,
    COUNT(*) as count,
    MAX(created_at) as latest_event
FROM outbox
GROUP BY event_type, status
ORDER BY event_type, status;
