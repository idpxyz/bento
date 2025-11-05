import json

import pulsar

client = pulsar.Client("pulsar://192.168.8.137:6650")

producer = client.create_producer("persistent://idp-framework/idp-namespace/idp-topic")

payload = {
    "message": "Order Created",
    "orderId": "1234567890",
    "orderAmount": 100.00,
    "orderDate": "2021-01-01",
    "orderStatus": "CREATED",
    "orderItems": [
        {
            "itemId": "1234567890",
            "itemName": "苹果iPhone 14 Pro Max",
            "itemQuantity": 1,
            "itemPrice": 100.00
        },
        {
            "itemId": "1234567890",
            "itemName": "苹果Macbook Pro",
            "itemQuantity": 2,
            "itemPrice": 200.00
        }
    ],
    "customer": {
        "customerId": "1234567890",
        "customerName": "Customer 1",
        "customerEmail": "customer@example.com"
    },
    "sender": "producer-test 001"
}

producer.send(json.dumps(payload).encode("utf-8"))

print("[✅] 发送成功:", payload)

producer.close()
client.close()
