from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import MainAPIException
from app.core.responses import error_response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MainAPIException)
    async def main_api_exception_handler(
        _request: Request, exc: MainAPIException
    ) -> JSONResponse:
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg')}"
            for err in exc.errors()
        )
        return error_response(
            MainAPIException(
                type="validation",
                code=422,
                message=details or "Validation error",
                localized_message={
                    "en": "Invalid request data",
                    "ar": "بيانات الطلب غير صالحة",
                },
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return error_response(
            MainAPIException(
                type="http",
                code=exc.status_code,
                message=detail,
                http_status=exc.status_code,
            )
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        return error_response(
            MainAPIException(
                type="server",
                code=500,
                message="Internal server error",
                localized_message={
                    "en": "Something went wrong. Please try again later.",
                    "ar": "حدث خطأ ما. يرجى المحاولة مرة أخرى لاحقاً.",
                },
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        )
