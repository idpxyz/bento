"""AlipayAdapter - 支付宝支付适配器（实现模板）

⚠️ 此文件为实现模板，需要根据实际情况修改和完善。

集成步骤：
1. 安装支付宝 SDK: pip install alipay-sdk-python
2. 在支付宝开放平台创建应用并获取密钥
3. 配置应用私钥和支付宝公钥
4. 实现所有接口方法
5. 测试沙箱环境
6. 切换到生产环境

文档：https://opendocs.alipay.com/open/
"""

from __future__ import annotations

# TODO: 安装并导入支付宝 SDK
# from alipay import AliPay, ISVAliPay
# from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from contexts.ordering.domain.ports.services.i_payment_service import (
    IPaymentService,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
)


class AlipayAdapter(IPaymentService):
    """支付宝支付适配器

    实现：IPaymentService (domain/ports/services/i_payment_service.py)

    配置示例：
    ```python
    adapter = AlipayAdapter(
        app_id="2021001234567890",
        app_private_key_path="/path/to/app_private_key.pem",
        alipay_public_key_path="/path/to/alipay_public_key.pem",
        sign_type="RSA2",
        debug=False,  # False = 生产环境，True = 沙箱环境
    )
    ```
    """

    def __init__(
        self,
        app_id: str,
        app_private_key_path: str,
        alipay_public_key_path: str,
        sign_type: str = "RSA2",
        debug: bool = False,
    ):
        """初始化支付宝适配器

        Args:
            app_id: 应用ID
            app_private_key_path: 应用私钥文件路径
            alipay_public_key_path: 支付宝公钥文件路径
            sign_type: 签名类型（RSA2 推荐）
            debug: 是否为沙箱环境
        """
        self.app_id = app_id
        self.debug = debug

        # TODO: 初始化支付宝 SDK
        # self.alipay = AliPay(
        #     appid=app_id,
        #     app_notify_url=None,
        #     app_private_key_path=app_private_key_path,
        #     alipay_public_key_path=alipay_public_key_path,
        #     sign_type=sign_type,
        #     debug=debug
        # )

    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """处理支付

        支付宝支付流程：
        1. 创建支付订单（生成支付链接或二维码）
        2. 用户扫码/跳转支付
        3. 支付宝回调通知
        4. 验证签名并更新订单状态

        Args:
            request: 支付请求

        Returns:
            PaymentResult: 支付结果
        """
        # TODO: 实现支付宝支付逻辑

        # 示例代码：
        # order_string = self.alipay.api_alipay_trade_page_pay(
        #     subject=f"订单支付-{request.order_id}",
        #     out_trade_no=request.order_id,
        #     total_amount=str(request.amount),
        #     return_url="https://myshop.com/payment/return",
        #     notify_url="https://myshop.com/payment/notify",
        # )

        # 实际上支付是异步的，这里应该返回 PROCESSING 状态
        return PaymentResult(
            transaction_id=f"ALIPAY_{request.order_id}",
            status=PaymentStatus.PROCESSING,
            amount=request.amount,
            payment_method=request.payment_method,
            message="Payment created, waiting for user to pay",
        )

    async def query_payment(self, transaction_id: str) -> PaymentResult:
        """查询支付状态

        Args:
            transaction_id: 交易ID

        Returns:
            PaymentResult: 支付结果
        """
        # TODO: 调用支付宝查询接口

        # 示例代码：
        # response = self.alipay.api_alipay_trade_query(
        #     out_trade_no=transaction_id
        # )

        # if response.get("trade_status") == "TRADE_SUCCESS":
        #     return PaymentResult(...)

        raise NotImplementedError("Alipay query_payment not implemented")

    async def cancel_payment(self, transaction_id: str) -> bool:
        """取消支付

        Args:
            transaction_id: 交易ID

        Returns:
            bool: 是否成功取消
        """
        # TODO: 调用支付宝关闭接口

        # 示例代码：
        # response = self.alipay.api_alipay_trade_close(
        #     out_trade_no=transaction_id
        # )

        raise NotImplementedError("Alipay cancel_payment not implemented")

    async def refund_payment(
        self, transaction_id: str, amount: float | None = None
    ) -> PaymentResult:
        """退款

        Args:
            transaction_id: 交易ID
            amount: 退款金额（None 表示全额退款）

        Returns:
            PaymentResult: 退款结果
        """
        # TODO: 调用支付宝退款接口

        # 示例代码：
        # response = self.alipay.api_alipay_trade_refund(
        #     out_trade_no=transaction_id,
        #     refund_amount=str(amount),
        #     refund_reason="用户申请退款"
        # )

        raise NotImplementedError("Alipay refund_payment not implemented")


# ============ 集成指南 ============
"""
## 1. 安装依赖

```bash
pip install alipay-sdk-python
```

## 2. 获取密钥

1. 登录支付宝开放平台：https://open.alipay.com/
2. 创建应用
3. 配置应用信息（网页/移动应用）
4. 生成RSA密钥对
5. 上传公钥到支付宝
6. 下载支付宝公钥

## 3. 配置示例

```python
# 开发环境配置
adapter = AlipayAdapter(
    app_id="2021001234567890",  # 沙箱应用ID
    app_private_key_path="keys/app_private_key.pem",
    alipay_public_key_path="keys/alipay_public_key.pem",
    debug=True,  # 使用沙箱环境
)

# 生产环境配置
adapter = AlipayAdapter(
    app_id="2021009876543210",  # 正式应用ID
    app_private_key_path="keys/prod_app_private_key.pem",
    alipay_public_key_path="keys/prod_alipay_public_key.pem",
    debug=False,  # 使用生产环境
)
```

## 4. 实现回调处理

```python
@app.post("/payment/notify")
async def alipay_notify(request: Request):
    '''支付宝异步通知'''
    # 获取通知参数
    params = await request.form()

    # 验证签名
    sign = params.get("sign")
    if adapter.verify(params, sign):
        # 处理支付结果
        out_trade_no = params.get("out_trade_no")
        trade_status = params.get("trade_status")

        if trade_status == "TRADE_SUCCESS":
            # 更新订单状态
            pass

    return "success"
```

## 5. 参考文档

- 支付宝开放平台：https://opendocs.alipay.com/open/
- Python SDK：https://github.com/fzlee/alipay
- 沙箱环境：https://openhome.alipay.com/develop/sandbox/app
"""
