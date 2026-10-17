"""One JSON error shape for every failure: {"error": {"code": ..., "message": ...}}."""

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)

_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    501: "not_implemented",
}


class AppError(Exception):
    """Raise from services/routers for an expected, user-facing failure."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


async def _app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.code, exc.message)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _STATUS_CODES.get(exc.status_code, "http_error")
    return error_response(exc.status_code, code, str(exc.detail), getattr(exc, "headers", None))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
        parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    return error_response(422, "validation_error", "; ".join(parts) or "Invalid request")


async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", exc_info=exc)
    return error_response(500, "internal_error", "Something went wrong")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled_error)
