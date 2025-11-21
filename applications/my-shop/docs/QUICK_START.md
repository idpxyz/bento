# 🚀 快速开始

## 1. 配置环境

```bash
# 复制配置
cp config/.env.example .env

# 编辑 .env 配置邮件服务
nano .env
```

## 2. Gmail 配置

1. 启用两步验证：https://myaccount.google.com/security
2. 生成应用密码：https://myaccount.google.com/apppasswords
3. 配置 .env：

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 3. 测试

```bash
uv run python tests/ordering/test_real_adapters.py
```

## 4. 使用 Adapter Factory

```python
from contexts.ordering.infrastructure.adapters.adapter_factory import AdapterFactory

factory = AdapterFactory(session)
adapters = factory.get_all_adapters()

use_case = CreateOrderUseCase(uow=uow, **adapters)
```

完整文档见：`docs/REAL_ADAPTERS_IMPLEMENTATION_GUIDE.md`
