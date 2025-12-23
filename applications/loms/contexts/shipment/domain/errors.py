from dataclasses import dataclass

@dataclass(frozen=True)
class ContractError(Exception):
    http_status: int
    code: str
    message_key: str
    reason_code: str
    retryable: bool
    params: dict
    details: dict

    def to_payload(self, locale: str, localize) -> dict:
        message = localize(locale, self.message_key, self.params)
        return {
            "code": self.code,
            "message": message,
            "message_key": self.message_key,
            "params": self.params or {},
            "reason_code": self.reason_code,
            "retryable": self.retryable,
            "details": self.details or {},
        }

    @staticmethod
    def validation_failed(message_key: str = "VALIDATION_FAILED", *, details: dict | None = None, params: dict | None = None):
        return ContractError(400, "VALIDATION_ERROR", message_key, "VALIDATION_FAILED", False, params or {}, details or {})

    @staticmethod
    def unauthorized(details: dict | None = None):
        return ContractError(401, "UNAUTHORIZED", "UNAUTHORIZED", "UNAUTHORIZED", False, {}, details or {})

    @staticmethod
    def forbidden(details: dict | None = None):
        return ContractError(403, "FORBIDDEN", "FORBIDDEN", "FORBIDDEN", False, {}, details or {})

    @staticmethod
    def not_found(details: dict | None = None):
        return ContractError(404, "NOT_FOUND", "NOT_FOUND", "NOT_FOUND", False, {}, details or {})

    @staticmethod
    def state_conflict(message_key: str = "STATE_CONFLICT", *, reason_code: str = "STATE_CONFLICT", details: dict | None = None, params: dict | None = None):
        return ContractError(409, "STATE_CONFLICT", message_key, reason_code, False, params or {}, details or {})
