#!/bin/bash
# 简单幂等性测试 - 只测试一个订单创建操作

echo "🧪 Simple Idempotency Test"
echo "=========================="
echo ""

BASE_URL="http://localhost:8000/api/v1"
TIMESTAMP=$(date +%s)
IDEM_KEY="simple-test-${TIMESTAMP}"

echo "Setup:"
echo "  Base URL: $BASE_URL"
echo "  Idempotency Key: $IDEM_KEY"
echo ""

# 创建分类
echo "Step 1: Create category..."
CATEGORY=$(curl -s -X POST "$BASE_URL/categories/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "description": "Test"
  }')
CATEGORY_ID=$(echo $CATEGORY | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Category: $CATEGORY_ID"
echo ""

# 创建产品
echo "Step 2: Create product..."
PRODUCT=$(curl -s -X POST "$BASE_URL/products/" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test\",
    \"description\": \"Test\",
    \"price\": 99.99,
    \"category_id\": \"$CATEGORY_ID\"
  }")
PRODUCT_ID=$(echo $PRODUCT | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Product: $PRODUCT_ID"
echo ""

# 第一次创建订单
echo "Step 3: First order creation..."
echo "  Request:"
echo "    POST /api/v1/orders/"
echo "    Header: x-idempotency-key: $IDEM_KEY"
echo ""

ORDER_1=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/orders/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEM_KEY" \
  -d "{
    \"customer_id\": \"test-001\",
    \"items\": [{
      \"product_id\": \"$PRODUCT_ID\",
      \"product_name\": \"Test\",
      \"quantity\": 1,
      \"unit_price\": 99.99
    }]
  }")

HTTP_1=$(echo "$ORDER_1" | tail -1)
BODY_1=$(echo "$ORDER_1" | head -1)
ORDER_ID_1=$(echo "$BODY_1" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "  Response:"
echo "    HTTP Status: $HTTP_1"
echo "    Order ID: $ORDER_ID_1"
echo ""

# 第二次创建订单（相同 key）
echo "Step 4: Second order creation (same key)..."
echo "  Request:"
echo "    POST /api/v1/orders/"
echo "    Header: x-idempotency-key: $IDEM_KEY (same)"
echo ""

ORDER_2=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/orders/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEM_KEY" \
  -d "{
    \"customer_id\": \"test-001\",
    \"items\": [{
      \"product_id\": \"$PRODUCT_ID\",
      \"product_name\": \"Test\",
      \"quantity\": 1,
      \"unit_price\": 99.99
    }]
  }")

HTTP_2=$(echo "$ORDER_2" | tail -1)
BODY_2=$(echo "$ORDER_2" | head -1)
ORDER_ID_2=$(echo "$BODY_2" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "  Response:"
echo "    HTTP Status: $HTTP_2"
echo "    Order ID: $ORDER_ID_2"
echo ""

# 验证
echo "Step 5: Verification..."
if [ "$ORDER_ID_1" = "$ORDER_ID_2" ]; then
  echo "✅ IDEMPOTENCY WORKING!"
  echo "   Both requests returned the same order ID: $ORDER_ID_1"
else
  echo "❌ IDEMPOTENCY NOT WORKING"
  echo "   First request:  $ORDER_ID_1"
  echo "   Second request: $ORDER_ID_2"
  echo ""
  echo "   Checking database..."
  echo "   This might indicate:"
  echo "   1. IdempotencyMiddleware is not properly initialized"
  echo "   2. Database session is not available to middleware"
  echo "   3. Idempotency records are not being stored"
fi
echo ""

echo "=========================="
echo "Test Complete"
echo "=========================="
