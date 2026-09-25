import pytest

from app.services.report_parser import InvalidReportURL, extract_report_code


def test_extract_report_code_from_fresh_url() -> None:
    assert extract_report_code("https://fresh.warcraftlogs.com/reports/AbC123?fight=last") == "AbC123"
    assert extract_report_code("https://fresh.warcraftlogs.com/reports/AbC123/") == "AbC123"


@pytest.mark.parametrize("url", [
    "https://www.warcraftlogs.com/reports/AbC123",
    "https://fresh.warcraftlogs.com/characters/AbC123",
    "javascript:alert(1)",
    "https://fresh.warcraftlogs.com.evil.example/reports/AbC123",
    "https://fresh.warcraftlogs.com/reports/",
    "not a url",
])
def test_reject_invalid_report_urls(url: str) -> None:
    with pytest.raises(InvalidReportURL):
        extract_report_code(url)
