from typing import Any

from fastapi import status


class MainAPIException(Exception):
    """Business/API error that serializes to the MainAPIException JSON shape."""

    def __init__(
        self,
        *,
        type: str,
        code: int,
        message: str,
        localized_message: dict[str, str] | None = None,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        self.type = type
        self.code = code
        self.message = message
        self.localized_message = localized_message
        self.http_status = http_status
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "type": self.type,
            "code": self.code,
            "message": self.message,
        }
        if self.localized_message is not None:
            error["localized_message"] = self.localized_message
        return {"status": "failed", "error": error}
