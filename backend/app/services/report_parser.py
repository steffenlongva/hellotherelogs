import re
from urllib.parse import urlparse


REPORT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
FRESH_REPORT_HOST = "fresh.warcraftlogs.com"


class InvalidReportURL(ValueError):
    pass


def extract_report_code(report_url: str) -> str:
    parsed = urlparse(report_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname != FRESH_REPORT_HOST:
        raise InvalidReportURL("Use a Warcraft Logs Fresh report URL.")
    match = re.fullmatch(r"/reports/([A-Za-z0-9]+)/?", parsed.path)
    if not match or not REPORT_CODE_PATTERN.fullmatch(match.group(1)):
        raise InvalidReportURL("URL must contain a report path like /reports/REPORTCODE.")
    return match.group(1)
