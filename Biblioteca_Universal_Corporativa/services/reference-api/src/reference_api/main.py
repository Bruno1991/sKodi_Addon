from __future__ import annotations

import base64
import binascii
import logging
import re
import time
import uuid

from corporate_security import AesGcmService, CorporateError, EnvironmentKeyProvider
from corporate_security.structured_logging import JsonFormatter
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_BODY_BYTES = 1_048_576
CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
logger = logging.getLogger("mbuc.reference_api")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
crypto = AesGcmService(EnvironmentKeyProvider())
app = FastAPI(title="MBUC Reference API", version="1.0.0", docs_url=None, redoc_url=None)


class EncryptCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    plaintext_base64: str = Field(min_length=1, max_length=1_398_104)
    associated_data: str = Field(min_length=1, max_length=512)

    @field_validator("plaintext_base64")
    @classmethod
    def validate_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("plaintext_base64 must be canonical Base64") from error
        return value


class DecryptCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    envelope: str = Field(min_length=41, max_length=1_398_200, pattern=r"^v1\.[A-Za-z0-9_-]+$")
    associated_data: str = Field(min_length=1, max_length=512)


@app.middleware("http")
async def operational_middleware(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and int(length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"version": 1, "code": "request_too_large", "message": "Request exceeds the configured limit.", "correlation_id": "rejected-size"})
    supplied = request.headers.get("x-correlation-id", "")
    correlation_id = supplied if CORRELATION_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info("Request completed.", extra={"event": "http.request", "service": "mbuc-reference-api", "correlation_id": correlation_id, "outcome": "success" if response.status_code < 500 else "failure", "structured": {"method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 3)}})
    return response


@app.exception_handler(CorporateError)
async def corporate_error_handler(request: Request, error: CorporateError) -> JSONResponse:
    status = 400 if error.code.startswith(("invalid_", "authentication_")) else 503
    return JSONResponse(status_code=status, content={"version": 1, "code": error.code, "message": error.public_message, "correlation_id": request.state.correlation_id})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready")
def ready() -> dict[str, str]:
    EnvironmentKeyProvider().get_key()
    return {"status": "ready"}


@app.post("/v1/encrypt")
def encrypt(command: EncryptCommand) -> dict[str, str | int]:
    plaintext = base64.b64decode(command.plaintext_base64, validate=True)
    envelope = crypto.encrypt(plaintext, command.associated_data.encode("utf-8"))
    return {"version": 1, "envelope": envelope}


@app.post("/v1/decrypt")
def decrypt(command: DecryptCommand) -> dict[str, str | int]:
    plaintext = crypto.decrypt(command.envelope, command.associated_data.encode("utf-8"))
    return {"version": 1, "plaintext_base64": base64.b64encode(plaintext).decode("ascii")}
