"""Uniform error envelope: {"error":{"code","message","fields"}} (docs/03-api-spec.md)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400, fields: dict | None = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.fields = fields or {}
        super().__init__(message)


def _envelope(code: str, message: str, fields: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "fields": fields or {}}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.http_status, content=_envelope(exc.code, exc.message, exc.fields))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
            fields[loc or "body"] = err.get("msg", "invalid")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("VALIDATION_ERROR", "Request validation failed", fields),
        )


class UnhandledErrorMiddleware:
    """Turn any unhandled exception into our JSON error envelope.

    Starlette answers unhandled errors from its outermost layer, outside CORSMiddleware, as
    plain text with no CORS headers, so a cross-site browser can't read it and reports a
    network failure ("Failed to fetch"). Installed *inside* CORS, this keeps the headers.
    The exception is logged; the client gets a generic message, never internals.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def _send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception:
            logging.getLogger("app.errors").exception(
                "Unhandled error on %s %s", scope.get("method"), scope.get("path")
            )
            if started:  # response already under way (e.g. a background task): can't replace it
                raise
            response = JSONResponse(
                status_code=500,
                content=_envelope("INTERNAL_ERROR", "Something went wrong on our side. Please try again."),
            )
            await response(scope, receive, send)
