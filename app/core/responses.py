from typing import Any

from fastapi.responses import JSONResponse

from app.core.exceptions import MainAPIException


def success_response(data: Any = None, *, status_code: int = 200) -> JSONResponse:
    """Wrap payload in the standard success envelope."""
    return JSONResponse(
        status_code=status_code,
        content={"status": "success", "data": data if data is not None else {}},
    )


def error_response(exc: MainAPIException) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())
