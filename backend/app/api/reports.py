import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Request, UploadFile
from pydantic import BaseModel, Field

from app.services.report_normalizer import ReportNormalizationError
from app.services.report_parser import InvalidReportURL, extract_report_code
from app.services.report_service import ReportNotFoundError, ReportService
from app.services.combat_log import MAX_LOG_BYTES, analyze_combat_log, decompress_combat_log
from app.services.wcl_client import WCLAPIError, WCLConfigurationError

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)
REPORT_CODE_PATH = Path(pattern=r"^[A-Za-z0-9]+$")


class ParseReportRequest(BaseModel):
    report_url: str = Field(min_length=1, max_length=2048)


class ParseReportResponse(BaseModel):
    report_code: str


def get_report_service(request: Request) -> ReportService:
    return request.app.state.report_service


def _raise_api_error(exc: Exception) -> None:
    if isinstance(exc, WCLConfigurationError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ReportNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, InvalidReportURL):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, (WCLAPIError, ReportNormalizationError, httpx.HTTPError, ValueError)):
        raise HTTPException(status_code=502, detail="Warcraft Logs could not provide a valid report response.") from exc
    raise exc


@router.post("/parse", response_model=ParseReportResponse)
async def parse_report_url(payload: ParseReportRequest) -> dict[str, str]:
    try:
        return {"report_code": extract_report_code(payload.report_url)}
    except InvalidReportURL as exc:
        _raise_api_error(exc)


@router.post("/local/analyze")
async def analyze_local_log(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith((".txt", ".log", ".txt.gz", ".log.gz")):
        raise HTTPException(status_code=422, detail="Choose a WoW combat log .txt or .log file.")
    is_gzip = file.filename.lower().endswith(".gz")
    content = await file.read(MAX_LOG_BYTES + 1)
    await file.close()
    try:
        if is_gzip:
            content = decompress_combat_log(content)
        result = analyze_combat_log(content)
        result["file_name"] = file.filename
        return result
    except ValueError as exc:
        raise HTTPException(status_code=413 if len(content) > MAX_LOG_BYTES else 422, detail=str(exc)) from exc


@router.get("/{report_code}")
async def get_report(
    report_code: str = REPORT_CODE_PATH,
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    try:
        return await service.get_report(report_code)
    except Exception as exc:
        logger.exception("Report request failed for %s", report_code)
        _raise_api_error(exc)


@router.get("/{report_code}/fights")
async def get_report_fights(
    report_code: str = REPORT_CODE_PATH,
    service: ReportService = Depends(get_report_service),
) -> list[dict[str, Any]]:
    try:
        return await service.get_fights(report_code)
    except Exception as exc:
        logger.exception("Fight request failed for report %s", report_code)
        _raise_api_error(exc)


@router.get("/{report_code}/fights/{fight_id}/analysis")
async def get_fight_analysis(
    report_code: str = REPORT_CODE_PATH,
    fight_id: int = Path(gt=0),
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    try:
        return await service.get_fight_analysis(report_code, fight_id)
    except Exception as exc:
        logger.exception("Fight analysis request failed for report %s fight %s", report_code, fight_id)
        _raise_api_error(exc)


@router.get("/{report_code}/fights/{fight_id}/benchmarks")
async def get_fight_benchmarks(
    report_code: str = REPORT_CODE_PATH,
    fight_id: int = Path(gt=0),
    strictness: str = Query(default="balanced", pattern="^(strict|balanced|broad)$"),
    source: str = Query(default="recent", pattern="^(recent|execution|progression)$"),
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    try:
        return await service.get_benchmarks(report_code, fight_id, strictness, source)
    except Exception as exc:
        logger.exception("Benchmark request failed for report %s fight %s", report_code, fight_id)
        _raise_api_error(exc)
