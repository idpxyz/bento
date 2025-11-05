import sentry_sdk

sentry_sdk.init(
    dsn="https://a717fb1c8639f35bc78f4b60340ccc88@o4507072299991040.ingest.us.sentry.io/4507072302678016",  # 替换为你自己的 DSN
    traces_sample_rate=1.0,  # 或设置为 0.1 等
    environment="dev",
    send_default_pii=True,
)