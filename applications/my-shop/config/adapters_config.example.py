"""Adapters 配置示例

复制此文件为 adapters_config.py 并填写实际配置。
注意：不要将 adapters_config.py 提交到版本控制！
"""

import os
from dataclasses import dataclass


@dataclass
class EmailAdapterConfig:
    """邮件适配器配置"""

    # SMTP 服务器配置
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    smtp_user: str = os.getenv("SMTP_USER", "your-email@gmail.com")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "your-app-password")

    # 发件人信息
    from_email: str = os.getenv("FROM_EMAIL", "noreply@myshop.com")
    from_name: str = os.getenv("FROM_NAME", "My Shop")

    # SSL/TLS 配置
    use_ssl: bool = os.getenv("EMAIL_USE_SSL", "true").lower() == "true"
    use_tls: bool = os.getenv("EMAIL_USE_TLS", "false").lower() == "true"


@dataclass
class AlipayAdapterConfig:
    """支付宝适配器配置"""

    # 应用信息
    app_id: str = os.getenv("ALIPAY_APP_ID", "")

    # 密钥路径（推荐使用绝对路径）
    app_private_key_path: str = os.getenv(
        "ALIPAY_PRIVATE_KEY_PATH", "config/keys/alipay/app_private_key.pem"
    )
    alipay_public_key_path: str = os.getenv(
        "ALIPAY_PUBLIC_KEY_PATH", "config/keys/alipay/alipay_public_key.pem"
    )

    # 签名类型
    sign_type: str = "RSA2"

    # 环境配置
    debug: bool = os.getenv("ALIPAY_DEBUG", "true").lower() == "true"

    # 回调地址
    notify_url: str = os.getenv("ALIPAY_NOTIFY_URL", "https://myshop.com/api/payment/alipay/notify")
    return_url: str = os.getenv("ALIPAY_RETURN_URL", "https://myshop.com/payment/success")


@dataclass
class SmsAdapterConfig:
    """短信适配器配置（阿里云）"""

    # AccessKey
    access_key_id: str = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
    access_key_secret: str = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")

    # 短信配置
    sign_name: str = os.getenv("SMS_SIGN_NAME", "My Shop")
    region: str = os.getenv("SMS_REGION", "cn-hangzhou")

    # 模板ID
    template_verify_code: str = os.getenv("SMS_TEMPLATE_VERIFY", "SMS_123456789")
    template_order_created: str = os.getenv("SMS_TEMPLATE_ORDER_CREATED", "SMS_987654321")


@dataclass
class RedisInventoryConfig:
    """Redis 库存适配器配置"""

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_password: str = os.getenv("REDIS_PASSWORD", "")

    # 库存键前缀
    inventory_prefix: str = "inventory:"

    # 预留过期时间（秒）
    reservation_ttl: int = int(os.getenv("INVENTORY_RESERVATION_TTL", "1800"))  # 30分钟


# ============ 环境配置 ============


class AdaptersConfig:
    """适配器总配置"""

    def __init__(self):
        self.env = os.getenv("ENV", "development")

        # 邮件配置
        self.email = EmailAdapterConfig()

        # 支付宝配置
        self.alipay = AlipayAdapterConfig()

        # 短信配置
        self.sms = SmsAdapterConfig()

        # Redis 库存配置
        self.redis_inventory = RedisInventoryConfig()

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.env == "production"

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.env == "development"

    def is_test(self) -> bool:
        """是否为测试环境"""
        return self.env == "test"


# ============ 配置实例 ============

# 全局配置实例
config = AdaptersConfig()


# ============ 配置说明 ============
"""
## 使用方式

### 1. 复制配置文件
```bash
cp config/adapters_config.example.py config/adapters_config.py
```

### 2. 配置环境变量

创建 .env 文件：

```env
# 环境
ENV=development

# 邮件配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@myshop.com
FROM_NAME=My Shop
EMAIL_USE_SSL=true

# 支付宝配置
ALIPAY_APP_ID=2021001234567890
ALIPAY_PRIVATE_KEY_PATH=/path/to/app_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=/path/to/alipay_public_key.pem
ALIPAY_DEBUG=true
ALIPAY_NOTIFY_URL=https://myshop.com/api/payment/alipay/notify
ALIPAY_RETURN_URL=https://myshop.com/payment/success

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
INVENTORY_RESERVATION_TTL=1800
```

### 3. 在代码中使用

```python
from config.adapters_config import config
from contexts.ordering.infrastructure.adapters import EmailAdapter
from contexts.ordering.infrastructure.adapters.services.email_adapter import EmailConfig

# 使用配置创建适配器
email_adapter = EmailAdapter(
    EmailConfig(
        smtp_host=config.email.smtp_host,
        smtp_port=config.email.smtp_port,
        smtp_user=config.email.smtp_user,
        smtp_password=config.email.smtp_password,
        from_email=config.email.from_email,
        from_name=config.email.from_name,
        use_ssl=config.email.use_ssl,
    )
)
```

## Gmail 配置步骤

1. 启用两步验证：https://myaccount.google.com/security
2. 生成应用专用密码：https://myaccount.google.com/apppasswords
3. 使用应用密码作为 SMTP_PASSWORD

## 支付宝配置步骤

1. 注册开放平台：https://open.alipay.com/
2. 创建应用
3. 生成RSA密钥对（见下方命令）
4. 上传公钥到支付宝
5. 下载支付宝公钥

### 生成RSA密钥对

```bash
# 创建密钥目录
mkdir -p config/keys/alipay

# 生成应用私钥
openssl genrsa -out config/keys/alipay/app_private_key.pem 2048

# 生成应用公钥
openssl rsa -in config/keys/alipay/app_private_key.pem \\
    -pubout -out config/keys/alipay/app_public_key.pem

# 将 app_public_key.pem 的内容上传到支付宝开放平台
# 然后下载支付宝公钥保存为 alipay_public_key.pem
```

## 安全建议

1. ❌ 不要将 adapters_config.py 提交到版本控制
2. ❌ 不要将密钥文件提交到版本控制
3. ✅ 使用环境变量存储敏感信息
4. ✅ 生产环境使用密钥管理服务（如 AWS Secrets Manager）
5. ✅ 定期轮换密钥

## .gitignore

确保以下内容在 .gitignore 中：

```
# 配置文件
config/adapters_config.py
.env

# 密钥文件
config/keys/
*.pem
*.key
```
"""
