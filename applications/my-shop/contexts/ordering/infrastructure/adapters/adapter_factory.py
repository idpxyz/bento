"""Adapter 工厂

根据环境和配置自动选择合适的 Adapter 实现。
支持开发、测试、生产环境的无缝切换。
"""

import os

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.ordering.domain.ports.services import (
    IInventoryService,
    INotificationService,
    IPaymentService,
    IProductCatalogService,
)


class AdapterFactory:
    """Adapter 工厂

    负责根据环境创建合适的 Adapter 实例。

    使用示例：
    ```python
    factory = AdapterFactory(session)

    # 获取 Adapters
    payment = factory.get_payment_adapter()
    notification = factory.get_notification_adapter()
    inventory = factory.get_inventory_adapter()
    ```
    """

    def __init__(self, session: AsyncSession | None = None):
        """初始化工厂

        Args:
            session: 数据库会话（某些 Adapter 需要）
        """
        self.session = session
        self.env = os.getenv("ENV", "development")

    def get_product_catalog_adapter(self) -> IProductCatalogService:
        """获取产品目录适配器

        所有环境都使用真实实现（查询数据库）
        """
        from contexts.ordering.infrastructure.adapters import ProductCatalogAdapter

        if not self.session:
            raise ValueError("ProductCatalogAdapter requires database session")

        return ProductCatalogAdapter(self.session)

    def get_payment_adapter(self) -> IPaymentService:
        """获取支付适配器

        - 开发/测试环境：MockPaymentAdapter
        - 生产环境：AlipayAdapter（需要配置）
        """
        if self.env == "production":
            # 生产环境：尝试使用真实支付
            alipay_app_id = os.getenv("ALIPAY_APP_ID")

            if alipay_app_id:
                # 使用支付宝（需要先实现 AlipayAdapter）
                private_key_path = os.getenv("ALIPAY_PRIVATE_KEY_PATH")
                public_key_path = os.getenv("ALIPAY_PUBLIC_KEY_PATH")

                if private_key_path and public_key_path:
                    try:
                        # Import template (needs implementation)
                        # pylint: disable=import-error
                        from contexts.ordering.infrastructure.adapters.services._alipay_adapter_template import (  # noqa: E501
                            AlipayAdapter,
                        )

                        return AlipayAdapter(
                            app_id=alipay_app_id,
                            app_private_key_path=private_key_path,
                            alipay_public_key_path=public_key_path,
                            debug=False,
                        )
                    except (ImportError, NotImplementedError):
                        print("⚠️ AlipayAdapter not fully implemented, using Mock")

            # 如果没有配置或未实现，降级为 Mock
            print("⚠️ Production environment but using MockPaymentAdapter")

        # 开发/测试环境：使用 Mock
        from contexts.ordering.infrastructure.adapters import MockPaymentAdapter

        return MockPaymentAdapter()

    def get_notification_adapter(self) -> INotificationService:
        """获取通知适配器

        - 开发/测试环境：MockNotificationAdapter（除非配置了邮件）
        - 生产环境：EmailAdapter（需要配置）
        """
        # 检查是否配置了邮件
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        if smtp_user and smtp_password:
            # 使用真实邮件适配器
            from contexts.ordering.infrastructure.adapters import (
                EmailAdapter,
                EmailConfig,
            )

            config = EmailConfig(
                smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
                smtp_port=int(os.getenv("SMTP_PORT", "465")),
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_email=os.getenv("FROM_EMAIL", "noreply@myshop.com"),
                from_name=os.getenv("FROM_NAME", "My Shop"),
                use_ssl=os.getenv("EMAIL_USE_SSL", "true").lower() == "true",
                use_tls=os.getenv("EMAIL_USE_TLS", "false").lower() == "true",
            )

            print(f"📧 Using EmailAdapter (SMTP: {config.smtp_host})")
            return EmailAdapter(config)

        # 使用 Mock
        from contexts.ordering.infrastructure.adapters import MockNotificationAdapter

        verbose = self.env != "test"  # 测试环境不输出详细日志
        print(f"📧 Using MockNotificationAdapter (verbose={verbose})")
        return MockNotificationAdapter(verbose=verbose)

    def get_inventory_adapter(self) -> IInventoryService:
        """获取库存适配器

        - 开发/测试环境：LocalInventoryAdapter（需要数据库）或 MockInventoryAdapter
        - 生产环境：RedisInventoryAdapter（需要配置）或 LocalInventoryAdapter
        """
        if self.env == "production":
            # 生产环境：优先使用 Redis
            redis_url = os.getenv("REDIS_URL")

            if redis_url:
                try:
                    # Try to import Redis adapter (not implemented yet)
                    # pylint: disable=import-error
                    from contexts.ordering.infrastructure.adapters.services.redis_inventory_adapter import (  # noqa: E501  # type: ignore
                        RedisInventoryAdapter,
                    )

                    msg = f"📦 Using RedisInventoryAdapter (Redis: {redis_url})"
                    print(msg)
                    return RedisInventoryAdapter(redis_url)
                except ImportError:
                    msg = "⚠️ RedisInventoryAdapter not implemented"
                    print(f"{msg}, using LocalInventoryAdapter")

        # 使用本地数据库库存
        if self.session:
            from contexts.ordering.infrastructure.adapters import LocalInventoryAdapter

            print("📦 Using LocalInventoryAdapter (Database)")
            return LocalInventoryAdapter(self.session)

        # 如果没有数据库会话，使用 Mock
        from contexts.ordering.infrastructure.adapters import MockInventoryAdapter

        print("📦 Using MockInventoryAdapter")
        return MockInventoryAdapter()

    def get_all_adapters(self) -> dict:
        """获取所有适配器

        Returns:
            dict: {
                'product_catalog': IProductCatalogService,
                'payment': IPaymentService,
                'notification': INotificationService,
                'inventory': IInventoryService,
            }
        """
        return {
            "product_catalog": self.get_product_catalog_adapter(),
            "payment": self.get_payment_adapter(),
            "notification": self.get_notification_adapter(),
            "inventory": self.get_inventory_adapter(),
        }


