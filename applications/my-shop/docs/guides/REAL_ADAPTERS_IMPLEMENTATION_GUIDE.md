# 🔌 真实 Adapters 实现指南

## 📋 概述

本指南提供所有真实 Adapters 的实现模板和集成说明。

---

## ✅ 已实现的真实 Adapters

| Adapter | Port 接口 | 状态 | 文件 |
|---------|----------|------|------|
| `EmailAdapter` | `INotificationService` | ✅ 完成 | `email_adapter.py` |
| `LocalInventoryAdapter` | `IInventoryService` | ✅ 完成 | `local_inventory_adapter.py` |

---

## ⏳ 待实现的 Adapters（提供模板）

### 支付类 Adapters

| Adapter | 用途 | 优先级 | 模板 |
|---------|------|--------|------|
| `AlipayAdapter` | 支付宝支付 | P1 | ✅ 已提供 |
| `WeChatPayAdapter` | 微信支付 | P1 | 见下文 |
| `StripeAdapter` | Stripe支付（国际） | P2 | 见下文 |

### 通知类 Adapters

| Adapter | 用途 | 优先级 | 模板 |
|---------|------|--------|------|
| `EmailAdapter` | SMTP邮件 | ✅ 已实现 | - |
| `SmsAdapter` | 短信通知 | P1 | 见下文 |
| `PushAdapter` | 推送通知 | P2 | 见下文 |

### 库存类 Adapters

| Adapter | 用途 | 优先级 | 模板 |
|---------|------|--------|------|
| `LocalInventoryAdapter` | 本地数据库 | ✅ 已实现 | - |
| `RedisInventoryAdapter` | Redis库存 | P1 | 见下文 |
| `InventoryServiceAdapter` | 独立服务 | P2 | 见下文 |

---

## 1️⃣ EmailAdapter ✅ (已实现)

### 使用示例

```python
from contexts.ordering.infrastructure.adapters.services.email_adapter import (
    EmailAdapter,
    EmailConfig,
)

# 配置
config = EmailConfig(
    smtp_host="smtp.gmail.com",
    smtp_port=465,
    smtp_user="your-email@gmail.com",
    smtp_password="your-app-password",  # 使用应用专用密码
    from_email="noreply@myshop.com",
    from_name="My Shop",
    use_ssl=True,
)

# 创建适配器
email_adapter = EmailAdapter(config)

# 发送通知
await email_adapter.send_order_created("ORDER_001", "customer@example.com")
```

### Gmail 配置步骤

1. 启用两步验证
2. 生成应用专用密码：https://myaccount.google.com/apppasswords
3. 使用应用密码而不是账号密码

### 其他邮件服务

**SendGrid：**
```python
config = EmailConfig(
    smtp_host="smtp.sendgrid.net",
    smtp_port=587,
    smtp_user="apikey",
    smtp_password="YOUR_SENDGRID_API_KEY",
    from_email="noreply@myshop.com",
    use_tls=True,
)
```

**阿里云邮件推送：**
```python
config = EmailConfig(
    smtp_host="smtpdm.aliyun.com",
    smtp_port=465,
    smtp_user="your-username@your-domain.com",
    smtp_password="YOUR_SMTP_PASSWORD",
    from_email="noreply@your-domain.com",
    use_ssl=True,
)
```

---

## 2️⃣ LocalInventoryAdapter ✅ (已实现)

### 使用示例

```python
from contexts.ordering.infrastructure.adapters import LocalInventoryAdapter

# 创建适配器（需要数据库会话）
inventory_adapter = LocalInventoryAdapter(session)

# 检查库存
is_available = await inventory_adapter.check_availability("PROD_001", 10)

# 预留库存
reservation_request = ReservationRequest(
    order_id="ORDER_001",
    items=[("PROD_001", 10)]
)
result = await inventory_adapter.reserve_inventory(reservation_request)

# 扣减库存
await inventory_adapter.deduct_inventory("PROD_001", 10)
```

