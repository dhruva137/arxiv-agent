from enum import Enum
from pydantic import BaseModel

class Significance(str, Enum):
    COSMETIC = "COSMETIC"         # typos, formatting
    CLARIFICATION = "CLARIFICATION"  # rewording, same meaning
    SUBSTANTIVE = "SUBSTANTIVE"    # new content, modified arguments
    CRITICAL = "CRITICAL"          # changed results, weakened claims

class Severity(str, Enum):
    COSMETIC = "COSMETIC"
    MINOR = "MINOR"
    SIGNIFICANT = "SIGNIFICANT"
    MAJOR = "MAJOR"

class ChangeEntry(BaseModel):
    section: str
    significance: Significance
    description: str
    detail: str | None = None

class NumberChange(BaseModel):
    location: str
    metric: str
    old_value: str
    new_value: str
    direction: str  # "increased", "decreased", "changed"

class Changelog(BaseModel):
    arxiv_id: str
    title: str
    version_from: int
    version_to: int
    date_from: str
    date_to: str
    severity: Severity
    tldr: str
    changes: list[ChangeEntry]
    number_changes: list[NumberChange]
    unchanged_claims: list[str]
    new_authors: list[str]
    removed_authors: list[str]
    new_sections: list[str]
    removed_sections: list[str]
    likely_peer_review_response: bool
