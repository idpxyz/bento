import json
import signal
import sys
from typing import Optional

import pulsar

# 创建信号处理的标志
running = True

def signal_handler(sig, frame):
    """处理退出信号"""
    global running
    print("\n[🛑] 正在优雅关闭消费者...")
    running = False

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def consume_messages(topic: str, subscription_name: str, timeout_ms: int = 5000):
    """持续消费消息的函数"""
    client = pulsar.Client("pulsar://192.168.8.137:6650")
    
    try:
        consumer = client.subscribe(
            topic,
            subscription_name=subscription_name,
            consumer_type=pulsar.ConsumerType.Exclusive
        )
        
        print(f"[🔄] 开始监听主题 {topic}，按 Ctrl+C 退出...")
        
        # 持续消费消息直到手动停止
        while running:
            try:
                # 使用较短的超时时间，以便能够及时响应退出信号
                msg = consumer.receive(timeout_millis=timeout_ms)
                
                try:
                    data = json.loads(msg.data())
                    print(f"[📩] 收到消息 ID: {msg.message_id()}")
                    print(f"[📄] 消息内容: {data}")
                    
                    # 确认消息已处理
                    consumer.acknowledge(msg)
                except json.JSONDecodeError:
                    print(f"[⚠️] 无法解析消息内容: {msg.data()}")
                    consumer.negative_acknowledge(msg)
                except Exception as e:
                    print(f"[❌] 消费失败: {str(e)}")
                    consumer.negative_acknowledge(msg)
                    
            except pulsar.Timeout:
                # 超时不做任何处理，继续循环
                continue
            except Exception as e:
                print(f"[❗] 接收消息出错: {str(e)}")
                # 短暂暂停以避免在出错情况下过度消耗CPU
                if running:
                    import time
                    time.sleep(1)
    
    finally:
        # 无论如何都确保资源被正确关闭
        print("[🧹] 正在清理资源...")
        try:
            if 'consumer' in locals():
                consumer.close()
            client.close()
        except Exception as e:
            print(f"[⚠️] 关闭资源时出错: {str(e)}")
        print("[✓] 消费者已关闭")

if __name__ == "__main__":
    # 默认配置
    default_topic = "persistent://idp-framework/idp-namespace/idp-topic"
    default_subscription = "test-subscription"
    
    # 从命令行参数获取配置（如果提供）
    topic = sys.argv[1] if len(sys.argv) > 1 else default_topic
    subscription = sys.argv[2] if len(sys.argv) > 2 else default_subscription
    
    # 启动消费循环
    consume_messages(topic, subscription)
