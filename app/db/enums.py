from enum import StrEnum


class DocumentType(StrEnum):
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    NEWS = "news"
    LEGAL_CASE = "legal_case"
    RATING_REPORT = "rating_report"
    PRESS_RELEASE = "press_release"


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskReportStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"


class AgentName(StrEnum):
    REPORT_AGENT = "report_agent"
    NEWS_AGENT = "news_agent"
    MARKET_AGENT = "market_agent"
    LEGAL_AGENT = "legal_agent"
    RATING_AGENT = "rating_agent"
    SUPERVISOR = "supervisor"