### 特点

- ✅ 直接使用 Catalog BC 的 Product 表
- ✅ 支持事务
- ⚠️ 预留信息存储在内存（生产环境建议使用 Redis）

---

## 3️⃣ AlipayAdapter（支付宝）

### 安装依赖

```bash
pip install alipay-sdk-python
```

### 实现模板

详见：`_alipay_adapter_template.py`

### 集成步骤

1. **注册应用**
   - 登录：https://open.alipay.com/
   - 创建应用（网页/移动应用）
   - 获取 AppID

2. **配置密钥**
   ```bash
   # 生成RSA密钥对
   openssl genrsa -out app_private_key.pem 2048
   openssl rsa -in app_private_key.pem -pubout -out app_public_key.pem
   ```

3. **上传公钥**
   - 将 `app_public_key.pem` 内容上传到支付宝开放平台
   - 下载支付宝公钥保存为 `alipay_public_key.pem`

4. **测试沙箱**
   ```python
   adapter = AlipayAdapter(
       app_id="SANDBOX_APP_ID",
       app_private_key_path="keys/app_private_key.pem",
       alipay_public_key_path="keys/alipay_public_key.pem",
       debug=True,  # 沙箱环境
   )
   ```

5. **切换生产**
   ```python
   adapter = AlipayAdapter(
       app_id="PROD_APP_ID",
       app_private_key_path="keys/prod_private_key.pem",
       alipay_public_key_path="keys/prod_alipay_public_key.pem",
       debug=False,  # 生产环境
   )
   ```

### 参考文档

- 官方文档：https://opendocs.alipay.com/open/
- Python SDK：https://github.com/fzlee/alipay
- 沙箱环境：https://openhome.alipay.com/develop/sandbox/app

---

## 4️⃣ WeChatPayAdapter（微信支付）

### 安装依赖

```bash
pip install wechatpy
```

### 实现骨架

```python
from wechatpy.pay import WeChatPay
from contexts.ordering.domain.ports.services import IPaymentService

class WeChatPayAdapter(IPaymentService):
    def __init__(
        self,
        app_id: str,
        mch_id: str,
        api_key: str,
        mch_cert_path: str,
        mch_key_path: str,
    ):
        self.wechat_pay = WeChatPay(
            appid=app_id,
            api_key=api_key,
            mch_id=mch_id,
            mch_cert=mch_cert_path,
            mch_key=mch_key_path,
        )

    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        # 创建统一下单
        order = self.wechat_pay.order.create(
            trade_type='NATIVE',  # 扫码支付
            body=f'订单支付-{request.order_id}',
            out_trade_no=request.order_id,
            total_fee=int(request.amount * 100),  # 单位：分
            notify_url='https://myshop.com/payment/wechat/notify',
        )
        # 返回二维码链接
        return PaymentResult(...)
```

### 集成步骤

1. 注册微信商户平台：https://pay.weixin.qq.com/
2. 获取商户号（mch_id）和API密钥
3. 下载证书（API证书）
4. 配置回调地址

### 参考文档

- 官方文档：https://pay.weixin.qq.com/wiki/doc/api/
- Python SDK：https://github.com/wechatpy/wechatpy

---

## 5️⃣ StripeAdapter（Stripe - 国际）

### 安装依赖

```bash
pip install stripe
```

### 实现骨架

```python
import stripe
from contexts.ordering.domain.ports.services import IPaymentService

class StripeAdapter(IPaymentService):
    def __init__(self, api_key: str):
        stripe.api_key = api_key

    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        # 创建支付意图
        intent = stripe.PaymentIntent.create(
            amount=int(request.amount * 100),  # 单位：分
            currency=request.currency.lower(),
            description=f'Order {request.order_id}',
            metadata={'order_id': request.order_id},
        )

        return PaymentResult(
            transaction_id=intent.id,
            status=PaymentStatus.PROCESSING,
            amount=request.amount,
            payment_method=request.payment_method,
        )
```