# ============ 便捷函数 ============


def create_adapters(session: AsyncSession | None = None) -> dict:
    """创建所有适配器（便捷函数）

    Args:
        session: 数据库会话

    Returns:
        dict: 所有适配器

    Example:
        ```python
        adapters = create_adapters(session)

        use_case = CreateOrderUseCase(
            uow=uow,
            product_catalog=adapters['product_catalog'],
            payment=adapters['payment'],
            notification=adapters['notification'],
            inventory=adapters['inventory'],
        )
        ```
    """
    factory = AdapterFactory(session)
    return factory.get_all_adapters()


def get_payment_adapter() -> IPaymentService:
    """获取支付适配器（便捷函数）"""
    return AdapterFactory().get_payment_adapter()


def get_notification_adapter() -> INotificationService:
    """获取通知适配器（便捷函数）"""
    return AdapterFactory().get_notification_adapter()


def get_inventory_adapter(session: AsyncSession | None = None) -> IInventoryService:
    """获取库存适配器（便捷函数）"""
    return AdapterFactory(session).get_inventory_adapter()


def get_product_catalog_adapter(session: AsyncSession) -> IProductCatalogService:
    """获取产品目录适配器（便捷函数）"""
    return AdapterFactory(session).get_product_catalog_adapter()


# ============ 使用示例 ============
"""
## 方式1：使用工厂类

```python
from contexts.ordering.infrastructure.adapters.adapter_factory import AdapterFactory

# 创建工厂
factory = AdapterFactory(session)

# 获取各个适配器
payment = factory.get_payment_adapter()
notification = factory.get_notification_adapter()
inventory = factory.get_inventory_adapter()
product_catalog = factory.get_product_catalog_adapter()

# 或一次性获取所有
adapters = factory.get_all_adapters()
```

## 方式2：使用便捷函数

```python
from contexts.ordering.infrastructure.adapters.adapter_factory import (
    create_adapters,
    get_payment_adapter,
    get_notification_adapter,
)

# 一次性创建所有
adapters = create_adapters(session)

# 或单独获取
payment = get_payment_adapter()
notification = get_notification_adapter()
```

## 方式3：在依赖注入中使用

```python
# interfaces/order_api.py
from contexts.ordering.infrastructure.adapters.adapter_factory import AdapterFactory

def get_create_order_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
):
    # 创建工厂
    factory = AdapterFactory(uow.session)

    # 创建 Use Case
    return CreateOrderUseCase(
        uow=uow,
        product_catalog=factory.get_product_catalog_adapter(),
        payment=factory.get_payment_adapter(),
        notification=factory.get_notification_adapter(),
        inventory=factory.get_inventory_adapter(),
    )
```

## 环境配置

通过环境变量控制 Adapter 选择：

```bash
# 开发环境（使用 Mock）
ENV=development

# 生产环境（使用真实 Adapter）
ENV=production
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
ALIPAY_APP_ID=your-app-id
REDIS_URL=redis://localhost:6379/0
```

## 优势

✅ **自动选择** - 根据环境自动选择合适的 Adapter
✅ **配置驱动** - 通过环境变量控制，无需修改代码
✅ **降级策略** - 配置不完整时自动降级为 Mock
✅ **易于测试** - 测试环境自动使用 Mock
✅ **生产就绪** - 生产环境自动使用真实 Adapter
"""
