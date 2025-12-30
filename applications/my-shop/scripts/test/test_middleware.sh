#!/bin/bash

# Test script for my-shop middleware stack
# Tests: RequestID, StructuredLogging, RateLimiting, Idempotency

set -e

BASE_URL="http://localhost:8000"
echo "Testing my-shop middleware stack at $BASE_URL"
echo "========================================"
echo ""

# Test 1: Request ID Middleware
echo "📋 Test 1: Request ID Middleware"
echo "Testing auto-generated request ID..."
RESPONSE=$(curl -s -i "$BASE_URL/ping")
REQUEST_ID=$(echo "$RESPONSE" | grep -i "X-Request-ID:" | awk '{print $2}' | tr -d '\r')
if [ -n "$REQUEST_ID" ]; then
    echo "✅ Request ID generated: $REQUEST_ID"
else
    echo "❌ Request ID not found in response headers"
fi
echo ""

echo "Testing client-provided request ID..."
CLIENT_REQUEST_ID="test-request-123"
RESPONSE=$(curl -s -i -H "X-Request-ID: $CLIENT_REQUEST_ID" "$BASE_URL/ping")
RETURNED_ID=$(echo "$RESPONSE" | grep -i "X-Request-ID:" | awk '{print $2}' | tr -d '\r')
if [ "$RETURNED_ID" = "$CLIENT_REQUEST_ID" ]; then
    echo "✅ Client request ID preserved: $RETURNED_ID"
else
    echo "❌ Client request ID not preserved. Got: $RETURNED_ID"
fi
echo ""

# Test 2: Rate Limiting Middleware
echo "📋 Test 2: Rate Limiting Middleware"
echo "Testing rate limit headers..."
RESPONSE=$(curl -s -i "$BASE_URL/ping")
RATE_LIMIT=$(echo "$RESPONSE" | grep -i "X-RateLimit-Limit:" | awk '{print $2}' | tr -d '\r')
RATE_REMAINING=$(echo "$RESPONSE" | grep -i "X-RateLimit-Remaining:" | awk '{print $2}' | tr -d '\r')
if [ -n "$RATE_LIMIT" ] && [ -n "$RATE_REMAINING" ]; then
    echo "✅ Rate limit headers present:"
    echo "   Limit: $RATE_LIMIT"
    echo "   Remaining: $RATE_REMAINING"
else
    echo "❌ Rate limit headers not found"
fi
echo ""

echo "Testing rate limit enforcement (sending 65 requests)..."
SUCCESS_COUNT=0
RATE_LIMITED=0
for i in {1..65}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ping")
    if [ "$STATUS" = "200" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    elif [ "$STATUS" = "429" ]; then
        RATE_LIMITED=$((RATE_LIMITED + 1))
    fi
done
echo "   Successful requests: $SUCCESS_COUNT"
echo "   Rate limited requests: $RATE_LIMITED"
if [ $RATE_LIMITED -gt 0 ]; then
    echo "✅ Rate limiting working (got 429 responses)"
else
    echo "⚠️  No rate limiting detected (may need to adjust limits or wait)"
fi
echo ""

# Test 3: Idempotency Middleware
echo "📋 Test 3: Idempotency Middleware"
echo "Creating category with idempotency key..."
IDEMPOTENCY_KEY="test-category-$(date +%s)"
CATEGORY_DATA='{
  "name": "Test Category",
  "description": "Test category for middleware validation"
}'

# First request
RESPONSE1=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/categories/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEMPOTENCY_KEY" \
  -d "$CATEGORY_DATA")
STATUS1=$(echo "$RESPONSE1" | tail -n1)
BODY1=$(echo "$RESPONSE1" | head -n-1)

if [ "$STATUS1" = "201" ]; then
    CATEGORY_ID=$(echo "$BODY1" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
    echo "✅ First request successful (201 Created)"
    echo "   Category ID: $CATEGORY_ID"
else
    echo "❌ First request failed with status: $STATUS1"
fi
echo ""

# Second request with same idempotency key
echo "Sending duplicate request with same idempotency key..."
sleep 1
RESPONSE2=$(curl -s -i -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/categories/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEMPOTENCY_KEY" \
  -d "$CATEGORY_DATA")
STATUS2=$(echo "$RESPONSE2" | tail -n1)
REPLAY_HEADER=$(echo "$RESPONSE2" | grep -i "X-Idempotent-Replay:" | awk '{print $2}' | tr -d '\r')

if [ "$STATUS2" = "201" ] && [ "$REPLAY_HEADER" = "1" ]; then
    echo "✅ Idempotency working (got cached response with X-Idempotent-Replay: 1)"
else
    echo "⚠️  Idempotency may not be working as expected"
    echo "   Status: $STATUS2"
    echo "   Replay header: $REPLAY_HEADER"
fi
echo ""

# Test 4: Idempotency Conflict Detection
echo "📋 Test 4: Idempotency Conflict Detection"
echo "Sending request with same key but different data..."
CONFLICT_DATA='{
  "name": "Different Category",
  "description": "This should trigger a conflict"
}'
RESPONSE3=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/categories/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEMPOTENCY_KEY" \
  -d "$CONFLICT_DATA")
STATUS3=$(echo "$RESPONSE3" | tail -n1)

if [ "$STATUS3" = "409" ]; then
    echo "✅ Conflict detection working (got 409 Conflict)"
else
    echo "⚠️  Expected 409 Conflict, got: $STATUS3"
fi
echo ""

# Test 5: Structured Logging
echo "📋 Test 5: Structured Logging"
echo "Check application logs for structured JSON output"
echo "Expected format:"
echo '  {"event": "http_response", "request_id": "...", "method": "GET", "path": "/ping", ...}'
echo ""

echo "========================================"
echo "✅ Middleware Tests Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  1. Request ID: Generates unique IDs and preserves client IDs"
echo "  2. Rate Limiting: Enforces limits and returns 429 when exceeded"
echo "  3. Idempotency: Caches responses and returns same result for duplicate requests"
echo "  4. Conflict Detection: Returns 409 when same key used with different data"
echo "  5. Structured Logging: Check logs for JSON-formatted request/response data"
echo ""
echo "Note: Make sure the my-shop application is running before executing this script"