### 集成步骤

1. 注册 Stripe：https://stripe.com/
2. 获取 API 密钥（测试环境和生产环境分别获取）
3. 配置 Webhook 接收支付事件

### 参考文档

- 官方文档：https://stripe.com/docs/api
- Python SDK：https://github.com/stripe/stripe-python

---

## 6️⃣ SmsAdapter（短信通知）

### 安装依赖

```bash
# 阿里云
pip install aliyun-python-sdk-core
pip install aliyun-python-sdk-dysmsapi

# 腾讯云
pip install tencentcloud-sdk-python
```

### 实现骨架（阿里云）

```python
from aliyunsdkcore.client import AcsClient
from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
from contexts.ordering.domain.ports.services import INotificationService

class SmsAdapter(INotificationService):
    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        sign_name: str,
        region: str = "cn-hangzhou",
    ):
        self.client = AcsClient(access_key_id, access_key_secret, region)
        self.sign_name = sign_name

    async def send_notification(self, request: NotificationRequest) -> NotificationResult:
        if request.notification_type != NotificationType.SMS:
            return NotificationResult(success=False, ...)

        # 构建请求
        sms_request = SendSmsRequest.SendSmsRequest()
        sms_request.set_PhoneNumbers(request.recipient)
        sms_request.set_SignName(self.sign_name)
        sms_request.set_TemplateCode(request.template_id)
        sms_request.set_TemplateParam(request.template_data)

        # 发送短信
        response = self.client.do_action_with_exception(sms_request)
        # 处理响应
        return NotificationResult(...)
```

### 集成步骤

1. 注册云服务商账号（阿里云/腾讯云）
2. 开通短信服务
3. 申请签名和模板
4. 获取 AccessKey

### 参考文档

- 阿里云：https://help.aliyun.com/product/44282.html
- 腾讯云：https://cloud.tencent.com/document/product/382

---

## 7️⃣ RedisInventoryAdapter（Redis库存）

### 安装依赖

```bash
pip install redis
pip install aioredis  # 异步版本
```

### 实现骨架

```python
import redis.asyncio as redis
from contexts.ordering.domain.ports.services import IInventoryService

class RedisInventoryAdapter(IInventoryService):
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        # 从 Redis 获取库存
        stock = await self.redis.get(f"inventory:{product_id}")
        if stock is None:
            return False
        return int(stock) >= quantity

    async def deduct_inventory(self, product_id: str, quantity: int) -> bool:
        # 使用 Lua 脚本保证原子性
        lua_script = """
        local stock = redis.call('GET', KEYS[1])
        if not stock or tonumber(stock) < tonumber(ARGV[1]) then
            return 0
        end
        redis.call('DECRBY', KEYS[1], ARGV[1])
        return 1
        """
        result = await self.redis.eval(
            lua_script,
            1,
            f"inventory:{product_id}",
            quantity
        )
        return result == 1
```

### 优势

- ✅ 高性能（内存操作）
- ✅ 原子性（Lua 脚本）
- ✅ 支持分布式
- ✅ 支持过期时间（预留库存）

### 集成步骤

1. 安装 Redis
2. 配置 Redis 连接
3. 同步数据库库存到 Redis
4. 实现双写逻辑（Redis + MySQL）

---

## 📊 Adapter 选择建议

### 支付类

| 场景 | 推荐Adapter | 原因 |
|-----|------------|------|
| **国内C端** | AlipayAdapter + WeChatPayAdapter | 支付宝和微信覆盖99%用户 |
| **国际市场** | StripeAdapter | 支持全球主流支付方式 |
| **B2B** | 银行转账 + AlipayAdapter | 大额交易 |

### 通知类

| 场景 | 推荐Adapter | 原因 |
|-----|------------|------|
| **订单通知** | EmailAdapter | 成本低、信息完整 |
| **验证码** | SmsAdapter | 实时性强、到达率高 |
| **营销** | EmailAdapter + PushAdapter | 多渠道触达 |
| **紧急通知** | SmsAdapter + PushAdapter | 确保送达 |

