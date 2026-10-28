"""Health-check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthResponse
from app.services.ocr_service import OCRService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns the current service status, version, database, OCR engine, and environment.",
)
def health_check() -> HealthResponse:
    settings = get_settings()
    ocr = OCRService(settings.tesseract_cmd)
    ocr_avail = ocr.is_engine_available()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        service="AICTE VerifyAI API",
        database="SQLite (verifyai.db)",
        ocrEngineAvailable=ocr_avail,
        ocrDetails="Tesseract OCR engine is available." if ocr_avail else "Tesseract OCR binary not found on PATH. Native PDF extraction active.",
        pdfEngine="PyMuPDF (fitz)",
    )
