from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import uuid

class TraceXException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class EntityNotFoundError(TraceXException):
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} '{entity_id}' was not found.",
            code="ENTITY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id}
        )

class DatasetProcessingError(TraceXException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            code="DATASET_PROCESSING_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

class InvalidFileFormatError(TraceXException):
    def __init__(self, format_found: str, supported: list = None):
        super().__init__(
            message=f"Unsupported format: '{format_found}'. Supported formats are CSV, JSON, and XML.",
            code="INVALID_FILE_FORMAT",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"format": format_found, "supported": supported or ["csv", "json", "xml"]}
        )

async def tracex_exception_handler(request: Request, exc: TraceXException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": req_id,
                "details": exc.details
            }
        }
    )

async def generic_http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "request_id": req_id,
                "details": exc.detail if isinstance(exc.detail, dict) else {}
            }
        }
    )