### 库存类

| 场景 | 推荐Adapter | 原因 |
|-----|------------|------|
| **小规模** | LocalInventoryAdapter | 简单、无额外依赖 |
| **中等规模** | RedisInventoryAdapter | 高性能、支持并发 |
| **大规模** | InventoryServiceAdapter | 独立服务、易扩展 |
| **微服务** | InventoryServiceAdapter | 服务解耦 |

---

## 🔧 依赖注入配置

### 根据环境选择 Adapter

```python
import os
from contexts.ordering.infrastructure.adapters import *

def get_payment_adapter():
    """根据环境获取支付适配器"""
    env = os.getenv("ENV", "development")

    if env == "production":
        # 生产环境：支付宝
        return AlipayAdapter(
            app_id=os.getenv("ALIPAY_APP_ID"),
            app_private_key_path="keys/alipay_private_key.pem",
            alipay_public_key_path="keys/alipay_public_key.pem",
            debug=False,
        )
    else:
        # 开发/测试环境：Mock
        return MockPaymentAdapter()

def get_notification_adapter():
    """根据环境获取通知适配器"""
    env = os.getenv("ENV", "development")

    if env == "production":
        # 生产环境：真实邮件
        return EmailAdapter(
            config=EmailConfig(
                smtp_host=os.getenv("SMTP_HOST"),
                smtp_port=int(os.getenv("SMTP_PORT", "465")),
                smtp_user=os.getenv("SMTP_USER"),
                smtp_password=os.getenv("SMTP_PASSWORD"),
                from_email=os.getenv("FROM_EMAIL"),
                use_ssl=True,
            )
        )
    else:
        # 开发/测试环境：Mock
        return MockNotificationAdapter()

def get_inventory_adapter(session):
    """根据环境获取库存适配器"""
    env = os.getenv("ENV", "development")

    if env == "production":
        # 生产环境：Redis
        return RedisInventoryAdapter(
            redis_url=os.getenv("REDIS_URL")
        )
    else:
        # 开发/测试环境：本地数据库
        return LocalInventoryAdapter(session)
```

### 在 Use Case 中使用

```python
# interfaces/order_api.py
def get_create_order_use_case(uow=Depends(get_uow)):
    return CreateOrderUseCase(
        uow=uow,
        product_catalog=ProductCatalogAdapter(uow.session),
        payment=get_payment_adapter(),
        notification=get_notification_adapter(),
        inventory=get_inventory_adapter(uow.session),
    )
```

---

## 📋 实现清单

### 已完成 ✅

- [x] MockPaymentAdapter
- [x] MockNotificationAdapter
- [x] MockInventoryAdapter
- [x] ProductCatalogAdapter
- [x] EmailAdapter
- [x] LocalInventoryAdapter

### 模板已提供 📝

- [x] AlipayAdapter（模板 + 指南）
- [x] WeChatPayAdapter（指南）
- [x] StripeAdapter（指南）
- [x] SmsAdapter（指南）
- [x] RedisInventoryAdapter（指南）

### 待实现（可选）⏳

- [ ] PushAdapter（推送通知）
- [ ] InventoryServiceAdapter（独立服务）

---

## 🎯 下一步

1. **P1 - 推荐立即实现**
   - 选择支付方式（AlipayAdapter 或 StripeAdapter）
   - 可选：SmsAdapter（如需短信验证码）

2. **P2 - 可选实现**
   - RedisInventoryAdapter（如果需要高并发）
   - PushAdapter（如需APP推送）

3. **测试和优化**
   - 在沙箱环境测试所有 Adapters
   - 编写集成测试
   - 监控和日志

---

**所有 Adapter 都遵循相同的接口，切换实现不需要修改业务代码！** 🚀

这就是六边形架构的威力！
