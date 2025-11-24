#!/bin/bash
# Order 模块完整流程测试脚本

echo "🧪 Testing Order Module - Complete Flow"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000/api/v1"

# 1. 创建分类
echo "📦 Step 1: Create Category..."
CATEGORY_RESPONSE=$(curl -s -X POST "$BASE_URL/categories/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "电子产品",
    "description": "各类电子产品"
  }')
CATEGORY_ID=$(echo $CATEGORY_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Category created: $CATEGORY_ID"
echo ""

# 2. 创建产品
echo "📱 Step 2: Create Product..."
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/products/" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"iPhone 15 Pro\",
    \"description\": \"最新款 iPhone\",
    \"price\": 999.99,
    \"category_id\": \"$CATEGORY_ID\"
  }")
PRODUCT_ID=$(echo $PRODUCT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
PRODUCT_NAME=$(echo $PRODUCT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
PRODUCT_PRICE=$(echo $PRODUCT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['price'])")
echo "✅ Product created: $PRODUCT_ID - $PRODUCT_NAME ($PRODUCT_PRICE)"
echo ""

# 3. 创建订单
echo "🛒 Step 3: Create Order..."
ORDER_RESPONSE=$(curl -s -X POST "$BASE_URL/orders/" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"customer-001\",
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"product_name\": \"$PRODUCT_NAME\",
        \"quantity\": 2,
        \"unit_price\": $PRODUCT_PRICE
      }
    ]
  }")
ORDER_ID=$(echo $ORDER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
ORDER_STATUS=$(echo $ORDER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
ORDER_TOTAL=$(echo $ORDER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])")
echo "✅ Order created: $ORDER_ID"
echo "   Status: $ORDER_STATUS"
echo "   Total: \$$ORDER_TOTAL"
echo ""

# 4. 查询订单详情
echo "🔍 Step 4: Get Order Details..."
ORDER_DETAIL=$(curl -s "$BASE_URL/orders/$ORDER_ID")
echo "$ORDER_DETAIL" | python3 -m json.tool
echo ""

# 5. 确认支付
echo "💳 Step 5: Pay Order..."
PAY_RESPONSE=$(curl -s -X POST "$BASE_URL/orders/$ORDER_ID/pay")
PAY_STATUS=$(echo $PAY_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
echo "✅ Payment confirmed"
echo "   Status: $PAY_STATUS"
echo ""

# 6. 发货
echo "🚚 Step 6: Ship Order..."
SHIP_RESPONSE=$(curl -s -X POST "$BASE_URL/orders/$ORDER_ID/ship" \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_number": "SF1234567890"
  }')
SHIP_STATUS=$(echo $SHIP_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
echo "✅ Order shipped"
echo "   Status: $SHIP_STATUS"
echo ""

# 7. 查询所有订单
echo "📋 Step 7: List All Orders..."
ALL_ORDERS=$(curl -s "$BASE_URL/orders/")
echo "$ALL_ORDERS" | python3 -m json.tool
echo ""

echo "========================================"
echo "✅ Order Module Test Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "  Category ID: $CATEGORY_ID"
echo "  Product ID:  $PRODUCT_ID"
echo "  Order ID:    $ORDER_ID"
echo "  Final Status: $SHIP_STATUS"
echo "  Total Amount: \$$ORDER_TOTAL"
