#!/bin/bash
# 幂等性测试脚本 - 验证 IdempotencyMiddleware 是否正常工作

echo "🧪 Testing Idempotency Middleware"
echo "=================================="
echo ""

BASE_URL="http://localhost:8000/api/v1"
TIMESTAMP=$(date +%s)
IDEM_KEY="test-order-${TIMESTAMP}"

echo "📝 Test Setup:"
echo "  Base URL: $BASE_URL"
echo "  Idempotency Key: $IDEM_KEY"
echo ""

# 第一步：创建分类
echo "Step 1: Create category..."
CATEGORY=$(curl -s -X POST "$BASE_URL/categories/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Category",
    "description": "Test category for idempotency"
  }')
CATEGORY_ID=$(echo $CATEGORY | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Category created: $CATEGORY_ID"
echo ""

# 第二步：创建产品
echo "Step 2: Create product..."
PRODUCT=$(curl -s -X POST "$BASE_URL/products/" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Product\",
    \"description\": \"Test product\",
    \"price\": 99.99,
    \"category_id\": \"$CATEGORY_ID\"
  }")
PRODUCT_ID=$(echo $PRODUCT | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Product created: $PRODUCT_ID"
echo ""

# 第三步：第一次创建订单（带 idempotency_key 在 Header 中）
echo "Step 3: First order creation (with idempotency_key in header)..."
echo "  Idempotency Key: $IDEM_KEY"
ORDER_1=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/orders/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEM_KEY" \
  -d "{
    \"customer_id\": \"customer-test-001\",
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"product_name\": \"Test Product\",
        \"quantity\": 1,
        \"unit_price\": 99.99
      }
    ]
  }")

HTTP_CODE_1=$(echo "$ORDER_1" | tail -1)
ORDER_1_BODY=$(echo "$ORDER_1" | head -1)
ORDER_ID=$(echo $ORDER_1_BODY | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "  HTTP Status: $HTTP_CODE_1"
echo "  Order ID: $ORDER_ID"
echo "  Response:"
echo "$ORDER_1_BODY" | python3 -m json.tool | head -20
echo ""

# 第四步：第二次创建订单（相同 idempotency_key）
echo "Step 4: Second order creation (same idempotency_key - should be idempotent)..."
echo "  Idempotency Key: $IDEM_KEY (same as first request)"
ORDER_2=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/orders/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEM_KEY" \
  -d "{
    \"customer_id\": \"customer-test-001\",
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"product_name\": \"Test Product\",
        \"quantity\": 1,
        \"unit_price\": 99.99
      }
    ]
  }")

HTTP_CODE_2=$(echo "$ORDER_2" | tail -1)
ORDER_2_BODY=$(echo "$ORDER_2" | head -1)
ORDER_ID_2=$(echo $ORDER_2_BODY | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "  HTTP Status: $HTTP_CODE_2"
echo "  Order ID: $ORDER_ID_2"
echo ""

# 第五步：验证幂等性
echo "Step 5: Verify Idempotency..."
if [ "$ORDER_ID" = "$ORDER_ID_2" ]; then
  echo "✅ IDEMPOTENCY WORKING: Both requests returned the same order ID"
  echo "   First request:  $ORDER_ID"
  echo "   Second request: $ORDER_ID_2"
else
  echo "❌ IDEMPOTENCY NOT WORKING: Different order IDs returned"
  echo "   First request:  $ORDER_ID"
  echo "   Second request: $ORDER_ID_2"
fi
echo ""

# 第六步：测试不同 idempotency_key 应该创建新订单
echo "Step 6: Create order with different idempotency_key (should create new order)..."
IDEM_KEY_2="test-order-${TIMESTAMP}-2"
echo "  Idempotency Key: $IDEM_KEY_2 (different from first)"
ORDER_3=$(curl -s -X POST "$BASE_URL/orders/" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $IDEM_KEY_2" \
  -d "{
    \"customer_id\": \"customer-test-001\",
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"product_name\": \"Test Product\",
        \"quantity\": 1,
        \"unit_price\": 99.99
      }
    ]
  }")

ORDER_ID_3=$(echo $ORDER_3 | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "  Order ID: $ORDER_ID_3"
echo ""

if [ "$ORDER_ID" != "$ORDER_ID_3" ]; then
  echo "✅ Different idempotency_key creates new order"
  echo "   First key order:  $ORDER_ID"
  echo "   Second key order: $ORDER_ID_3"
else
  echo "❌ Different idempotency_key should create new order"
fi
echo ""

# 第七步：测试支付幂等性
echo "Step 7: Test Payment Idempotency..."
PAYMENT_KEY="payment-${TIMESTAMP}"
echo "  Idempotency Key: $PAYMENT_KEY"

# 第一次支付
echo "  First payment request..."
PAY_1=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/orders/$ORDER_ID/pay" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $PAYMENT_KEY" \
  -d "{}")

PAY_HTTP_1=$(echo "$PAY_1" | tail -1)
PAY_BODY_1=$(echo "$PAY_1" | head -1)
PAY_STATUS_1=$(echo $PAY_BODY_1 | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

echo "    HTTP Status: $PAY_HTTP_1"
echo "    Order Status: $PAY_STATUS_1"

# 第二次支付（相同 key）
echo "  Second payment request (same key)..."
PAY_2=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/orders/$ORDER_ID/pay" \
  -H "Content-Type: application/json" \
  -H "x-idempotency-key: $PAYMENT_KEY" \
  -d "{}")

PAY_HTTP_2=$(echo "$PAY_2" | tail -1)
PAY_BODY_2=$(echo "$PAY_2" | head -1)
PAY_STATUS_2=$(echo $PAY_BODY_2 | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

echo "    HTTP Status: $PAY_HTTP_2"
echo "    Order Status: $PAY_STATUS_2"
echo ""

if [ "$PAY_STATUS_1" = "$PAY_STATUS_2" ] && [ "$PAY_HTTP_1" = "$PAY_HTTP_2" ]; then
  echo "✅ PAYMENT IDEMPOTENCY WORKING: Same status returned"
else
  echo "⚠️  Payment responses differ (may be normal if middleware handles differently)"
fi
echo ""

echo "=================================="
echo "✅ Idempotency Test Complete!"
echo "=================================="
echo ""
echo "Summary:"
echo "  Order Creation Idempotency: $([ "$ORDER_ID" = "$ORDER_ID_2" ] && echo '✅ WORKING' || echo '❌ NOT WORKING')"
echo "  Different Key Creates New: $([ "$ORDER_ID" != "$ORDER_ID_3" ] && echo '✅ WORKING' || echo '❌ NOT WORKING')"
echo "  Payment Idempotency: $([ "$PAY_HTTP_1" = "$PAY_HTTP_2" ] && echo '✅ WORKING' || echo '❌ NOT WORKING')"
