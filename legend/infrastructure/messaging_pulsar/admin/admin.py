import argparse
import asyncio

from idp.framework.infrastructure.messaging.admin.client import PulsarAdminClient
from idp.framework.infrastructure.messaging.admin.diagnostic import Diagnostics
from idp.framework.infrastructure.messaging.admin.dlq import DLQAdmin
from idp.framework.infrastructure.messaging.admin.subscription import Subscriptions

DEFAULT_URL = "http://192.168.8.137:8080"
DEFAULT_TENANT = "idp-framework"
DEFAULT_NS = "idp-namespace"

def init_messaging():
    # Import the entire codec package to trigger auto-imports
    import idp.framework.infrastructure.messaging.codec

    # Also directly import the json module to ensure it's registered
    import idp.framework.infrastructure.messaging.codec.json  # 👈 保证执行注册

def build_parser():
    parser = argparse.ArgumentParser(description="Pulsar Admin CLI 工具")

    subparsers = parser.add_subparsers(dest="command")

    # dlq replay
    replay = subparsers.add_parser("dlq-replay", help="重放 DLQ 消息")
    replay.add_argument("topic", help="DLQ 主题（不含 persistent 路径）")
    replay.add_argument("--max", type=int, default=10, help="最多重放条数")

    # dlq clear
    clear = subparsers.add_parser("dlq-clear", help="清空 DLQ 消息")
    clear.add_argument("topic", help="DLQ 主题名")

    # backlog
    backlog = subparsers.add_parser("backlog", help="查看主题 backlog")
    backlog.add_argument("topic", help="主题名")

    # reset sub
    reset = subparsers.add_parser("reset-sub", help="重置订阅到最新位点")
    reset.add_argument("topic", help="主题名")
    reset.add_argument("sub", help="订阅名")

    return parser


async def main():
    parser = build_parser()
    args = parser.parse_args()

    init_messaging()
    admin = PulsarAdminClient(DEFAULT_URL)
    dlq = DLQAdmin(admin)
    diag = Diagnostics(admin)
    subs = Subscriptions(admin)
    
    if args.command == "dlq-replay":
        await dlq.replay_dlq(DEFAULT_TENANT, DEFAULT_NS, args.topic, args.max)

    elif args.command == "dlq-clear":
        await dlq.clear_dlq(DEFAULT_TENANT, DEFAULT_NS, args.topic)

    elif args.command == "backlog":
        size = await diag.get_backlog_size(DEFAULT_TENANT, DEFAULT_NS, args.topic)
        print(f"Backlog for {args.topic} = {size} messages")

    elif args.command == "reset-sub":
        await subs.reset_cursor_to_latest(DEFAULT_TENANT, DEFAULT_NS, args.topic, args.sub)
        print(f"Subscription {args.sub} reset to latest on {args.topic}")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())


# 实用方式示例
# 补偿 DLQ 消息
# python scripts/messaging_admin.py dlq-replay user.registered.dlq --max 10

# # 查看 backlog
# python scripts/messaging_admin.py backlog user.registered

# # 重置订阅
# python scripts/messaging_admin.py reset-sub user.registered default-sub

# # 清空 DLQ
# python scripts/messaging_admin.py dlq-clear user.registered.dlq
