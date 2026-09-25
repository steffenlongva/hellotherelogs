from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field

from app.services.report_normalizer import ReportNormalizationError
from app.services.report_parser import InvalidReportURL, extract_report_code
from app.services.report_service import ReportNotFoundError, ReportService
from app.services.wcl_client import WCLAPIError, WCLConfigurationError

router = APIRouter(prefix="/reports", tags=["reports"])
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


@router.get("/{report_code}")
async def get_report(
    report_code: str = REPORT_CODE_PATH,
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    try:
        return await service.get_report(report_code)
    except Exception as exc:
        _raise_api_error(exc)


@router.get("/{report_code}/fights")
async def get_report_fights(
    report_code: str = REPORT_CODE_PATH,
    service: ReportService = Depends(get_report_service),
) -> list[dict[str, Any]]:
    try:
        return await service.get_fights(report_code)
    except Exception as exc:
        _raise_api_error(exc)
