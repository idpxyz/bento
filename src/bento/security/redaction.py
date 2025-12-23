SENSITIVE_KEYS = {"authorization", "cookie", "set-cookie", "x-api-key", "token", "secret", "password"}

def redact_headers(headers: dict) -> dict:
    out = {}
    for k,v in headers.items():
        if k.lower() in SENSITIVE_KEYS:
            out[k] = "***"
        else:
            out[k] = v
    return out
