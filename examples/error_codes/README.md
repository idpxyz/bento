# Error Codes Examples

This directory contains **EXAMPLES** of how to define domain-specific error codes.

## ⚠️ Important

These are **NOT** part of the Bento framework. They are examples for reference only.

## 📦 Files

- `order_errors.py` - Order domain error codes example
- `product_errors.py` - Product domain error codes example
- `user_errors.py` - User domain error codes example

## 🎯 Usage in Your Project

### Step 1: Create Error Codes in Your Module

```python
# modules/order/errors.py
from core.errors import ErrorCode


class OrderErrors:
    """Order domain error codes."""
    
    ORDER_NOT_FOUND = ErrorCode(
        code="ORDER_001",
        message="Order not found",
        http_status=404
    )
    
    ORDER_ALREADY_PAID = ErrorCode(
        code="ORDER_003",
        message="Order is already paid",
        http_status=409
    )
```

### Step 2: Use in Your Domain

```python
# modules/order/domain/order.py
from core.errors import DomainException
from modules.order.errors import OrderErrors


class Order(AggregateRoot):
    def pay(self) -> None:
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={"order_id": self.id.value}
            )
        
        self.status = OrderStatus.PAID
```

## 📋 Best Practices

### 1. Error Code Naming Convention

```
{DOMAIN}_{NUMBER}

Examples:
- ORDER_001    # Order domain, error #1
- PRODUCT_003  # Product domain, error #3
- USER_005     # User domain, error #5
```

### 2. HTTP Status Mapping

| Status | Use Case | Example |
|--------|----------|---------|
| 400 | Invalid input | INVALID_PRICE |
| 401 | Not authenticated | UNAUTHORIZED |
| 403 | No permission | FORBIDDEN |
| 404 | Not found | ORDER_NOT_FOUND |
| 409 | Conflict | ORDER_ALREADY_PAID |
| 500 | Server error | DATABASE_ERROR |

### 3. Module Structure

```
modules/
├── order/
│   ├── domain/
│   │   └── order.py
│   ├── application/
│   │   └── create_order.py
│   └── errors.py          # ← Define OrderErrors here
│
├── product/
│   ├── domain/
│   │   └── product.py
│   └── errors.py          # ← Define ProductErrors here
│
└── user/
    ├── domain/
    │   └── user.py
    └── errors.py          # ← Define UserErrors here
```

## 🔗 Related

- Framework errors: `src/core/error_codes.py` (CommonErrors, RepositoryErrors)
- Exception system: `src/core/errors.py`
- Usage guide: `docs/infrastructure/EXCEPTION_USAGE.md`

